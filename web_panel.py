"""Panel web local para controlar el bot de Twitch sin GUI de escritorio."""

import json
import os
import threading
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv("config.env")

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "webui"
CONFIG_ENV_PATH = BASE_DIR / "config.env"

SYSTEM_PROMPT_A_FILE = os.getenv("SYSTEM_PROMPT_A_FILE", "system_prompt_a.txt").strip()
SYSTEM_PROMPT_B_FILE = os.getenv("SYSTEM_PROMPT_B_FILE", "system_prompt_b.txt").strip()
OWNER_SYSTEM_PROMPT_FILE = os.getenv("OWNER_SYSTEM_PROMPT_FILE", "prompts/owner_system_prompt.txt").strip()
ACTIVE_PROMPT_SELECTOR_FILE = os.getenv("ACTIVE_PROMPT_SELECTOR_FILE", "active_system_prompt.txt").strip()
WHISPER_MODE_FILE = os.getenv("WHISPER_MODE_FILE", "whisper_mode_on.txt").strip()
WHISPER_LIVE_FILE = os.getenv("WHISPER_LIVE_FILE", "whisper_live.txt").strip()
AUTO_REPLY_MODE_FILE = os.getenv("AUTO_REPLY_MODE_FILE", "auto_reply_mode_on.txt").strip()
COMMAND_QUEUE_FILE = os.getenv("COMMAND_QUEUE_FILE", "gui_command_queue.txt").strip()
DEBUG_WEB_MODE_FILE = os.getenv("DEBUG_WEB_MODE_FILE", "runtime/debug_web_mode_on.txt").strip()
DEBUG_WEB_LOG_FILE = os.getenv("DEBUG_WEB_LOG_FILE", "runtime/debug_web.log").strip()
RESTART_CMD_TOKEN = "__RESTART_BOT__"

WEB_UI_HOST = os.getenv("WEB_UI_HOST", "127.0.0.1").strip() or "127.0.0.1"
WEB_UI_PORT = int(os.getenv("WEB_UI_PORT", "8787"))
WEB_UI_AUTO_OPEN = os.getenv("WEB_UI_AUTO_OPEN", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "si",
    "on",
)

LOCK = threading.Lock()


def resolver_ruta(ruta: str) -> Path:
    if not ruta:
        return BASE_DIR
    p = Path(ruta)
    return p if p.is_absolute() else (BASE_DIR / p)


