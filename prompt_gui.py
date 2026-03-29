"""Panel de control del bot: prompts, toggles, canal, comandos y monitor Whisper."""

import os
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from dotenv import load_dotenv

load_dotenv("config.env")

BASE_DIR = os.path.dirname(__file__)
CONFIG_ENV_PATH = os.path.join(BASE_DIR, "config.env")
SYSTEM_PROMPT_A_FILE = os.getenv("SYSTEM_PROMPT_A_FILE", "system_prompt_a.txt").strip()
SYSTEM_PROMPT_B_FILE = os.getenv("SYSTEM_PROMPT_B_FILE", "system_prompt_b.txt").strip()
ACTIVE_PROMPT_SELECTOR_FILE = os.getenv("ACTIVE_PROMPT_SELECTOR_FILE", "active_system_prompt.txt").strip()
WHISPER_MODE_FILE = os.getenv("WHISPER_MODE_FILE", "whisper_mode_on.txt").strip()
WHISPER_LIVE_FILE = os.getenv("WHISPER_LIVE_FILE", "whisper_live.txt").strip()
AUTO_REPLY_MODE_FILE = os.getenv("AUTO_REPLY_MODE_FILE", "auto_reply_mode_on.txt").strip()
COMMAND_QUEUE_FILE = os.getenv("COMMAND_QUEUE_FILE", "gui_command_queue.txt").strip()
RESTART_CMD_TOKEN = "__RESTART_BOT__"


def resolver_ruta(ruta: str) -> str:
    if not ruta:
        return ""
    if os.path.isabs(ruta):
        return ruta
    return os.path.join(BASE_DIR, ruta)


