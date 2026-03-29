"""
Bot de Twitch con Ollama (IA local)
Ejecutar: python bot.py
"""

import os
import asyncio
import time
import re
import sys
import json
import subprocess
import inspect
from datetime import datetime
import aiohttp
from dotenv import load_dotenv
from twitchio.ext import commands

# ─── Cargar configuración ────────────────────────────────────────────────────
load_dotenv("config.env")

TOKEN      = os.getenv("TWITCH_TOKEN")        # oauth:xxxxxxxxxxxxxxxx
BOT_NICK   = os.getenv("TWITCH_BOT_NICK")     # tu usuario de Twitch
CHANNEL    = os.getenv("TWITCH_CHANNEL")      # canal donde vivirá el bot
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "").strip()
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
TWITCH_BOT_ID = os.getenv("TWITCH_BOT_ID", "").strip()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODELO     = os.getenv("OLLAMA_MODEL", "llama3")
IA_PROVIDER = os.getenv("IA_PROVIDER", "ollama").strip().lower()
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "x-ai/grok-4")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "bottwitch")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "").strip()
SYSTEM_PROMPT_FILE = os.getenv("SYSTEM_PROMPT_FILE", "system_prompt.txt").strip()
ENABLE_PROMPT_GUI = os.getenv("ENABLE_PROMPT_GUI", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "si",
    "on",
)
SYSTEM_PROMPT_A_FILE = os.getenv("SYSTEM_PROMPT_A_FILE", "system_prompt_a.txt").strip()
SYSTEM_PROMPT_B_FILE = os.getenv("SYSTEM_PROMPT_B_FILE", "system_prompt_b.txt").strip()
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "").strip()
OWNER_SYSTEM_PROMPT = os.getenv("OWNER_SYSTEM_PROMPT", "").strip()
OWNER_SYSTEM_PROMPT_FILE = os.getenv("OWNER_SYSTEM_PROMPT_FILE", "prompts/owner_system_prompt.txt").strip()
ACTIVE_PROMPT_SELECTOR_FILE = os.getenv("ACTIVE_PROMPT_SELECTOR_FILE", "active_system_prompt.txt").strip()
WHISPER_MODE_FILE = os.getenv("WHISPER_MODE_FILE", "whisper_mode_on.txt").strip()
AUTO_REPLY_MODE_FILE = os.getenv("AUTO_REPLY_MODE_FILE", "auto_reply_mode_on.txt").strip()
COMMAND_QUEUE_FILE = os.getenv("COMMAND_QUEUE_FILE", "gui_command_queue.txt").strip()
DEBUG_WEB_MODE_FILE = os.getenv("DEBUG_WEB_MODE_FILE", "runtime/debug_web_mode_on.txt").strip()
DEBUG_WEB_LOG_FILE = os.getenv("DEBUG_WEB_LOG_FILE", "runtime/debug_web.log").strip()
RESTART_CMD_TOKEN = "__RESTART_BOT__"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small").strip()
WHISPER_RT_MODEL = (os.getenv("WHISPER_RT_MODEL", "") or "").strip() or WHISPER_MODEL
WHISPER_SEGUNDOS = int(os.getenv("WHISPER_SEGUNDOS", "60"))
WHISPER_COOLDOWN = int(os.getenv("WHISPER_COOLDOWN", "30"))
WHISPER_REALTIME = os.getenv("WHISPER_REALTIME", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "si",
    "on",
)
WHISPER_RT_HOP_SEG = max(1, int(os.getenv("WHISPER_RT_HOP_SEG", "1")))
WHISPER_RT_WINDOW_SEG = max(2, int(os.getenv("WHISPER_RT_WINDOW_SEG", "3")))
WHISPER_CHAT_MIN_INTERVAL_SEG = max(1, int(os.getenv("WHISPER_CHAT_MIN_INTERVAL_SEG", "10")))
WHISPER_MIN_TRANSCRIPCION_CHARS = max(4, int(os.getenv("WHISPER_MIN_TRANSCRIPCION_CHARS", "10")))
WHISPER_LIVE_FILE = os.getenv("WHISPER_LIVE_FILE", "whisper_live.txt").strip()
CHANNEL_POLL_SEG = int(os.getenv("CHANNEL_POLL_SEG", "3"))
MODELO_PUBLICO = os.getenv("MODELO_PUBLICO", "Llama 3.2")
COOLDOWN   = int(os.getenv("COOLDOWN_SEG", "10"))
MAX_CHARS  = int(os.getenv("MAX_RESPUESTA_CHARS", "500"))
NUM_PREDICT    = int(os.getenv("OLLAMA_NUM_PREDICT", "220"))
TEMPERATURE    = float(os.getenv("OLLAMA_TEMPERATURE", "0.75"))
TOP_P          = float(os.getenv("OLLAMA_TOP_P", "0.92"))
TOP_K          = int(os.getenv("OLLAMA_TOP_K", "40"))
MIN_P          = float(os.getenv("OLLAMA_MIN_P", "0.05"))
REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))
REPEAT_LAST_N  = int(os.getenv("OLLAMA_REPEAT_LAST_N", "64"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT_SEG", "45"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "si",
    "on",
)
MEMORY_FILE = os.getenv("MEMORY_FILE", "conversation_memory.json").strip()
MEMORY_MAX_TURNS = max(0, int(os.getenv("MEMORY_MAX_TURNS", "6")))
MEMORY_MAX_CHARS_PER_TURN = max(80, int(os.getenv("MEMORY_MAX_CHARS_PER_TURN", "260")))
ENABLE_CONSOLE_TWITCH_CMDS = os.getenv("ENABLE_CONSOLE_TWITCH_CMDS", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "si",
    "on",
)
WEB_UI_HOST = os.getenv("WEB_UI_HOST", "127.0.0.1").strip() or "127.0.0.1"
WEB_UI_PORT = int(os.getenv("WEB_UI_PORT", "8787"))

# Historial de cooldown por usuario  {username: timestamp}
ultimo_uso: dict[str, float] = {}
BASE_DIR = os.path.dirname(__file__)
CONFIG_ENV_PATH = os.path.join(BASE_DIR, "config.env")


def resolver_ruta_config(ruta: str) -> str:
    # Resuelve rutas relativas tomando como base la carpeta del proyecto.
    if not ruta:
        return ""
    if os.path.isabs(ruta):
        return ruta
    return os.path.join(BASE_DIR, ruta)


def lanzar_panel_web_independiente() -> None:
    # Permite abrir la web aunque Twitch falle o no haya canal/token validos.
    if not ENABLE_PROMPT_GUI:
        return
    script_gui = os.path.join(BASE_DIR, "web_panel.py")
    if not os.path.exists(script_gui):
        print("[GUI] No se encontro web_panel.py. Se omite panel web.")
        return
    try:
        subprocess.Popen([sys.executable, script_gui], cwd=BASE_DIR)
        print(f"[GUI] Panel web iniciado en http://{WEB_UI_HOST}:{WEB_UI_PORT}")
    except Exception as exc:
        print(f"[GUI] No se pudo iniciar el panel web: {exc}")


MEMORY_PATH = resolver_ruta_config(MEMORY_FILE)
COMMAND_QUEUE_PATH = resolver_ruta_config(COMMAND_QUEUE_FILE)
DEBUG_WEB_MODE_PATH = resolver_ruta_config(DEBUG_WEB_MODE_FILE)
DEBUG_WEB_LOG_PATH = resolver_ruta_config(DEBUG_WEB_LOG_FILE)


def leer_texto(path: str) -> str:
    # Lectura segura: si falla, devuelve cadena vacia para no romper el flujo.
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def escribir_texto(path: str, contenido: str) -> bool:
    # Escritura segura usada por estados runtime (GUI/Whisper/modos).
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(contenido)
        return True
    except OSError:
        return False


def append_linea(path: str, texto: str) -> bool:
    # Escritura en append para logs y colas simples en runtime.
    try:
        dirpath = os.path.dirname(path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{texto}\n")
        return True
    except OSError:
        return False


def asegurar_archivo(path: str, contenido_inicial: str = "") -> None:
    # Crea archivo faltante con un valor por defecto para evitar checks repetidos.
    if not path or os.path.exists(path):
        return
    escribir_texto(path, contenido_inicial)


def leer_y_vaciar_lineas(path: str, max_lineas: int = 20) -> list[str]:
    # Cola simple por archivo: consume comandos y limpia el buffer en una sola pasada.
    if not path:
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            contenido = f.read()
    except OSError:
        return []

    if not contenido.strip():
        return []

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
    except OSError:
        pass

    lineas = [ln.strip() for ln in contenido.splitlines() if ln.strip()]
    return lineas[:max_lineas]


def prompt_activo_slot() -> str:
    # Normaliza el selector: cualquier valor distinto de B se considera A.
    selector_path = resolver_ruta_config(ACTIVE_PROMPT_SELECTOR_FILE)
    valor = leer_texto(selector_path).strip().upper()
    return "B" if valor == "B" else "A"


def leer_twitch_channel_config() -> str:
    """Lee TWITCH_CHANNEL desde config.env en caliente."""
    return leer_config_env_clave("TWITCH_CHANNEL")


def leer_config_env_clave(clave: str) -> str:
    """Lee una clave puntual desde config.env en caliente."""
    try:
        with open(CONFIG_ENV_PATH, "r", encoding="utf-8") as f:
            for linea in f:
                linea_limpia = linea.strip()
                if not linea_limpia or linea_limpia.startswith("#"):
                    continue
                if linea_limpia.startswith(f"{clave}="):
                    return linea_limpia.split("=", 1)[1].strip()
    except OSError:
        return ""
    return ""


def modelo_activo() -> str:
    """Devuelve el modelo según el proveedor activo."""
    return OPENROUTER_MODEL if IA_PROVIDER == "openrouter" else MODELO


def leer_prompt_desde_archivo() -> str:
    """Lee el prompt desde archivo si existe y tiene contenido."""
    if not SYSTEM_PROMPT_FILE:
        return ""

    ruta = resolver_ruta_config(SYSTEM_PROMPT_FILE)

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def obtener_prompt_sistema() -> str:
    """Devuelve el system prompt desde archivo o variable de entorno."""
    if ENABLE_PROMPT_GUI:
        selector_path = resolver_ruta_config(ACTIVE_PROMPT_SELECTOR_FILE)
        prompt_a_path = resolver_ruta_config(SYSTEM_PROMPT_A_FILE)
        prompt_b_path = resolver_ruta_config(SYSTEM_PROMPT_B_FILE)

        asegurar_archivo(prompt_a_path, "")
        asegurar_archivo(prompt_b_path, "")
        asegurar_archivo(selector_path, "A")

        slot = prompt_activo_slot()
        ruta_activa = prompt_b_path if slot == "B" else prompt_a_path
        prompt_slot = leer_texto(ruta_activa).strip()
        if prompt_slot:
            return prompt_slot

    prompt_archivo = leer_prompt_desde_archivo()
    if prompt_archivo:
        return prompt_archivo

    if SYSTEM_PROMPT:
        return SYSTEM_PROMPT
    return ""


def leer_owner_username_config() -> str:
    """Devuelve el owner actual leyendo config.env para aplicar cambios en caliente."""
    valor = leer_config_env_clave("OWNER_USERNAME") or OWNER_USERNAME
    return (valor or "").strip().lstrip("@").lower()


def leer_owner_prompt_desde_archivo() -> str:
    """Lee el prompt especifico del owner desde archivo dedicado."""
    ruta = resolver_ruta_config(OWNER_SYSTEM_PROMPT_FILE)
    if not ruta:
        return ""
    asegurar_archivo(ruta, "")
    return leer_texto(ruta).strip()


def obtener_prompt_sistema_para_usuario(username: str) -> str:
    """Usa prompt especial para owner; resto usa A/B o prompt global normal."""
    usuario = (username or "").strip().lstrip("@").lower()
    owner = leer_owner_username_config()
    if owner and usuario and usuario == owner:
        prompt_owner = leer_owner_prompt_desde_archivo()
        if prompt_owner:
            return prompt_owner
        if OWNER_SYSTEM_PROMPT:
            return OWNER_SYSTEM_PROMPT
    return obtener_prompt_sistema()


def normalizar_memory_key(memory_key: str) -> str:
    clave = (memory_key or "global").strip().lower()
    return re.sub(r"[^a-z0-9:_-]+", "_", clave) or "global"


def cargar_memoria() -> dict[str, list[dict[str, str]]]:
    # Memoria persistente por contexto (usuario/consola/whisper).
    if not MEMORY_ENABLED or MEMORY_MAX_TURNS <= 0:
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def guardar_memoria(data: dict[str, list[dict[str, str]]]) -> None:
    # Guarda sin interrumpir el bot si hay problemas de IO.
    if not MEMORY_ENABLED or MEMORY_MAX_TURNS <= 0:
        return
    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


def obtener_turnos_memoria(memory_key: str) -> list[dict[str, str]]:
    # Sanea estructura para evitar que memoria corrupta ensucie el prompt.
    data = cargar_memoria()
    clave = normalizar_memory_key(memory_key)
    turnos = data.get(clave, [])
    if not isinstance(turnos, list):
        return []

    validos: list[dict[str, str]] = []
    for turno in turnos[-MEMORY_MAX_TURNS:]:
        if not isinstance(turno, dict):
            continue
        usuario = str(turno.get("user", "")).strip()
        asistente = str(turno.get("assistant", "")).strip()
        if usuario and asistente:
            validos.append({"user": usuario, "assistant": asistente})
    return validos


def respuesta_memorizable(texto: str) -> bool:
    limpio = (texto or "").strip()
    if not limpio:
        return False
    lc = limpio.lower()
    if lc.startswith("error:"):
        return False
    # Evita memorizar coletillas/bromas que luego se repiten en bucle.
    if re.match(r"^\s*ja+\b", lc):
        return False
    if "fundiendo oro robado de latam" in lc:
        return False

    # No memorizar respuestas vacias de valor tipo "no se" sin contexto.
    if re.fullmatch(r"(?:no\s+se|no\s+s[ée]\s+|no\s+lo\s+s[ée])", lc.strip(" .!?¡¿")):
        return False
    return True


def limpiar_texto_memoria(texto: str) -> str:
    t = " ".join((texto or "").split()).strip()
    if not t:
        return ""
    # Quita arranques tipo "Ja!" para reducir la deriva de estilo.
    t = re.sub(r"^\s*[¡!]?ja+[!¡,.:;\-\s]+", "", t, flags=re.IGNORECASE)
    if len(t) > MEMORY_MAX_CHARS_PER_TURN:
        t = t[:MEMORY_MAX_CHARS_PER_TURN].rstrip()
    return t


def registrar_turno_memoria(memory_key: str, prompt: str, respuesta: str) -> None:
    if not MEMORY_ENABLED or MEMORY_MAX_TURNS <= 0:
        return

    prompt_limpio = limpiar_texto_memoria(prompt)
    respuesta_limpia = limpiar_texto_memoria(respuesta)
    if not prompt_limpio or not respuesta_memorizable(respuesta_limpia):
        return

    data = cargar_memoria()
    clave = normalizar_memory_key(memory_key)
    turnos = data.get(clave, [])
    if not isinstance(turnos, list):
        turnos = []

    # Mantiene solo una ventana corta para reducir deriva de estilo/costo de contexto.
    turnos.append({"user": prompt_limpio, "assistant": respuesta_limpia})
    data[clave] = turnos[-MEMORY_MAX_TURNS:]
    guardar_memoria(data)


def construir_messages_openrouter(prompt_sistema: str, prompt: str, memory_key: str) -> list[dict[str, str]]:
    # Formato estilo chat para OpenRouter.
    messages: list[dict[str, str]] = []
    if prompt_sistema:
        messages.append({"role": "system", "content": prompt_sistema})

    for turno in obtener_turnos_memoria(memory_key):
        messages.append({"role": "user", "content": turno["user"]})
        messages.append({"role": "assistant", "content": turno["assistant"]})

    messages.append({"role": "user", "content": prompt})
    return messages


def construir_prompt_ollama(prompt_sistema: str, prompt: str, memory_key: str) -> str:
    # Formato plain-text dialogado para endpoint /api/generate de Ollama.
    bloques: list[str] = []
    if prompt_sistema:
        bloques.append(prompt_sistema)

    for turno in obtener_turnos_memoria(memory_key):
        bloques.append(f"Usuario: {turno['user']}\nAsistente: {turno['assistant']}")

    bloques.append(f"Usuario: {prompt}\nAsistente:")
    return "\n\n".join(b for b in bloques if b)


async def preguntar_openrouter(prompt: str, memory_key: str = "", prompt_sistema_override: str | None = None) -> str:
    """Envía un prompt a OpenRouter y devuelve la respuesta como texto."""
    if not OPENROUTER_API_KEY:
        return "Error: falta OPENROUTER_API_KEY en config.env"

    prompt_sistema = prompt_sistema_override if prompt_sistema_override is not None else obtener_prompt_sistema()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": OPENROUTER_APP_NAME,
    }
    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL

    # Se comparte temperatura/top_p con Ollama para mantener comportamiento similar.
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": construir_messages_openrouter(prompt_sistema, prompt, memory_key),
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
    }

    timeout = aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT, connect=5, sock_read=OLLAMA_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(OPENROUTER_URL, json=payload, headers=headers) as resp:
                if resp.status >= 400:
                    try:
                        data = await resp.json()
                        detalle = data.get("error", {}).get("message", "")
                    except Exception:
                        detalle = await resp.text()
                    return f"Error de OpenRouter: {(detalle or f'HTTP {resp.status}').strip()}"

                data = await resp.json()

        choices = data.get("choices") or []
        if not choices:
            return "OpenRouter no devolvió opciones de respuesta."

        contenido = choices[0].get("message", {}).get("content", "")
        if isinstance(contenido, list):
            partes = []
            for item in contenido:
                if isinstance(item, dict) and item.get("type") == "text":
                    partes.append(item.get("text", ""))
            contenido = "".join(partes)

        texto = (contenido or "").strip()
        if respuesta_memorizable(texto):
            registrar_turno_memoria(memory_key, prompt, texto)
        return texto if texto else "OpenRouter no devolvió respuesta."

    except aiohttp.ClientConnectorError:
        return "Error: no se pudo conectar con OpenRouter."
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
        return "Error: OpenRouter tardó demasiado en responder."
    except Exception as exc:
        return f"Error inesperado: {exc}"


