"""
Consola local para probar comandos de Twitch sin conectarse a Twitch.
Comandos soportados:
  !hola
  !ping
  !modelo
  !ia <pregunta>
  !ias <pregunta>
  !salir
"""

import asyncio
import bot


def mostrar_ayuda() -> None:
    print("Comandos disponibles:")
    print("  !hola")
    print("  !ping")
    print("  !modelo")
    print("  !ia <pregunta>")
    print("  !ias <pregunta>")
    print("  !salir")


async def ejecutar_comando(entrada: str) -> str:
    texto = entrada.strip()
    if not texto:
        return ""

    if texto.lower() in ("!salir", "!exit", "!quit"):
        return "__SALIR__"

    if not texto.startswith("!"):
        return "Usa comandos tipo Twitch. Ejemplo: !ia hola"

    partes = texto.split(" ", 1)
    comando = partes[0].lower()
    argumento = partes[1].strip() if len(partes) > 1 else ""

    if comando == "!hola":
        return "Hola, soy darigptcito. Usa !ia seguido de texto para hablar conmigo."

    if comando == "!ping":
        return "pong!"

    if comando in ("!modelo", "!model"):
        return bot.modelo_activo()

    if comando == "!ia":
        if not argumento:
            return "Uso correcto: !ia <tu pregunta>"
        respuesta = await bot.preguntar_modelo(argumento)
        respuesta = bot.limpiar_fuera_de_tema(argumento, respuesta)
        return bot.recortar_para_twitch(respuesta)

    if comando == "!ias":
        if not argumento:
            return "Uso correcto: !ias <tu pregunta>"
        respuesta = await bot.preguntar_modelo(argumento)
        respuesta = bot.limpiar_fuera_de_tema(argumento, respuesta)
        return bot.recortar_para_twitch(respuesta, prefijo="!speak ")

    return "Comando no reconocido. Escribe !hola, !ia, !ias, !modelo o !ping"


async def main() -> None:
    print("=" * 60)
    print("  Prueba local de comandos Twitch (sin conectarse a Twitch)")
    print(f"  Proveedor: {bot.IA_PROVIDER} | Modelo: {bot.modelo_activo()}")
    print("=" * 60)
    mostrar_ayuda()

    while True:
        try:
            entrada = input("\nTu comando> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        salida = await ejecutar_comando(entrada)
        if salida == "__SALIR__":
            print("Saliendo...")
            break
        if salida:
            print(f"Bot> {salida}")


if __name__ == "__main__":
    asyncio.run(main())