def leer_texto(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def escribir_texto(path: Path, contenido: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contenido, encoding="utf-8")
        return True
    except OSError:
        return False


def append_linea(path: Path, texto: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{texto}\n")
        return True
    except OSError:
        return False


def asegurar_archivo(path: Path, contenido: str = "") -> None:
    if not path.exists():
        escribir_texto(path, contenido)


def leer_slot_activo(selector_path: Path) -> str:
    valor = leer_texto(selector_path).strip().upper()
    return "B" if valor == "B" else "A"


def leer_twitch_channel_config() -> str:
    valor = leer_config_env_clave("TWITCH_CHANNEL")
    return valor.strip()


def leer_owner_username_config() -> str:
    valor = leer_config_env_clave("OWNER_USERNAME")
    return valor.strip().lstrip("@").lower()


def leer_config_env_clave(clave: str) -> str:
    try:
        with CONFIG_ENV_PATH.open("r", encoding="utf-8") as f:
            for linea in f:
                s = linea.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith(f"{clave}="):
                    return s.split("=", 1)[1].strip()
    except OSError:
        return ""
    return ""


def actualizar_config_env_claves(cambios: dict[str, str]) -> bool:
    try:
        lineas = CONFIG_ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return False

    pendientes = {k: str(v) for k, v in cambios.items() if k}
    salida: list[str] = []
    for linea in lineas:
        linea_strip = linea.strip()
        reemplazada = False
        for clave in list(pendientes.keys()):
            if linea_strip.startswith(f"{clave}="):
                salida.append(f"{clave}={pendientes.pop(clave)}\n")
                reemplazada = True
                break
        if not reemplazada:
            salida.append(linea)

    for clave, valor in pendientes.items():
        salida.append(f"{clave}={valor}\n")

    try:
        CONFIG_ENV_PATH.write_text("".join(salida), encoding="utf-8")
        return True
    except OSError:
        return False


PATH_A = resolver_ruta(SYSTEM_PROMPT_A_FILE)
PATH_B = resolver_ruta(SYSTEM_PROMPT_B_FILE)
PATH_OWNER_PROMPT = resolver_ruta(OWNER_SYSTEM_PROMPT_FILE)
PATH_SELECTOR = resolver_ruta(ACTIVE_PROMPT_SELECTOR_FILE)
PATH_WHISPER_MODE = resolver_ruta(WHISPER_MODE_FILE)
PATH_WHISPER_LIVE = resolver_ruta(WHISPER_LIVE_FILE)
PATH_AUTO_REPLY_MODE = resolver_ruta(AUTO_REPLY_MODE_FILE)
PATH_COMMAND_QUEUE = resolver_ruta(COMMAND_QUEUE_FILE)
PATH_DEBUG_WEB_MODE = resolver_ruta(DEBUG_WEB_MODE_FILE)
PATH_DEBUG_WEB_LOG = resolver_ruta(DEBUG_WEB_LOG_FILE)

asegurar_archivo(PATH_A, "")
asegurar_archivo(PATH_B, "")
asegurar_archivo(PATH_OWNER_PROMPT, "")
asegurar_archivo(PATH_SELECTOR, "A")
asegurar_archivo(PATH_WHISPER_MODE, "0")
asegurar_archivo(PATH_WHISPER_LIVE, "[Whisper] Esperando...")
asegurar_archivo(PATH_AUTO_REPLY_MODE, "0")
asegurar_archivo(PATH_COMMAND_QUEUE, "")
asegurar_archivo(PATH_DEBUG_WEB_MODE, "0")
asegurar_archivo(PATH_DEBUG_WEB_LOG, "")


def get_state() -> dict:
    with LOCK:
        return {
            "slot": leer_slot_activo(PATH_SELECTOR),
            "promptA": leer_texto(PATH_A),
            "promptB": leer_texto(PATH_B),
            "ownerUsername": leer_owner_username_config(),
            "ownerPrompt": leer_texto(PATH_OWNER_PROMPT),
            "whisper": leer_texto(PATH_WHISPER_MODE).strip() == "1",
            "autoReply": leer_texto(PATH_AUTO_REPLY_MODE).strip() == "1",
            "debugWeb": leer_texto(PATH_DEBUG_WEB_MODE).strip() == "1",
            "whisperLive": leer_texto(PATH_WHISPER_LIVE),
            "channel": leer_twitch_channel_config(),
        }


def json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


class PanelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args):
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            return json_response(self, HTTPStatus.OK, {"ok": True, "state": get_state()})
        if parsed.path == "/api/health":
            return json_response(self, HTTPStatus.OK, {"ok": True})
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._read_json()

        if parsed.path == "/api/slot":
            slot = str(body.get("slot", "")).strip().upper()
            if slot not in ("A", "B"):
                return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Slot invalido"})
            ok = escribir_texto(PATH_SELECTOR, slot)
            return json_response(self, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": ok})

        if parsed.path == "/api/prompts":
            prompt_a = str(body.get("promptA", ""))
            prompt_b = str(body.get("promptB", ""))
            ok_a = escribir_texto(PATH_A, prompt_a)
            ok_b = escribir_texto(PATH_B, prompt_b)
            ok = ok_a and ok_b
            return json_response(self, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": ok})

        if parsed.path == "/api/mode":
            whisper = body.get("whisper")
            auto_reply = body.get("autoReply")
            debug_web = body.get("debugWeb")
            ok = True
            if isinstance(whisper, bool):
                ok = ok and escribir_texto(PATH_WHISPER_MODE, "1" if whisper else "0")
            if isinstance(auto_reply, bool):
                ok = ok and escribir_texto(PATH_AUTO_REPLY_MODE, "1" if auto_reply else "0")
            if isinstance(debug_web, bool):
                ok = ok and escribir_texto(PATH_DEBUG_WEB_MODE, "1" if debug_web else "0")
            return json_response(self, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": ok})

        if parsed.path == "/api/channel":
            canal = str(body.get("channel", "")).strip().lstrip("#")
            if not canal:
                return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Canal vacio"})
            ok = actualizar_config_env_claves({"TWITCH_CHANNEL": canal})
            return json_response(self, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": ok})

        if parsed.path == "/api/owner":
            owner_username = str(body.get("ownerUsername", "")).strip().lstrip("@").lower()
            owner_prompt = str(body.get("ownerPrompt", ""))
            ok_cfg = actualizar_config_env_claves({"OWNER_USERNAME": owner_username})
            ok_prompt = escribir_texto(PATH_OWNER_PROMPT, owner_prompt)
            ok = ok_cfg and ok_prompt
            return json_response(self, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": ok})

        if parsed.path == "/api/command":
            cmd = " ".join(str(body.get("command", "")).split()).strip()
            if not cmd:
                return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Comando vacio"})
            ok = append_linea(PATH_COMMAND_QUEUE, cmd)
            return json_response(self, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": ok})

        if parsed.path == "/api/restart":
            ok = append_linea(PATH_COMMAND_QUEUE, RESTART_CMD_TOKEN)
            return json_response(self, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": ok})

        return json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Ruta no encontrada"})


def main() -> None:
    if not WEB_DIR.exists():
        raise RuntimeError("Falta carpeta webui")

    server = ThreadingHTTPServer((WEB_UI_HOST, WEB_UI_PORT), PanelHandler)
    url = f"http://{WEB_UI_HOST}:{WEB_UI_PORT}"
    print(f"[WEB] Panel disponible en {url}")

    if WEB_UI_AUTO_OPEN:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