async def preguntar_modelo(prompt: str, memory_key: str = "", prompt_sistema_override: str | None = None) -> str:
    """Rutea la pregunta al proveedor configurado."""
    # Punto unico de enrutamiento para no duplicar logica en comandos/eventos.
    if IA_PROVIDER == "openrouter":
        return await preguntar_openrouter(prompt, memory_key=memory_key, prompt_sistema_override=prompt_sistema_override)
    return await preguntar_ollama(prompt, memory_key=memory_key, prompt_sistema_override=prompt_sistema_override)


# ─── Llamada a Ollama ─────────────────────────────────────────────────────────
async def preguntar_ollama(prompt: str, memory_key: str = "", prompt_sistema_override: str | None = None) -> str:
    """Envía un prompt a Ollama y devuelve la respuesta como texto."""
    prompt_sistema = prompt_sistema_override if prompt_sistema_override is not None else obtener_prompt_sistema()

    # Llamada no-stream para simplificar control de errores y post-procesado.
    payload = {
        "model": MODELO,
        "prompt": construir_prompt_ollama(prompt_sistema, prompt, memory_key),
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "num_predict": NUM_PREDICT,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "top_k": TOP_K,
            "min_p": MIN_P,
            "repeat_penalty": REPEAT_PENALTY,
            "repeat_last_n": REPEAT_LAST_N,
        },
    }

    timeout = aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT, connect=5, sock_read=OLLAMA_TIMEOUT)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                if resp.status >= 400:
                    try:
                        detalle = (await resp.json()).get("error", "")
                    except Exception:
                        detalle = await resp.text()
                    return f"Error de Ollama: {(detalle or f'HTTP {resp.status}').strip()}"

                data = await resp.json()

        texto = data.get("response", "").strip()
        if respuesta_memorizable(texto):
            registrar_turno_memoria(memory_key, prompt, texto)
        return texto if texto else "Ollama no devolvió respuesta."

    except aiohttp.ClientConnectorError:
        return "Error: Ollama no está corriendo. Ejecuta 'ollama serve' en otra terminal."
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
        return "Error: Ollama tardó demasiado en responder."
    except Exception as exc:
        return f"Error inesperado: {exc}"


