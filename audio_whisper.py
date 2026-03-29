"""
Captura el audio del stream de Twitch y lo transcribe usando Whisper local.
Requiere: ffmpeg, whisper (pip install openai-whisper), streamlink
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time
import threading
import wave
import io
import re
import numpy as np
try:
    import whisper as _whisper_local
except ImportError:
    _whisper_local = None

TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", "").strip()
IDIOMA = "es"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_RT_MODEL = (os.getenv("WHISPER_RT_MODEL", "") or "").strip() or WHISPER_MODEL
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "").strip()
WHISPER_RT_HOP_SEG = max(1, int(os.getenv("WHISPER_RT_HOP_SEG", "1")))
WHISPER_RT_WINDOW_SEG = max(2, int(os.getenv("WHISPER_RT_WINDOW_SEG", "3")))
WHISPER_INITIAL_PROMPT = os.getenv(
    "WHISPER_INITIAL_PROMPT",
    "Transcripcion en espanol neutro de una transmision en vivo de Twitch.",
).strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo").strip()
_MODEL_CACHE: dict[str, object] = {}
_STREAM_URL_CACHE: dict[str, tuple[str, float]] = {}
_STREAM_URL_TTL_SEG = 45
_READERS: dict[str, "ContinuousAudioReader"] = {}
_RT_STATES: dict[str, "RealtimeTranscriptionState"] = {}


class RealtimeTranscriptionState:
    """Estado por canal para subtitulado incremental."""

    def __init__(self):
        self.buffer = bytearray()
        self.last_text = ""

class ContinuousAudioReader:
    """Mantiene un proceso ffmpeg abierto para leer audio PCM continuo."""

    def __init__(self, channel: str):
        self.channel = channel
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self.last_open = 0.0
        self._open_process()

    def _open_process(self) -> bool:
        ffmpeg_bin = resolver_ffmpeg()
        if not ffmpeg_bin:
            return False

        url = get_stream_url(self.channel)
        if not url:
            return False

        cmd = [
            ffmpeg_bin,
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            url,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "s16le",
            "-",
        ]
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                bufsize=0,
            )
            self.last_open = time.time()
            return True
        except OSError:
            self.proc = None
            return False

    def _ensure_alive(self) -> bool:
        if self.proc and self.proc.poll() is None and self.proc.stdout:
            return True
        self.close()
        return self._open_process()

    def read_pcm(self, seconds: int) -> bytes:
        # 16kHz * 1 canal * 16bit (2 bytes)
        need_bytes = max(1, seconds) * 16000 * 2
        with self.lock:
            if not self._ensure_alive() or not self.proc or not self.proc.stdout:
                return b""

            for _ in range(2):
                data = bytearray()
                start = time.time()
                deadline = start + max(8, seconds + 8)

                while len(data) < need_bytes and time.time() < deadline:
                    chunk = self.proc.stdout.read(min(4096, need_bytes - len(data)))
                    if not chunk:
                        # stream caido/EOF, reintentar apertura
                        if not self._ensure_alive() or not self.proc or not self.proc.stdout:
                            break
                        continue
                    data.extend(chunk)

                if data:
                    return bytes(data)

                # Reintento total de proceso para el siguiente ciclo interno
                self.close()
                self._open_process()

            return b""

    def close(self) -> None:
        proc = self.proc
        self.proc = None
        if not proc:
            return
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _get_reader(channel: str) -> ContinuousAudioReader:
    reader = _READERS.get(channel)
    if reader is None:
        reader = ContinuousAudioReader(channel)
        _READERS[channel] = reader
    return reader


def _get_rt_state(channel: str) -> RealtimeTranscriptionState:
    state = _RT_STATES.get(channel)
    if state is None:
        state = RealtimeTranscriptionState()
        _RT_STATES[channel] = state
    return state


def pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Convierte PCM raw int16 mono a bytes de archivo WAV en memoria."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def transcribir_con_groq(wav_bytes: bytes, idioma: str = "es") -> str:
    """Transcribe audio WAV via Groq API (whisper-large-v3-turbo). Rapido y sin GPU."""
    import requests as _req
    try:
        resp = _req.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")},
            data={"model": GROQ_WHISPER_MODEL, "language": idioma, "response_format": "text"},
            timeout=20,
        )
        if resp.status_code == 200:
            texto = re.sub(r"\s+", " ", (resp.text or "").strip())
            if not texto:
                return ""
            texto_lc = texto.lower()
            frases_ruido = ("no tengo audio", "sin audio", "audio no disponible", "no se escucha", "gracias por ver")
            if any(f in texto_lc for f in frases_ruido):
                return ""
            palabras = re.findall(r"[a-zA-Z\u00c0-\u024f]+", texto)
            if len(palabras) < 2:
                return ""
            return texto
        print(f"[Groq] Error {resp.status_code}: {(resp.text or '')[:200]}")
        return ""
    except Exception as exc:
        print(f"[Groq] Error en transcripcion: {exc}")
        return ""


def resolver_ffmpeg() -> str:
    if FFMPEG_PATH:
        return FFMPEG_PATH
    return shutil.which("ffmpeg") or ""


def get_stream_url(channel: str) -> str:
    """Obtiene la URL HLS del stream usando streamlink."""
    ahora = time.time()
    cached = _STREAM_URL_CACHE.get(channel)
    if cached and (ahora - cached[1]) < _STREAM_URL_TTL_SEG:
        return cached[0]

    canal = channel.strip().lstrip("@")
    target_url = f"https://twitch.tv/{canal}"

    # Intentamos primero audio_only (menor latencia) y fallback a best.
    # --twitch-low-latency fue eliminado en streamlink 5+, no se usa.
    intents = [
        [
            sys.executable,
            "-m",
            "streamlink",
            "--loglevel",
            "error",
            "--hls-live-edge",
            "1",
            "--stream-url",
            target_url,
            "audio_only",
        ],
        [
            sys.executable,
            "-m",
            "streamlink",
            "--loglevel",
            "error",
            "--hls-live-edge",
            "1",
            "--stream-url",
            target_url,
            "best",
        ],
    ]

    last_err = ""
    for cmd in intents:
        try:
            proc = subprocess.run(
                cmd,
                text=True,
                timeout=20,
                capture_output=True,
                check=False,
            )
            if proc.returncode == 0:
                url = (proc.stdout or "").strip()
                if url:
                    _STREAM_URL_CACHE[channel] = (url, ahora)
                    return url

            salida = (proc.stderr or proc.stdout or "").strip()
            if salida:
                last_err = salida
        except Exception as e:
            last_err = str(e)

    if last_err:
        print(f"[Whisper] Error obteniendo URL del stream: {last_err}")
    else:
        print("[Whisper] Error obteniendo URL del stream: sin detalles (canal offline o streamlink).")
    return ""


def grabar_audio_hls(url: str, duracion_seg: int, archivo_salida: str) -> bool:
    """Graba N segundos de audio del stream HLS a un archivo wav."""
    ffmpeg_bin = resolver_ffmpeg()
    if not ffmpeg_bin:
        print("[Whisper] ffmpeg no encontrado. Instala ffmpeg o define FFMPEG_PATH en config.env")
        return False

    cmd = [
        ffmpeg_bin, "-y", "-i", url,
        "-t", str(duracion_seg),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        archivo_salida
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[Whisper] Error grabando audio: {e}")
        return False


def transcribir_audio(archivo: str, idioma: str = "es", modelo: str = "small") -> str:
    if GROQ_API_KEY:
        try:
            with open(archivo, "rb") as f:
                return transcribir_con_groq(f.read(), idioma=idioma)
        except Exception as exc:
            print(f"[Groq] Error leyendo archivo de audio: {exc}")
    if not _whisper_local:
        print("[Whisper] openai-whisper no instalado y no hay GROQ_API_KEY.")
        return ""
    model = _MODEL_CACHE.get(modelo)
    if model is None:
        model = _whisper_local.load_model(modelo)
        _MODEL_CACHE[modelo] = model

    # Ajustes para CPU/latencia menor.
    result = model.transcribe(
        archivo,
        language=idioma,
        fp16=False,
        temperature=0.0,
        condition_on_previous_text=False,
        without_timestamps=True,
    )
    return result.get("text", "")


def transcribir_pcm(
    pcm_bytes: bytes,
    idioma: str = "es",
    modelo: str = "small",
    realtime: bool = False,
) -> str:
    if not pcm_bytes:
        return ""

    if GROQ_API_KEY:
        return transcribir_con_groq(pcm_to_wav_bytes(pcm_bytes), idioma=idioma)

    if not _whisper_local:
        print("[Whisper] openai-whisper no instalado y no hay GROQ_API_KEY.")
        return ""

    model = _MODEL_CACHE.get(modelo)
    if model is None:
        model = _whisper_local.load_model(modelo)
        _MODEL_CACHE[modelo] = model

    # PCM int16 mono 16kHz -> float32 [-1, 1]
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if realtime:
        result = model.transcribe(
            audio,
            language=idioma,
            fp16=False,
            temperature=0.0,
            beam_size=1,
            best_of=1,
            no_speech_threshold=0.7,
            logprob_threshold=-1.2,
            compression_ratio_threshold=2.6,
            initial_prompt=WHISPER_INITIAL_PROMPT,
            condition_on_previous_text=False,
            without_timestamps=True,
        )
    else:
        result = model.transcribe(
            audio,
            language=idioma,
            fp16=False,
            temperature=(0.0, 0.2, 0.4),
            beam_size=5,
            best_of=5,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.4,
            initial_prompt=WHISPER_INITIAL_PROMPT,
            condition_on_previous_text=False,
            without_timestamps=True,
        )

    segments = result.get("segments") or []
    if segments:
        max_no_speech = 0.75 if realtime else 0.6
        min_avg_logprob = -1.8 if realtime else -1.3
        utiles = [s for s in segments if float(s.get("no_speech_prob", 1.0)) < max_no_speech]
        if not utiles:
            return ""
        avg_logprob = sum(float(s.get("avg_logprob", -10.0)) for s in utiles) / max(1, len(utiles))
        if avg_logprob < min_avg_logprob:
            return ""

    texto = (result.get("text") or "").strip()
    texto = re.sub(r"\s+", " ", texto)
    if not texto:
        return ""

    texto_lc = texto.lower()
    frases_ruido = (
        "no tengo audio",
        "sin audio",
        "audio no disponible",
        "no se escucha",
    )
    if any(f in texto_lc for f in frases_ruido):
        return ""

    palabras = re.findall(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ]+", texto)
    min_palabras = 2 if realtime else 3
    if len(palabras) < min_palabras:
        return ""

    return texto


def escuchar_y_transcribir_tiempo_real(
    channel: str,
    modelo: str = WHISPER_RT_MODEL,
    hop_seg: int = WHISPER_RT_HOP_SEG,
    window_seg: int = WHISPER_RT_WINDOW_SEG,
) -> str:
    """Subtitulado incremental: lee microbloques y transcribe una ventana deslizante."""
    ffmpeg_bin = resolver_ffmpeg()
    if not ffmpeg_bin:
        return "[Whisper] ffmpeg no encontrado (define FFMPEG_PATH)."

    hop_seg = max(1, int(hop_seg))
    window_seg = max(2, int(window_seg))

    reader = _get_reader(channel)
    state = _get_rt_state(channel)

    # Verificar URL antes de intentar leer (da diagnostico rapido si el canal esta offline).
    if not reader.proc or reader.proc.poll() is not None:
        url_test = get_stream_url(channel)
        if not url_test:
            return f"[Whisper] No se pudo obtener el stream de #{channel}. Canal offline o streamlink no disponible."

    pcm_chunk = reader.read_pcm(hop_seg)
    if not pcm_chunk:
        return f"[Whisper] Sin audio de #{channel}. Reintentando..."

    state.buffer.extend(pcm_chunk)

    bytes_por_seg = 16000 * 2
    max_buffer_bytes = max(10, window_seg * 3) * bytes_por_seg
    if len(state.buffer) > max_buffer_bytes:
        del state.buffer[:-max_buffer_bytes]

    window_bytes = window_seg * bytes_por_seg
    if len(state.buffer) < bytes_por_seg * 2:
        return ""

    pcm_window = bytes(state.buffer[-window_bytes:]) if len(state.buffer) >= window_bytes else bytes(state.buffer)
    texto = transcribir_pcm(pcm_window, idioma=IDIOMA, modelo=modelo, realtime=True).strip()
    if not texto:
        return ""

    texto = re.sub(r"\s+", " ", texto)
    anterior = state.last_text
    if texto == anterior:
        return ""

    # Si el nuevo texto extiende al anterior, devuelve solo el delta para subtitulado fluido.
    if anterior and texto.startswith(anterior):
        delta = texto[len(anterior):].strip(" ,.;:-")
        state.last_text = texto
        return delta if delta else ""

    state.last_text = texto
    return texto

def escuchar_y_transcribir(channel: str, segundos: int = 60, modelo: str = "small") -> str:
    url = get_stream_url(channel)
    if not url:
        return "[Whisper] No se pudo obtener el stream (revisa streamlink/canal en vivo)."
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        archivo = tmp.name
    try:
        ok = grabar_audio_hls(url, segundos, archivo)
        if not ok:
            return "[Whisper] No se pudo grabar el audio (revisa ffmpeg)."
        texto = transcribir_audio(archivo, idioma=IDIOMA, modelo=modelo)
        return texto.strip()
    finally:
        try:
            os.remove(archivo)
        except OSError:
            pass


def escuchar_y_transcribir_continuo(channel: str, segundos: int = 30, modelo: str = "small") -> str:
    """Lee audio continuo ya abierto y transcribe una ventana sin reconectar cada vez."""
    ffmpeg_bin = resolver_ffmpeg()
    if not ffmpeg_bin:
        return "[Whisper] ffmpeg no encontrado (define FFMPEG_PATH)."

    reader = _get_reader(channel)
    pcm = reader.read_pcm(segundos)
    if not pcm:
        return "[Whisper] Sin audio continuo disponible del stream."

    texto = transcribir_pcm(pcm, idioma=IDIOMA, modelo=modelo)
    return texto.strip()


def cerrar_escucha_continua(channel: str | None = None) -> None:
    if channel:
        reader = _READERS.pop(channel, None)
        if reader:
            reader.close()
        _RT_STATES.pop(channel, None)
        return

    for ch, reader in list(_READERS.items()):
        reader.close()
        _READERS.pop(ch, None)
    _RT_STATES.clear()


# Ejemplo de uso directo
if __name__ == "__main__":
    canal = os.getenv("TWITCH_CHANNEL", "gnomopiedra")
    print(f"Escuchando 30s de {canal}...")
    print(escuchar_y_transcribir(canal, segundos=30, modelo=WHISPER_MODEL))