def leer_texto(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def escribir_texto(path: str, contenido: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(contenido)
        return True
    except OSError:
        return False


def append_linea(path: str, texto: str) -> bool:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{texto}\n")
        return True
    except OSError:
        return False


def asegurar_archivo(path: str, contenido: str = "") -> None:
    if not path or os.path.exists(path):
        return
    escribir_texto(path, contenido)


def leer_slot_activo(selector_path: str) -> str:
    valor = leer_texto(selector_path).strip().upper()
    return "B" if valor == "B" else "A"


def leer_twitch_channel_config() -> str:
    try:
        with open(CONFIG_ENV_PATH, "r", encoding="utf-8") as f:
            for linea in f:
                s = linea.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("TWITCH_CHANNEL="):
                    return s.split("=", 1)[1].strip()
    except OSError:
        return ""
    return ""


def actualizar_twitch_channel_config(nuevo_canal: str) -> bool:
    try:
        with open(CONFIG_ENV_PATH, "r", encoding="utf-8") as f:
            lineas = f.readlines()
    except OSError:
        return False

    cambiado = False
    salida: list[str] = []
    for linea in lineas:
        if linea.strip().startswith("TWITCH_CHANNEL="):
            salida.append(f"TWITCH_CHANNEL={nuevo_canal}\n")
            cambiado = True
        else:
            salida.append(linea)

    if not cambiado:
        salida.append(f"TWITCH_CHANNEL={nuevo_canal}\n")

    try:
        with open(CONFIG_ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(salida)
        return True
    except OSError:
        return False


class PromptGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BotTwitch Control Center")
        self.geometry("1160x760")
        self.minsize(980, 640)

        self.path_a = resolver_ruta(SYSTEM_PROMPT_A_FILE)
        self.path_b = resolver_ruta(SYSTEM_PROMPT_B_FILE)
        self.path_selector = resolver_ruta(ACTIVE_PROMPT_SELECTOR_FILE)
        self.path_whisper_mode = resolver_ruta(WHISPER_MODE_FILE)
        self.path_whisper_live = resolver_ruta(WHISPER_LIVE_FILE)
        self.path_auto_reply_mode = resolver_ruta(AUTO_REPLY_MODE_FILE)
        self.path_command_queue = resolver_ruta(COMMAND_QUEUE_FILE)

        asegurar_archivo(self.path_a, "")
        asegurar_archivo(self.path_b, "")
        asegurar_archivo(self.path_selector, "A")
        asegurar_archivo(self.path_whisper_mode, "0")
        asegurar_archivo(self.path_whisper_live, "[Whisper] Esperando...")
        asegurar_archivo(self.path_auto_reply_mode, "0")
        asegurar_archivo(self.path_command_queue, "")

        self._autosave_job_a = None
        self._autosave_job_b = None
        self._ultimo_whisper_texto = ""

        self.slot_var = tk.StringVar(value=leer_slot_activo(self.path_selector))
        self.whisper_var = tk.BooleanVar(value=self._leer_estado_whisper())
        self.auto_reply_var = tk.BooleanVar(value=self._leer_estado_auto_reply())
        self.channel_var = tk.StringVar(value=leer_twitch_channel_config())
        self.cmd_text_var = tk.StringVar()
        self.ia_text_var = tk.StringVar()
        self.ia_mode_var = tk.StringVar(value="!ia")

        self._aplicar_estilo()
        self._construir_ui()
        self._cargar_prompts()
        self._actualizar_estado("Panel listo")
        self._poll_whisper_live()

    def _aplicar_estilo(self):
        self.configure(bg="#0b111a")
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Root.TFrame", background="#0b111a")
        style.configure("Card.TFrame", background="#111827")
        style.configure("Head.TFrame", background="#141d2b")
        style.configure("TLabel", background="#0b111a", foreground="#dbe7ff", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#0b111a", foreground="#f8fbff", font=("Segoe UI Semibold", 19))
        style.configure("Sub.TLabel", background="#0b111a", foreground="#8fa6d2", font=("Segoe UI", 10))
        style.configure("Status.TLabel", background="#0b111a", foreground="#6fe3c1", font=("Segoe UI Semibold", 10))
        style.configure("TButton", padding=(10, 7), font=("Segoe UI Semibold", 10), background="#1f2a3a", foreground="#e7f0ff")
        style.map("TButton", background=[("active", "#253246")])
        style.configure("Accent.TButton", background="#1f8a70", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#24a181")])
        style.configure("Toggle.TCheckbutton", background="#111827", foreground="#cfe0ff", font=("Segoe UI", 10))
        style.configure("TRadiobutton", background="#111827", foreground="#d6e4ff")
        style.configure("TLabelframe", background="#111827", foreground="#dbe7ff")
        style.configure("TLabelframe.Label", background="#111827", foreground="#9fb6dd", font=("Segoe UI Semibold", 10))
        style.configure("TEntry", fieldbackground="#0f1726", foreground="#eaf2ff", insertcolor="#eaf2ff")

    def _construir_ui(self):
        root = ttk.Frame(self, style="Root.TFrame", padding=14)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root, style="Root.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="BotTwitch Control Center", style="Title.TLabel").pack(anchor="w")
        ttk.Label(top, text="Todo el control desde GUI: prompts, comandos, canal y Whisper", style="Sub.TLabel").pack(anchor="w", pady=(2, 8))

        self.lbl_estado = ttk.Label(top, text="", style="Status.TLabel")
        self.lbl_estado.pack(anchor="w", pady=(0, 6))

        head = ttk.Frame(root, style="Head.TFrame", padding=10)
        head.pack(fill="x", pady=(0, 10))

        ttk.Label(head, text="Prompt activo:", style="TLabel").pack(side="left")
        ttk.Radiobutton(head, text="A", variable=self.slot_var, value="A", command=self._cambiar_slot).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(head, text="B", variable=self.slot_var, value="B", command=self._cambiar_slot).pack(side="left", padx=(8, 0))
        ttk.Button(head, text="Guardar prompts", style="Accent.TButton", command=self._guardar_todo).pack(side="left", padx=(14, 6))

        self.btn_whisper = ttk.Checkbutton(
            head,
            text="Whisper en vivo",
            variable=self.whisper_var,
            command=self._cambiar_whisper_mode,
            style="Toggle.TCheckbutton",
        )
        self.btn_whisper.pack(side="left", padx=(16, 0))

        self.btn_auto_reply = ttk.Checkbutton(
            head,
            text="Responder todo",
            variable=self.auto_reply_var,
            command=self._cambiar_auto_reply_mode,
            style="Toggle.TCheckbutton",
        )
        self.btn_auto_reply.pack(side="left", padx=(12, 0))

        ttk.Label(head, text="Canal:", style="TLabel").pack(side="left", padx=(16, 4))
        self.entry_channel = ttk.Entry(head, textvariable=self.channel_var, width=18)
        self.entry_channel.pack(side="left")
        self.entry_channel.bind("<Return>", lambda _e: self._aplicar_canal())
        ttk.Button(head, text="Aplicar", command=self._aplicar_canal).pack(side="left", padx=(6, 0))

        body = ttk.Frame(root, style="Root.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        prompts_card = ttk.LabelFrame(body, text="Prompts A/B", padding=10)
        prompts_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        prompts_card.columnconfigure(0, weight=1)
        prompts_card.columnconfigure(1, weight=1)
        prompts_card.rowconfigure(1, weight=1)

        ttk.Label(prompts_card, text="System Prompt A").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(prompts_card, text="System Prompt B").grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        self.txt_a = ScrolledText(prompts_card, wrap="word", undo=True, font=("Consolas", 10), bg="#0f1726", fg="#e7f2ff", insertbackground="#ffffff")
        self.txt_a.grid(row=1, column=0, sticky="nsew")
        self.txt_b = ScrolledText(prompts_card, wrap="word", undo=True, font=("Consolas", 10), bg="#0f1726", fg="#e7f2ff", insertbackground="#ffffff")
        self.txt_b.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

        self.txt_a.bind("<KeyRelease>", self._programar_autoguardado_a)
        self.txt_b.bind("<KeyRelease>", self._programar_autoguardado_b)

        cmd_card = ttk.LabelFrame(body, text="Comandos del chat (sin CMD)", padding=10)
        cmd_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        cmd_card.columnconfigure(0, weight=1)

        fila1 = ttk.Frame(cmd_card)
        fila1.grid(row=0, column=0, sticky="ew")
        fila1.columnconfigure(0, weight=1)
        ttk.Label(fila1, text="Texto libre o comando directo:").grid(row=0, column=0, sticky="w")
        self.entry_cmd = ttk.Entry(fila1, textvariable=self.cmd_text_var)
        self.entry_cmd.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.entry_cmd.bind("<Return>", lambda _e: self._enviar_texto_libre())
        ttk.Button(fila1, text="Enviar texto", style="Accent.TButton", command=self._enviar_texto_libre).grid(row=1, column=1, padx=(8, 0))

        fila2 = ttk.Frame(cmd_card)
        fila2.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        fila2.columnconfigure(1, weight=1)
        ttk.Label(fila2, text="Consulta IA:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(fila2, textvariable=self.ia_mode_var, values=("!ia", "!ias", "!responde"), width=10, state="readonly").grid(row=0, column=1, sticky="w", padx=(8, 6))
        self.entry_ia = ttk.Entry(fila2, textvariable=self.ia_text_var)
        self.entry_ia.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.entry_ia.bind("<Return>", lambda _e: self._enviar_consulta_ia())
        ttk.Button(fila2, text="Enviar IA", command=self._enviar_consulta_ia).grid(row=1, column=2, padx=(8, 0))

        fila3 = ttk.Frame(cmd_card)
        fila3.grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Button(fila3, text="!hola", command=lambda: self._encolar_comando("!hola")).pack(side="left")
        ttk.Button(fila3, text="!ping", command=lambda: self._encolar_comando("!ping")).pack(side="left", padx=(6, 0))
        ttk.Button(fila3, text="!modelo", command=lambda: self._encolar_comando("!modelo")).pack(side="left", padx=(6, 0))
        ttk.Button(fila3, text="Reiniciar bot", style="Accent.TButton", command=self._reiniciar_bot_desde_gui).pack(side="left", padx=(14, 0))

        whisper_card = ttk.LabelFrame(body, text="Whisper en tiempo real", padding=10)
        whisper_card.grid(row=0, column=1, rowspan=2, sticky="nsew")
        whisper_card.rowconfigure(0, weight=1)
        whisper_card.columnconfigure(0, weight=1)

        self.txt_whisper_live = ScrolledText(whisper_card, wrap="word", font=("Consolas", 10), bg="#0f1726", fg="#cfe5ff", insertbackground="#ffffff")
        self.txt_whisper_live.grid(row=0, column=0, sticky="nsew")
        self.txt_whisper_live.insert("1.0", leer_texto(self.path_whisper_live))
        self.txt_whisper_live.config(state="disabled")

        pie = ttk.Label(
            root,
            text=(
                "Todo se aplica en caliente. Los comandos que envias aqui se ejecutan en el bot "
                "y aparecen en el chat sin usar la consola CMD."
            ),
            style="Sub.TLabel",
        )
        pie.pack(anchor="w", pady=(10, 0))

    def _leer_estado_whisper(self) -> bool:
        return leer_texto(self.path_whisper_mode).strip() == "1"

    def _cambiar_whisper_mode(self):
        val = "1" if self.whisper_var.get() else "0"
        if escribir_texto(self.path_whisper_mode, val):
            self._actualizar_estado(f"Whisper {'ACTIVO' if val == '1' else 'desactivado'}")
        else:
            self._actualizar_estado("Error guardando modo Whisper")

    def _leer_estado_auto_reply(self) -> bool:
        return leer_texto(self.path_auto_reply_mode).strip() == "1"

    def _cambiar_auto_reply_mode(self):
        val = "1" if self.auto_reply_var.get() else "0"
        if escribir_texto(self.path_auto_reply_mode, val):
            self._actualizar_estado(f"Responder todo {'ACTIVO' if val == '1' else 'desactivado'}")
        else:
            self._actualizar_estado("Error guardando auto-reply")

    def _aplicar_canal(self):
        canal = (self.channel_var.get() or "").strip().lstrip("#")
        if not canal:
            self._actualizar_estado("Canal vacio")
            return
        if actualizar_twitch_channel_config(canal):
            self._actualizar_estado(f"Canal aplicado: #{canal}")
        else:
            self._actualizar_estado("Error al guardar TWITCH_CHANNEL")

    def _encolar_comando(self, comando: str):
        texto = " ".join((comando or "").split()).strip()
        if not texto:
            self._actualizar_estado("Comando vacio")
            return
        if append_linea(self.path_command_queue, texto):
            self._actualizar_estado(f"Encolado: {texto}")
        else:
            self._actualizar_estado("Error encolando comando")

    def _enviar_texto_libre(self):
        txt = self.cmd_text_var.get().strip()
        self._encolar_comando(txt)
        self.cmd_text_var.set("")

    def _enviar_consulta_ia(self):
        texto = self.ia_text_var.get().strip()
        if not texto:
            self._actualizar_estado("Escribe una consulta para IA")
            return
        comando = self.ia_mode_var.get().strip() or "!ia"
        self._encolar_comando(f"{comando} {texto}")
        self.ia_text_var.set("")

    def _reiniciar_bot_desde_gui(self):
        if append_linea(self.path_command_queue, RESTART_CMD_TOKEN):
            self._actualizar_estado("Reiniciando bot... espera 2-5 segundos")
        else:
            self._actualizar_estado("No se pudo solicitar reinicio")

    def _poll_whisper_live(self):
        texto = leer_texto(self.path_whisper_live)
        if texto != self._ultimo_whisper_texto:
            self._ultimo_whisper_texto = texto
            self.txt_whisper_live.config(state="normal")
            self.txt_whisper_live.delete("1.0", "end")
            self.txt_whisper_live.insert("1.0", texto)
            self.txt_whisper_live.see("end")
            self.txt_whisper_live.config(state="disabled")
        self.after(1000, self._poll_whisper_live)

    def _cargar_prompts(self):
        self.txt_a.delete("1.0", "end")
        self.txt_a.insert("1.0", leer_texto(self.path_a))
        self.txt_b.delete("1.0", "end")
        self.txt_b.insert("1.0", leer_texto(self.path_b))

    def _actualizar_estado(self, msg: str | None = None):
        if msg:
            self.lbl_estado.config(text=msg)
            return
        self.lbl_estado.config(text=f"Activo: {self.slot_var.get().upper()}")

    def _activar_slot(self, slot: str):
        self.slot_var.set(slot)
        self._cambiar_slot()

    def _cambiar_slot(self):
        slot = self.slot_var.get().upper()
        if slot not in ("A", "B"):
            slot = "A"
            self.slot_var.set(slot)
        if escribir_texto(self.path_selector, slot):
            self._actualizar_estado(f"Activo: {slot} (aplicado)")
        else:
            self._actualizar_estado("Error guardando selector")

    def _guardar_a(self):
        if escribir_texto(self.path_a, self.txt_a.get("1.0", "end-1c")):
            self._actualizar_estado("Prompt A guardado")
        else:
            self._actualizar_estado("Error guardando Prompt A")

    def _guardar_b(self):
        if escribir_texto(self.path_b, self.txt_b.get("1.0", "end-1c")):
            self._actualizar_estado("Prompt B guardado")
        else:
            self._actualizar_estado("Error guardando Prompt B")

    def _guardar_todo(self):
        self._guardar_a()
        self._guardar_b()
        self._cambiar_slot()
        self._actualizar_estado("Prompts guardados")

    def _programar_autoguardado_a(self, _event=None):
        if self._autosave_job_a:
            self.after_cancel(self._autosave_job_a)
        self._autosave_job_a = self.after(500, self._guardar_a)

    def _programar_autoguardado_b(self, _event=None):
        if self._autosave_job_b:
            self.after_cancel(self._autosave_job_b)
        self._autosave_job_b = self.after(500, self._guardar_b)


if __name__ == "__main__":
    app = PromptGui()
    app.mainloop()