def limitar_500(texto: str) -> str:
    """Aplica un limite duro de 500 caracteres a cualquier mensaje."""
    limpio = " ".join(texto.split())
    if len(limpio) <= 500:
        return limpio
    return limpio[:500].rstrip()


def normalizar_identidad(texto: str) -> str:
    """Evita que el modelo se presente con identidades no deseadas."""
    t = texto
    reemplazos = {
        "Nidum AI": "bot de Twitch basado en Llama 3.2",
        "Nidum": "bot basado en Llama 3.2",
        "asistente de Python": "asistente de Twitch",
    }
    for viejo, nuevo in reemplazos.items():
        t = t.replace(viejo, nuevo)

    # Evita coletillas de arranque que acaban en bucles por memoria.
    t = re.sub(r"^\s*[¡!]?ja+[!¡,.:;\-\s]+", "", t, flags=re.IGNORECASE)

    # Si la salida cae en frases comodín o de desconocimiento, la descartamos.
    frases_bloqueadas = (
        "no tengo suficiente informacion",
        "no tengo informacion",
        "no puedo confirmar",
        "no dispongo de",
        "fundiendo oro robado de latam",
    )
    t_lc = t.lower()
    if any(f in t_lc for f in frases_bloqueadas):
        return ""

    # Solo bloquea "no se" cuando toda la salida es basicamente eso.
    base = t_lc.strip(" .!?¡¿")
    if re.fullmatch(r"(?:no\s+se|no\s+s[ée]|no\s+lo\s+s[ée])", base):
        return ""

    # Limpia auto-dialogos y repeticiones tipo "pregunta-respuesta-adios".
    disparadores_dialogo = (
        "necesitas ayuda",
        "necesita mas ayuda",
        "estoy bien, gracias",
        "perfecto",
        "adios adios",
    )
    t_lc = t.lower()
    if any(d in t_lc for d in disparadores_dialogo):
        partes = re.split(r"(?<=[.!?])\s+", t)
        t = partes[0].strip() if partes else t

    # Reduce repeticion semantica quedandose con hasta 2 frases unicas.
    partes = re.split(r"(?<=[.!?])\s+", t)
    unicas: list[str] = []
    vistas: set[str] = set()
    for p in partes:
        p_limpia = p.strip()
        if not p_limpia:
            continue
        firma = re.sub(r"[^a-z0-9]+", "", p_limpia.lower())
        if not firma or firma in vistas:
            continue
        vistas.add(firma)
        unicas.append(p_limpia)
        if len(unicas) >= 2:
            break

    return " ".join(unicas) if unicas else t


