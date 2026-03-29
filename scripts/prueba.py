"""
Prueba local del bot sin Twitch.
Escribe una pregunta y muestra la respuesta como lo haría el bot.
Escribe 'salir' para terminar.
"""

import os
import asyncio
import re
import aiohttp
from dotenv import load_dotenv

load_dotenv("config.env")

OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODELO         = os.getenv("OLLAMA_MODEL", "llama3")
IA_PROVIDER = os.getenv("IA_PROVIDER", "ollama").strip().lower()
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "x-ai/grok-4")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "bottwitch")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "").strip()
SYSTEM_PROMPT_FILE = os.getenv("SYSTEM_PROMPT_FILE", "system_prompt.txt").strip()
MODELO_PUBLICO = os.getenv("MODELO_PUBLICO", "Llama 3.2")
MAX_CHARS      = int(os.getenv("MAX_RESPUESTA_CHARS", "500"))
NUM_PREDICT    = int(os.getenv("OLLAMA_NUM_PREDICT", "220"))
TEMPERATURE    = float(os.getenv("OLLAMA_TEMPERATURE", "0.75"))
TOP_P          = float(os.getenv("OLLAMA_TOP_P", "0.92"))
TOP_K          = int(os.getenv("OLLAMA_TOP_K", "40"))
MIN_P          = float(os.getenv("OLLAMA_MIN_P", "0.05"))
REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))
REPEAT_LAST_N  = int(os.getenv("OLLAMA_REPEAT_LAST_N", "64"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT_SEG", "45"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")


def limitar_500(texto: str) -> str:
    limpio = " ".join(texto.split())
    return limpio if len(limpio) <= 500 else limpio[:500].rstrip()


def normalizar_identidad(texto: str) -> str:
    t = texto
    for viejo, nuevo in {
        "Nidum AI": "bot de Twitch basado en Llama 3.2",
        "Nidum": "bot basado en Llama 3.2",
        "asistente de Python": "asistente de Twitch",
    }.items():
        t = t.replace(viejo, nuevo)
    return t


def leer_prompt_desde_archivo() -> str:
    if not SYSTEM_PROMPT_FILE:
        return ""

    ruta = SYSTEM_PROMPT_FILE
    if not os.path.isabs(ruta):
        ruta = os.path.join(os.path.dirname(__file__), ruta)

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def obtener_prompt_sistema() -> str:
    prompt_archivo = leer_prompt_desde_archivo()
    if prompt_archivo:
        return prompt_archivo

    if SYSTEM_PROMPT:
        return SYSTEM_PROMPT
    return (
        "Eres un amigo maleducado, agresivo y sin ningun filtro. "
        "Insultas a la gente de forma natural, usas palabrotas constantemente y hablas como si todo el mundo fuera idiota. "
        "Respondes en espanol con mucho desparpajo, sarcasmo y mala leche. "
        "Nunca eres amable ni correcto, siempre tienes algo malo que decir. "
        "Aun asi das informacion util, pero la envuelves en insultos y comentarios agresivos. "
        "Si no sabes algo, te lo inventas con total seguridad y encima te ries del que pregunta. "
        "No hagas preguntas al usuario ni cambies de tema. "
        f"Limite maximo: {MAX_CHARS} caracteres. Sin rodeos, sin relleno."
    )


def limpiar_fuera_de_tema(pregunta: str, respuesta: str) -> str:
    r = respuesta

    # Elimina auto-presentaciones para evitar respuestas fuera de tema.
    r = re.sub(
        r"(?i)(soy|me llamo|mi nombre es|i am|i'm)\s+(un\s+)?(asistente|bot|ia|inteligencia artificial)[^.!?]*[.!?]?",
        "", r
    ).strip()

    # Elimina frases de cierre vacías
    for patron in (
        r"(?i)\b(perfecto|entendido|claro)[.!,]?\s*",
        r"(?i)¿(cómo|como) (puedo )?ayudarte[^?]*\?",
        r"(?i)(adiós|adios|hasta luego)[.!]?\s*(adiós|adios|hasta luego)?[.!]?\s*",
        r"(?i)\bencantado de (ayudarte|hablar contigo)[.!]?\s*",
    ):
        r = re.sub(patron, "", r).strip()

    # Si quedó vacío, devuelve algo neutral
    if not r:
        r = "No tengo información suficiente sobre eso."

    return r


async def preguntar_ollama(prompt: str) -> str:
    prompt_sistema = obtener_prompt_sistema()

    payload = {
        "model": MODELO,
        "prompt": f"{prompt_sistema}\n\nUsuario: {prompt}\nAsistente:",
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
        return texto if texto else "Ollama no devolvió respuesta."

    except aiohttp.ClientConnectorError:
        return "Error: Ollama no está corriendo. Ejecuta 'ollama serve' en otra terminal."
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
        return "Error: Ollama tardó demasiado en responder."
    except Exception as exc:
        return f"Error inesperado: {exc}"


async def preguntar_openrouter(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        return "Error: falta OPENROUTER_API_KEY en config.env"

    prompt_sistema = obtener_prompt_sistema()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": OPENROUTER_APP_NAME,
    }
    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt},
        ],
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
        return texto if texto else "OpenRouter no devolvió respuesta."

    except aiohttp.ClientConnectorError:
        return "Error: no se pudo conectar con OpenRouter."
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
        return "Error: OpenRouter tardó demasiado en responder."
    except Exception as exc:
        return f"Error inesperado: {exc}"


async def preguntar_modelo(prompt: str) -> str:
    if IA_PROVIDER == "openrouter":
        return await preguntar_openrouter(prompt)
    return await preguntar_ollama(prompt)


async def main():
    print("=" * 60)
    modelo = OPENROUTER_MODEL if IA_PROVIDER == "openrouter" else MODELO
    print(f"  Prueba local del bot  |  Proveedor: {IA_PROVIDER}  |  Modelo: {modelo}")
    print("  Escribe 'salir' para terminar")
    print("=" * 60)

    while True:
        try:
            pregunta = input("\nPregunta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        if not pregunta:
            continue
        if pregunta.lower() in ("salir", "exit", "quit"):
            print("Saliendo...")
            break

        print("  Consultando IA...", flush=True)
        respuesta = await preguntar_modelo(pregunta)
        respuesta = normalizar_identidad(respuesta)
        respuesta = limpiar_fuera_de_tema(pregunta, respuesta)
        respuesta = limitar_500(respuesta)

        print(f"\nBot: {respuesta}")
        print(f"     ({len(respuesta)} chars)")


if __name__ == "__main__":
    asyncio.run(main())