def limpiar_fuera_de_tema(pregunta: str, respuesta: str) -> str:
    """Quita auto-presentaciones y coletillas si no preguntaron por el bot."""
    r = respuesta
    r = re.sub(r"(?i)^\s*(claro,?\s*)?soy\s+.*?bot.*?(?:[.!?]|$)\s*", "", r)
    r = re.sub(r"(?i)\bsoy\s+.*?bot.*?(?:[.!?]|$)", "", r)
    r = re.sub(
        r"(?i)¿\s*qu[ií]en\s+eres\s+t[uú]\s*\?",
        "",
        r,
    )
    r = re.sub(r"(?i)¿\s*c[oó]mo\s+puedo\s+ayudarte\??", "", r)
    r = re.sub(r"(?i)\bnecesitas\s+ayuda\b\??", "", r)
    r = re.sub(r"(?i)\bperfecto!?\b", "", r)
    r = re.sub(r"(?i)\bad[ií]os(?:\s+ad[ií]os)*\b", "", r)
    r = re.sub(r"\s+", " ", r).strip(" .")
    return r


def recortar_para_twitch(respuesta: str, prefijo: str = "") -> str:
    """Ajusta la respuesta al limite real de Twitch con prefijo opcional."""
    limite_total = 500
    limite_respuesta = min(MAX_CHARS, limite_total - len(prefijo))

    if limite_respuesta <= 0:
        return prefijo[:limite_total]

    texto = " ".join(respuesta.split())
    texto = texto.replace("Usuario:", "").replace("Asistente:", "").strip()
    texto = normalizar_identidad(texto)
    if not texto:
        return ""

    if len(texto) <= limite_respuesta:
        return limitar_500(f"{prefijo}{texto}")

    if limite_respuesta <= 3:
        return limitar_500(f"{prefijo}{texto[:limite_respuesta]}")

    return limitar_500(f"{prefijo}{texto[:limite_respuesta].rstrip()}")


async def enviar_seguro(ctx: commands.Context, texto: str) -> None:
    """Envia mensajes cumpliendo siempre el limite de Twitch."""
    await ctx.send(limitar_500(texto))


# ─── Bot ──────────────────────────────────────────────────────────────────────
class Bot(commands.Bot):

    def __init__(self):
        # Parametros base compatibles con TwitchIO v2 y v3.
        init_kwargs = dict(
            token=TOKEN,
            nick=BOT_NICK,
            prefix="!",
            initial_channels=[CHANNEL],
        )

        # Compatibilidad con TwitchIO v3 (requiere client_id, client_secret y bot_id)
        firma = inspect.signature(commands.Bot.__init__)
        params = firma.parameters
        requiere_v3 = all(k in params for k in ("client_id", "client_secret", "bot_id"))

        if requiere_v3:
            faltantes = []
            if not TWITCH_CLIENT_ID:
                faltantes.append("TWITCH_CLIENT_ID")
            if not TWITCH_CLIENT_SECRET:
                faltantes.append("TWITCH_CLIENT_SECRET")
            if not TWITCH_BOT_ID:
                faltantes.append("TWITCH_BOT_ID")

            if faltantes:
                raise RuntimeError(
                    "TwitchIO v3 detectado. Faltan variables en config.env: "
                    + ", ".join(faltantes)
                )

            init_kwargs["client_id"] = TWITCH_CLIENT_ID
            init_kwargs["client_secret"] = TWITCH_CLIENT_SECRET
            init_kwargs["bot_id"] = TWITCH_BOT_ID

        super().__init__(**init_kwargs)
        self.current_channel = CHANNEL
        self.console_task: asyncio.Task | None = None
        self.prompt_gui_process: subprocess.Popen | None = None
        self.whisper_task: asyncio.Task | None = None
        self.config_watch_task: asyncio.Task | None = None
        self._whisper_cooldown = False
        self._ultimo_whisper_chat_ts = 0.0
        self._ultimo_whisper_chat_txt = ""
        self._whisper_mode_cache = False
        # Cola de comandos generados desde la GUI.
        self.path_command_queue = COMMAND_QUEUE_PATH
        asegurar_archivo(self.path_command_queue, "")
        asegurar_archivo(DEBUG_WEB_MODE_PATH, "0")
        asegurar_archivo(DEBUG_WEB_LOG_PATH, "")
        asegurar_archivo(resolver_ruta_config(WHISPER_MODE_FILE), "0")
        self._whisper_mode_cache = leer_texto(resolver_ruta_config(WHISPER_MODE_FILE)).strip() == "1"
    def _leer_whisper_activado(self) -> bool:
        path = resolver_ruta_config(WHISPER_MODE_FILE)
        asegurar_archivo(path, "0")
        val = leer_texto(path).strip()

        # Evita falsos apagados por lecturas transitorias vacias/parciales.
        if val == "1":
            self._whisper_mode_cache = True
            return True
        if val == "0":
            self._whisper_mode_cache = False
            return False
        return self._whisper_mode_cache

    def _leer_auto_reply_activado(self) -> bool:
        path = resolver_ruta_config(AUTO_REPLY_MODE_FILE)
        asegurar_archivo(path, "0")
        val = leer_texto(path).strip()
        return val == "1"

    def _leer_debug_web_activado(self) -> bool:
        asegurar_archivo(DEBUG_WEB_MODE_PATH, "0")
        val = leer_texto(DEBUG_WEB_MODE_PATH).strip()
        return val == "1"

    def _registrar_debug_web(self, entrada: str, salida: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        append_linea(DEBUG_WEB_LOG_PATH, f"[{stamp}] IN: {entrada}")
        append_linea(DEBUG_WEB_LOG_PATH, f"[{stamp}] OUT: {salida}")

    async def _enviar_gui_o_chat(self, canal, origen: str, entrada: str, mensaje: str, tag: str) -> None:
        # En modo debug web, no publica en Twitch y deja trazas en runtime/debug_web.log.
        if origen == "gui" and self._leer_debug_web_activado():
            self._registrar_debug_web(entrada, mensaje)
            print(f"[DEBUG-WEB] {tag} -> {mensaje}")
            return
        await canal.send(mensaje)

    def _escribir_whisper_live(self, texto: str) -> None:
        path = resolver_ruta_config(WHISPER_LIVE_FILE)
        escribir_texto(path, texto)

    async def _cambiar_canal(self, nuevo_canal: str) -> None:
        nuevo = (nuevo_canal or "").strip()
        if not nuevo:
            return
        if nuevo.lower() == (self.current_channel or "").lower():
            return

        anterior = self.current_channel
        try:
            if anterior:
                await self.part_channels([anterior])
                try:
                    from audio_whisper import cerrar_escucha_continua
                    await asyncio.to_thread(cerrar_escucha_continua, anterior)
                except Exception:
                    pass
        except Exception as exc:
            print(f"[Canal] No se pudo salir de #{anterior}: {exc}")

        try:
            await self.join_channels([nuevo])
            self.current_channel = nuevo
            print(f"[Canal] Cambiado en caliente a #{self.current_channel}")
        except Exception as exc:
            print(f"[Canal] Error al cambiar a #{nuevo}: {exc}")
            # Si falla, intentamos volver al canal anterior
            if anterior and anterior.lower() != nuevo.lower():
                try:
                    await self.join_channels([anterior])
                    self.current_channel = anterior
                except Exception:
                    pass

    async def _monitor_config_runtime(self) -> None:
        """Monitorea cambios de canal y estado Whisper desde archivos de config."""
        while True:
            # Cada bloque se maneja por separado para evitar que un error
            # de Twitch/canal impida activar Whisper o procesar comandos GUI.
            try:
                canal_cfg = leer_twitch_channel_config()
                if canal_cfg:
                    await self._cambiar_canal(canal_cfg)
            except Exception as exc:
                print(f"[Runtime] Error actualizando canal: {exc}")

            try:
                await self._procesar_comandos_gui()
            except Exception as exc:
                print(f"[Runtime] Error procesando comandos GUI: {exc}")

            try:
                whisper_on = self._leer_whisper_activado()
                if whisper_on and (self.whisper_task is None or self.whisper_task.done()):
                    self.whisper_task = asyncio.create_task(self._ciclo_whisper())
            except Exception as exc:
                print(f"[Runtime] Error controlando Whisper: {exc}")

            await asyncio.sleep(max(1, CHANNEL_POLL_SEG))

    async def _ciclo_whisper(self):
        print("[Whisper] Ciclo de escucha/respuesta iniciado.")
        if WHISPER_REALTIME:
            self._escribir_whisper_live("[Whisper] Subtitulado en vivo iniciado...")
        else:
            self._escribir_whisper_live("[Whisper] Esperando audio...")
        while self._leer_whisper_activado():
            if self._whisper_cooldown:
                await asyncio.sleep(1)
                continue
            try:
                from audio_whisper import (
                    escuchar_y_transcribir,
                    escuchar_y_transcribir_continuo,
                    escuchar_y_transcribir_tiempo_real,
                )
                canal_objetivo = self.current_channel
                # Modo realtime: hop corto + ventana deslizante para subtitulado casi en vivo.
                if WHISPER_REALTIME:
                    texto = await asyncio.to_thread(
                        escuchar_y_transcribir_tiempo_real,
                        canal_objetivo,
                        WHISPER_RT_MODEL,
                        WHISPER_RT_HOP_SEG,
                        WHISPER_RT_WINDOW_SEG,
                    )
                else:
                    print(f"[Whisper] Escuchando {WHISPER_SEGUNDOS}s de {canal_objetivo}...")
                    self._escribir_whisper_live(f"[Whisper] Escuchando {WHISPER_SEGUNDOS}s de {canal_objetivo}...")
                    texto = await asyncio.to_thread(
                        escuchar_y_transcribir_continuo,
                        canal_objetivo,
                        WHISPER_SEGUNDOS,
                        WHISPER_MODEL,
                    )

                    # Fallback: si el stream continuo falla puntualmente, intentar una captura normal.
                    if "Sin audio continuo" in (texto or ""):
                        texto = await asyncio.to_thread(
                            escuchar_y_transcribir,
                            canal_objetivo,
                            WHISPER_SEGUNDOS,
                            WHISPER_MODEL,
                        )

                if texto:
                    if texto.startswith("[Whisper]"):
                        # Mensaje de diagnóstico, mostrarlo en la web y dar pausa.
                        self._escribir_whisper_live(texto)
                        await asyncio.sleep(3)
                    else:
                        print(f"[Whisper] Transcripción: {texto}")
                        self._escribir_whisper_live(texto)
                elif not WHISPER_REALTIME:
                    self._escribir_whisper_live("[Whisper] Sin transcripción")

                texto_limpio = (texto or "").strip()
                if texto_limpio and not texto_limpio.startswith("[Whisper]") and len(texto_limpio) >= WHISPER_MIN_TRANSCRIPCION_CHARS:
                    canal = await self._obtener_canal()
                    if canal:
                        ahora = time.time()
                        puede_enviar = True
                        if WHISPER_REALTIME:
                            # Anti-spam: no repetir mismo texto y respetar intervalo minimo.
                            if texto_limpio == self._ultimo_whisper_chat_txt:
                                puede_enviar = False
                            if (ahora - self._ultimo_whisper_chat_ts) < WHISPER_CHAT_MIN_INTERVAL_SEG:
                                puede_enviar = False

                        if puede_enviar:
                            respuesta = await preguntar_modelo(
                                texto_limpio,
                                memory_key=f"whisper:{self.current_channel}",
                            )
                            respuesta = limpiar_fuera_de_tema(texto_limpio, respuesta)
                            mensaje = recortar_para_twitch(respuesta)
                            if mensaje:
                                await canal.send(mensaje)
                                self._ultimo_whisper_chat_ts = ahora
                                self._ultimo_whisper_chat_txt = texto_limpio
                    else:
                        self._escribir_whisper_live(
                            f"[Whisper] Activo sin canal Twitch conectado. Ultima transcripcion: {texto_limpio[:220]}"
                        )
                else:
                    if not WHISPER_REALTIME:
                        print("[Whisper] Nada relevante transcrito.")
            except ModuleNotFoundError as exc:
                msg = (
                    f"[Whisper] Error: {exc}. Python actual: {sys.executable}. "
                    "Instala con: .venv\\Scripts\\python.exe -m pip install openai-whisper"
                )
                print(msg)
                self._escribir_whisper_live(msg)
                await asyncio.sleep(5)
                continue
            except Exception as exc:
                print(f"[Whisper] Error: {exc}")
                self._escribir_whisper_live(f"[Whisper] Error: {exc}")

            # Si WHISPER_COOLDOWN es 0, vuelve a escuchar inmediatamente.
            if WHISPER_COOLDOWN > 0:
                self._whisper_cooldown = True
                await asyncio.sleep(WHISPER_COOLDOWN)
                self._whisper_cooldown = False

            if not WHISPER_REALTIME:
                self._escribir_whisper_live(f"[Whisper] Reescuchando #{self.current_channel}...")
        print("[Whisper] Ciclo de escucha/respuesta detenido.")
        try:
            from audio_whisper import cerrar_escucha_continua
            await asyncio.to_thread(cerrar_escucha_continua, self.current_channel)
        except Exception:
            pass
        self._escribir_whisper_live("[Whisper] Modo desactivado")

    def _lanzar_gui_prompts(self) -> None:
        if not ENABLE_PROMPT_GUI:
            return

        if self.prompt_gui_process and self.prompt_gui_process.poll() is None:
            return

        script_gui = os.path.join(BASE_DIR, "web_panel.py")
        if not os.path.exists(script_gui):
            print("[GUI] No se encontro web_panel.py. Se omite panel web.")
            return

        # Reusa el mismo interprete del bot para evitar desalineaciones de entorno.
        exe = sys.executable

        try:
            self.prompt_gui_process = subprocess.Popen(
                [exe, script_gui],
                cwd=BASE_DIR
            )
            print("[GUI] Panel web iniciado.")
        except Exception as exc:
            print(f"[GUI] No se pudo iniciar el panel web: {exc}")

    async def _obtener_canal(self):
        canal = self.get_channel(self.current_channel)
        if canal is None:
            await asyncio.sleep(0.2)
            canal = self.get_channel(self.current_channel)
        return canal

    async def _procesar_comandos_gui(self) -> None:
        # Ejecuta comandos en lote para minimizar latencia entre GUI y bot.
        comandos = leer_y_vaciar_lineas(self.path_command_queue, max_lineas=25)
        if not comandos:
            return

        for cmd in comandos:
            try:
                if cmd.strip().upper() == RESTART_CMD_TOKEN:
                    await self._reiniciar_bot_completo()
                    return
                await self._ejecutar_comando_consola(cmd, origen="gui")
            except Exception as exc:
                print(f"[GUI-CMD] Error ejecutando '{cmd}': {exc}")

    async def _reiniciar_bot_completo(self) -> None:
        print("[GUI] Reinicio completo solicitado desde la interfaz.")
        try:
            from audio_whisper import cerrar_escucha_continua
            await asyncio.to_thread(cerrar_escucha_continua, self.current_channel)
        except Exception:
            pass

        # Evita GUI duplicada en el relanzamiento.
        proc = self.prompt_gui_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        await asyncio.sleep(0.2)
        # Reemplaza el proceso actual por uno nuevo (reinicio completo real).
        script = os.path.abspath(__file__)
        os.execv(sys.executable, [sys.executable, script])

    async def _ejecutar_comando_consola(self, texto: str, origen: str = "console") -> None:
        # Esta ruta es usada tanto por consola local como por comandos encolados de GUI.
        canal = await self._obtener_canal()
        if canal is None:
            print("[CMD] Canal no disponible todavía. Intenta de nuevo en unos segundos.")
            return

        partes = texto.split(" ", 1)
        comando = partes[0].lower()
        argumento = partes[1].strip() if len(partes) > 1 else ""

        if comando == "!hola":
            msg = "Hola, soy darigptcito. Usa !ia seguido de texto para hablar conmigo."
            await self._enviar_gui_o_chat(canal, origen, texto, msg, "!hola")
            print("[CMD] Enviado !hola al chat")
            return

        if comando == "!ping":
            msg = "pong!"
            await self._enviar_gui_o_chat(canal, origen, texto, msg, "!ping")
            print("[CMD] Enviado !ping al chat")
            return

        if comando in ("!modelo", "!model"):
            msg = modelo_activo()
            await self._enviar_gui_o_chat(canal, origen, texto, msg, "!modelo")
            print("[CMD] Enviado !modelo al chat")
            return

        if comando == "!ia":
            if not argumento:
                print("[CMD] Uso correcto: !ia <tu pregunta>")
                return
            respuesta = await preguntar_modelo(argumento, memory_key="console")
            respuesta = limpiar_fuera_de_tema(argumento, respuesta)
            mensaje = recortar_para_twitch(respuesta)
            if mensaje:
                await self._enviar_gui_o_chat(canal, origen, texto, mensaje, "!ia")
                print("[CMD] Enviado respuesta de !ia al chat")
            else:
                print("[CMD] La IA no devolvió texto útil para !ia")
            return

        if comando == "!ias":
            if not argumento:
                print("[CMD] Uso correcto: !ias <tu pregunta>")
                return
            respuesta = await preguntar_modelo(argumento, memory_key="console")
            respuesta = limpiar_fuera_de_tema(argumento, respuesta)
            mensaje = recortar_para_twitch(respuesta, prefijo="!speak ")
            if mensaje:
                await self._enviar_gui_o_chat(canal, origen, texto, mensaje, "!ias")
                print("[CMD] Enviado respuesta de !ias al chat")
            else:
                print("[CMD] La IA no devolvió texto útil para !ias")
            return

        if comando == "!responde":
            if not argumento:
                print("[CMD] Uso correcto: !responde <texto>")
                return
            respuesta = await preguntar_modelo(argumento, memory_key="console")
            respuesta = limpiar_fuera_de_tema(argumento, respuesta)
            mensaje = recortar_para_twitch(respuesta)
            if mensaje:
                await self._enviar_gui_o_chat(canal, origen, texto, mensaje, "!responde")
                print("[CMD] Enviado respuesta de !responde al chat")
            else:
                print("[CMD] La IA no devolvió texto útil para !responde")
            return

        await self._enviar_gui_o_chat(canal, origen, texto, texto, "texto")
        print("[CMD] Enviado texto directo al chat")

    async def _loop_consola_twitch(self) -> None:
        print("[CMD] Modo consola Twitch activo. Escribe !hola, !ia, !ias, !responde, !modelo, !ping o texto libre.")
        print("[CMD] Escribe /salir para cerrar solo el modo consola (el bot sigue corriendo).")
        while True:
            try:
                texto = (await asyncio.to_thread(input, "[CMD->Twitch] ")).strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[CMD] Consola cerrada.")
                break

            if not texto:
                continue

            if texto.lower() in ("/salir", "/exit", "/quit"):
                print("[CMD] Consola Twitch desactivada.")
                break

            try:
                await self._ejecutar_comando_consola(texto)
            except Exception as exc:
                print(f"[CMD] Error enviando comando al chat: {exc}")

    # Evento: bot conectado
    async def event_ready(self):
        # Monitor en caliente: canal + estado whisper
        if self.config_watch_task is None or self.config_watch_task.done():
            self.config_watch_task = asyncio.create_task(self._monitor_config_runtime())

        print(f"✓ Bot conectado como  : {self.nick}")
        print(f"✓ Python              : {sys.executable}")
        print(f"✓ Canal               : #{self.current_channel}")
        print(f"✓ Proveedor IA        : {IA_PROVIDER}")
        print(f"✓ Modelo IA           : {modelo_activo()}")
        owner_cfg = leer_owner_username_config()
        print(f"✓ Owner configurado   : @{owner_cfg}" if owner_cfg else "✓ Owner configurado   : (sin definir)")
        if ENABLE_PROMPT_GUI:
            print(
                f"✓ Prompt activo       : {prompt_activo_slot()} "
                f"({SYSTEM_PROMPT_A_FILE} / {SYSTEM_PROMPT_B_FILE})"
            )
            print(f"✓ Panel web           : http://{WEB_UI_HOST}:{WEB_UI_PORT}")
        if IA_PROVIDER == "openrouter":
            print(f"✓ URL OpenRouter      : {OPENROUTER_URL}")
        else:
            print(f"✓ URL Ollama          : {OLLAMA_URL}")
        print(f"✓ Cooldown por usuario: {COOLDOWN}s")
        print("─" * 45)
        print("Comandos disponibles en chat:")
        print("  !hola           → presenta el bot y explica !ia")
        print("  !ia <pregunta>  → responde con IA")
        print("  !ias <pregunta> → responde usando !speak")
        print("  !responde <txt> → responde con IA al texto dado")
        print("  !modelo         → muestra el modelo activo")
        print("  !ping           → verifica que el bot vive")
        print("─" * 45)

        # Si el panel web esta activo, se evita consola duplicada para no mezclar entradas.
        if (not ENABLE_PROMPT_GUI) and ENABLE_CONSOLE_TWITCH_CMDS and (self.console_task is None or self.console_task.done()):
            self.console_task = asyncio.create_task(self._loop_consola_twitch())

    # ── Comando !hola ───────────────────────────────────────────────────────
    @commands.command(name="hola")
    async def cmd_hola(self, ctx: commands.Context):
        """Presenta el bot y cómo hablar con IA."""
        await enviar_seguro(ctx, "Hola, soy darigptcito. Usa !ia seguido de texto para hablar conmigo.")

    # Evento: mensaje recibido
    async def event_message(self, message):
        # Ignorar mensajes del propio bot
        if message.echo:
            return
        await self.handle_commands(message)

        # Solo auto-responder mensajes normales (no comandos) cuando el modo este activo.
        if not self._leer_auto_reply_activado():
            return

        contenido = (message.content or "").strip()
        if not contenido or contenido.startswith("!"):
            return

        usuario = (message.author.name or "").lower() if message.author else ""
        if usuario in ultimo_uso:
            transcurrido = time.time() - ultimo_uso[usuario]
            if transcurrido < COOLDOWN:
                return

        if usuario:
            ultimo_uso[usuario] = time.time()

        try:
            prompt_sistema_usuario = obtener_prompt_sistema_para_usuario(usuario)
            respuesta = await preguntar_modelo(
                contenido,
                memory_key=f"user:{usuario or 'anon'}",
                prompt_sistema_override=prompt_sistema_usuario,
            )
            respuesta = limpiar_fuera_de_tema(contenido, respuesta)
            prefijo_usuario = f"@{message.author.name} " if message.author else ""
            mensaje = recortar_para_twitch(respuesta, prefijo=prefijo_usuario)
            if mensaje:
                await message.channel.send(mensaje)
        except Exception as exc:
            print(f"[AutoReply] Error respondiendo: {exc}")

    async def event_command_error(self, context, error):
        # Evita ruido en consola por comandos de terceros que este bot no implementa (ej: !clip).
        if isinstance(error, commands.errors.CommandNotFound):
            return
        cmd_name = ""
        try:
            if context and getattr(context, "command", None):
                cmd_name = getattr(context.command, "name", "") or ""
        except Exception:
            cmd_name = ""
        if cmd_name:
            print(f"[CMD] Error en !{cmd_name}: {error}")
        else:
            print(f"[CMD] Error de comando: {error}")

    # ── Comando !responde ───────────────────────────────────────────────
    @commands.command(name="responde")
    async def cmd_responde(self, ctx: commands.Context):
        """La IA reinterpreta y responde el texto dado."""
        partes = ctx.message.content.split(" ", 1)
        if len(partes) < 2 or not partes[1].strip():
            await enviar_seguro(ctx, "Uso correcto: !responde <texto>")
            return
        texto = partes[1].strip()
        usuario = (ctx.author.name or "").lower()
        prompt_sistema_usuario = obtener_prompt_sistema_para_usuario(usuario)
        respuesta = await preguntar_modelo(
            texto,
            memory_key=f"user:{usuario}",
            prompt_sistema_override=prompt_sistema_usuario,
        )
        respuesta = limpiar_fuera_de_tema(texto, respuesta)
        prefijo_usuario = f"@{ctx.author.name} "
        mensaje = recortar_para_twitch(respuesta, prefijo=prefijo_usuario)
        if mensaje:
            await enviar_seguro(ctx, mensaje)

    # ── Comando !ia ──────────────────────────────────────────────────────────
    @commands.command(name="ia")
    async def cmd_ia(self, ctx: commands.Context):
        """Uso en chat: !ia <tu pregunta>"""
        ahora   = time.time()
        usuario = ctx.author.name.lower()

        # Cooldown
        if usuario in ultimo_uso:
            transcurrido = ahora - ultimo_uso[usuario]
            if transcurrido < COOLDOWN:
                restante = int(COOLDOWN - transcurrido)
                await enviar_seguro(ctx, f"Espera {restante}s antes de volver a preguntar.")
                return

        # Extraer pregunta del mensaje
        partes = ctx.message.content.split(" ", 1)
        if len(partes) < 2 or not partes[1].strip():
            await enviar_seguro(ctx, "Uso correcto: !ia <tu pregunta>")
            return

        pregunta = partes[1].strip()
        ultimo_uso[usuario] = ahora

        print(f"[{ctx.author.name}] → {pregunta}")

        prompt_sistema_usuario = obtener_prompt_sistema_para_usuario(usuario)
        respuesta = await preguntar_modelo(
            pregunta,
            memory_key=f"user:{usuario}",
            prompt_sistema_override=prompt_sistema_usuario,
        )
        respuesta = limpiar_fuera_de_tema(pregunta, respuesta)
        prefijo_usuario = f"@{ctx.author.name} "
        mensaje = recortar_para_twitch(respuesta, prefijo=prefijo_usuario)

        print(f"[IA]      → {respuesta[:100]}{'...' if len(respuesta) > 100 else ''}")

        if mensaje:
            await enviar_seguro(ctx, mensaje)

    # ── Comando !ias ─────────────────────────────────────────────────────────
    @commands.command(name="ias")
    async def cmd_ias(self, ctx: commands.Context):
        """Uso en chat: !ias <tu pregunta>, responde como comando !speak."""
        ahora   = time.time()
        usuario = ctx.author.name.lower()

        if usuario in ultimo_uso:
            transcurrido = ahora - ultimo_uso[usuario]
            if transcurrido < COOLDOWN:
                restante = int(COOLDOWN - transcurrido)
                await enviar_seguro(ctx, f"Espera {restante}s antes de volver a preguntar.")
                return

        partes = ctx.message.content.split(" ", 1)
        if len(partes) < 2 or not partes[1].strip():
            await enviar_seguro(ctx, "Uso correcto: !ias <tu pregunta>")
            return

        pregunta = partes[1].strip()
        ultimo_uso[usuario] = ahora

        print(f"[{ctx.author.name}] → {pregunta} (speak)")

        prompt_sistema_usuario = obtener_prompt_sistema_para_usuario(usuario)
        respuesta = await preguntar_modelo(
            pregunta,
            memory_key=f"user:{usuario}",
            prompt_sistema_override=prompt_sistema_usuario,
        )
        respuesta = limpiar_fuera_de_tema(pregunta, respuesta)
        mensaje = recortar_para_twitch(respuesta, prefijo=f"!speak @{ctx.author.name} ")

        print(f"[IA]      → {respuesta[:100]}{'...' if len(respuesta) > 100 else ''}")

        if mensaje:
            await enviar_seguro(ctx, mensaje)

    # ── Comando !modelo ──────────────────────────────────────────────────────
    @commands.command(name="modelo", aliases=("model",))
    async def cmd_modelo(self, ctx: commands.Context):
        """Muestra qué modelo de IA está activo."""
        await enviar_seguro(ctx, modelo_activo())

    # ── Comando !ping ────────────────────────────────────────────────────────
    @commands.command(name="ping")
    async def cmd_ping(self, ctx: commands.Context):
        """Comprueba que el bot está vivo."""
        await enviar_seguro(ctx, "pong!")


# ─── Punto de entrada ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN or TOKEN == "oauth:pon_tu_token_aqui":
        lanzar_panel_web_independiente()
        print("ERROR: Configura TWITCH_TOKEN en config.env")
        print("Obtén tu token en: https://twitchtokengenerator.com/")
        print("Scopes minimos para chat: chat:read y chat:edit")
        exit(1)
    if not CHANNEL or CHANNEL == "nombre_del_canal":
        lanzar_panel_web_independiente()
        print("ERROR: Configura TWITCH_CHANNEL en config.env")
        exit(1)

    try:
        bot = Bot()
    except Exception as exc:
        lanzar_panel_web_independiente()
        print(f"[Twitch] Error inicializando el bot: {exc}")
        exit(1)
    # Inicia panel asociado al proceso del bot antes de conectar a Twitch.
    bot._lanzar_gui_prompts()
    try:
        bot.run()
    except Exception as exc:
        print(f"[Twitch] No se pudo conectar/iniciar el bot: {exc}")
        print(f"[Twitch] El panel web sigue disponible en http://{WEB_UI_HOST}:{WEB_UI_PORT}")
