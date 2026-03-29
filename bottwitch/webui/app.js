const statusEl = document.getElementById("status");
const btnRefresh = document.getElementById("btnRefresh");
const btnChannel = document.getElementById("btnChannel");
const btnSendFree = document.getElementById("btnSendFree");
const btnSendIA = document.getElementById("btnSendIA");
const btnRestart = document.getElementById("btnRestart");
const btnSaveA = document.getElementById("btnSaveA");
const btnSaveB = document.getElementById("btnSaveB");
const btnSaveOwner = document.getElementById("btnSaveOwner");

const slotA = document.getElementById("slotA");
const slotB = document.getElementById("slotB");
const toggleWhisper = document.getElementById("toggleWhisper");
const toggleAutoReply = document.getElementById("toggleAutoReply");
const toggleDebugWeb = document.getElementById("toggleDebugWeb");

const channelInput = document.getElementById("channelInput");
const freeCommand = document.getElementById("freeCommand");
const iaMode = document.getElementById("iaMode");
const iaText = document.getElementById("iaText");
const ownerUserInput = document.getElementById("ownerUserInput");
const ownerPrompt = document.getElementById("ownerPrompt");

const promptA = document.getElementById("promptA");
const promptB = document.getElementById("promptB");
const whisperText = document.getElementById("whisperText");

const streamFrame = document.getElementById("streamFrame");
const chatFrame = document.getElementById("chatFrame");
const chatPopoutLink = document.getElementById("chatPopoutLink");

let state = {
  slot: "A",
  whisper: false,
  autoReply: false,
  debugWeb: false,
  channel: "",
  ownerUsername: "",
  ownerPrompt: "",
  promptA: "",
  promptB: "",
  whisperLive: "",
};

let lastWhisper = "";
let lastEmbedChannel = "";
let isSyncingPrompts = false;

function collectParentHosts() {
  const raw = (window.location.hostname || "").trim().toLowerCase();
  const set = new Set();

  if (raw && raw !== "0.0.0.0") {
    set.add(raw);
  }

  // Compatibilidad local: algunos navegadores/Twitch validan mejor localhost/127.
  set.add("localhost");
  set.add("127.0.0.1");

  // Evita hostnames potencialmente invalidos para el parametro parent.
  return [...set].filter((h) => /^[a-z0-9.-]+$/.test(h));
}

function setStatus(text, ok = true) {
  statusEl.textContent = text;
  statusEl.style.color = ok ? "var(--ok)" : "var(--danger)";
}

function setLoading(msg) {
  setStatus(msg || "Cargando...", true);
}

async function apiGet(url) {
  const res = await fetch(url, { cache: "no-store" });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.error || `Error ${res.status}`);
  }
  return data;
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.error || `Error ${res.status}`);
  }
  return data;
}

function paintButtons() {
  slotA.classList.toggle("active", state.slot === "A");
  slotB.classList.toggle("active", state.slot === "B");

  toggleWhisper.classList.toggle("on", !!state.whisper);
  toggleWhisper.textContent = state.whisper ? "On" : "Off";

  toggleAutoReply.classList.toggle("on", !!state.autoReply);
  toggleAutoReply.textContent = state.autoReply ? "On" : "Off";

  toggleDebugWeb.classList.toggle("on", !!state.debugWeb);
  toggleDebugWeb.textContent = state.debugWeb ? "On" : "Off";
}

function setEmbeds(channel) {
  const clean = (channel || "").trim().replace(/^#/, "");
  if (!clean) {
    streamFrame.src = "about:blank";
    chatFrame.src = "about:blank";
    if (chatPopoutLink) {
      chatPopoutLink.href = "#";
    }
    return;
  }
  if (clean === lastEmbedChannel) {
    return;
  }
  lastEmbedChannel = clean;

  const parents = collectParentHosts();
  const parentQs = parents.map((p) => `parent=${encodeURIComponent(p)}`).join("&");

  streamFrame.src = `https://player.twitch.tv/?channel=${encodeURIComponent(clean)}&${parentQs}&autoplay=false&muted=true`;
  const chatEmbedUrl = `https://www.twitch.tv/embed/${encodeURIComponent(clean)}/chat?${parentQs}&darkpopout`;
  const chatPopoutUrl = `https://www.twitch.tv/popout/${encodeURIComponent(clean)}/chat?${parentQs}&darkpopout`;
  chatFrame.src = chatEmbedUrl;
  if (chatPopoutLink) {
    chatPopoutLink.href = chatPopoutUrl;
  }
}

function syncUIFromState() {
  paintButtons();

  // Evita sobrescribir el input mientras el usuario esta editando el canal.
  if (document.activeElement !== channelInput) {
    channelInput.value = state.channel || "";
  }
  if (document.activeElement !== ownerUserInput) {
    ownerUserInput.value = state.ownerUsername || "";
  }
  if (document.activeElement !== ownerPrompt) {
    ownerPrompt.value = state.ownerPrompt || "";
  }

  isSyncingPrompts = true;
  promptA.value = state.promptA || "";
  promptB.value = state.promptB || "";
  isSyncingPrompts = false;

  if (state.whisperLive !== lastWhisper) {
    lastWhisper = state.whisperLive;
    whisperText.textContent = state.whisperLive || "[Whisper] Esperando...";
    whisperText.scrollTop = whisperText.scrollHeight;
  }

  setEmbeds(state.channel || "");
}

async function refreshState(silent = false) {
  try {
    if (!silent) {
      setLoading("Sincronizando panel...");
    }
    const data = await apiGet("/api/state");
    state = data.state || state;
    syncUIFromState();
    if (!silent) {
      setStatus("Panel listo", true);
    }
  } catch (err) {
    setStatus(`Error: ${err.message}`, false);
  }
}

async function setSlot(slot) {
  try {
    await apiPost("/api/slot", { slot });
    state.slot = slot;
    paintButtons();
    setStatus(`Prompt activo: ${slot}`, true);
  } catch (err) {
    setStatus(`No se pudo cambiar slot: ${err.message}`, false);
  }
}

async function setMode(payload) {
  try {
    await apiPost("/api/mode", payload);
    await refreshState(true);
    if (Object.prototype.hasOwnProperty.call(payload, "whisper")) {
      setStatus(payload.whisper ? "Whisper activado" : "Whisper desactivado", true);
      return;
    }
    setStatus("Modo actualizado", true);
  } catch (err) {
    setStatus(`No se pudo actualizar modo: ${err.message}`, false);
  }
}

async function savePrompts(which = "both") {
  try {
    const body = {
      promptA: promptA.value,
      promptB: promptB.value,
    };

    if (which === "A") {
      body.promptB = state.promptB || promptB.value;
    }
    if (which === "B") {
      body.promptA = state.promptA || promptA.value;
    }

    await apiPost("/api/prompts", body);
    state.promptA = body.promptA;
    state.promptB = body.promptB;
    setStatus(`Prompt ${which} guardado`, true);
  } catch (err) {
    setStatus(`Error guardando prompts: ${err.message}`, false);
  }
}

async function applyChannel() {
  const channel = (channelInput.value || "").trim().replace(/^#/, "");
  if (!channel) {
    setStatus("Canal vacio", false);
    return;
  }
  try {
    await apiPost("/api/channel", { channel });
    state.channel = channel;
    setEmbeds(channel);
    setStatus(`Canal aplicado: #${channel}`, true);
  } catch (err) {
    setStatus(`No se pudo aplicar canal: ${err.message}`, false);
  }
}

async function sendCommand(command) {
  const cmd = (command || "").trim();
  if (!cmd) {
    setStatus("Comando vacio", false);
    return;
  }
  try {
    await apiPost("/api/command", { command: cmd });
    setStatus(`Encolado: ${cmd}`, true);
  } catch (err) {
    setStatus(`Error encolando comando: ${err.message}`, false);
  }
}

async function saveOwner() {
  const ownerUsername = (ownerUserInput.value || "").trim().replace(/^@/, "").toLowerCase();
  const ownerPromptText = ownerPrompt.value || "";
  try {
    await apiPost("/api/owner", {
      ownerUsername,
      ownerPrompt: ownerPromptText,
    });
    state.ownerUsername = ownerUsername;
    state.ownerPrompt = ownerPromptText;
    setStatus(ownerUsername ? `Owner guardado: @${ownerUsername}` : "Owner limpiado", true);
  } catch (err) {
    setStatus(`Error guardando owner: ${err.message}`, false);
  }
}

async function restartBot() {
  try {
    await apiPost("/api/restart", {});
    setStatus("Reinicio solicitado. Espera 2-5 segundos", true);
  } catch (err) {
    setStatus(`No se pudo reiniciar: ${err.message}`, false);
  }
}

btnRefresh.addEventListener("click", () => refreshState(false));
slotA.addEventListener("click", () => setSlot("A"));
slotB.addEventListener("click", () => setSlot("B"));

toggleWhisper.addEventListener("click", () => setMode({ whisper: !state.whisper }));
toggleAutoReply.addEventListener("click", () => setMode({ autoReply: !state.autoReply }));
toggleDebugWeb.addEventListener("click", () => setMode({ debugWeb: !state.debugWeb }));

btnChannel.addEventListener("click", applyChannel);
channelInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    applyChannel();
  }
});

btnSendFree.addEventListener("click", () => {
  sendCommand(freeCommand.value);
  freeCommand.value = "";
});
freeCommand.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    sendCommand(freeCommand.value);
    freeCommand.value = "";
  }
});

btnSendIA.addEventListener("click", () => {
  const txt = iaText.value.trim();
  if (!txt) {
    setStatus("Escribe una consulta IA", false);
    return;
  }
  sendCommand(`${iaMode.value} ${txt}`);
  iaText.value = "";
});
iaText.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const txt = iaText.value.trim();
    if (txt) {
      sendCommand(`${iaMode.value} ${txt}`);
      iaText.value = "";
    }
  }
});

document.querySelectorAll("[data-quick]").forEach((btn) => {
  btn.addEventListener("click", () => sendCommand(btn.dataset.quick));
});

btnRestart.addEventListener("click", restartBot);
btnSaveA.addEventListener("click", () => savePrompts("A"));
btnSaveB.addEventListener("click", () => savePrompts("B"));
btnSaveOwner.addEventListener("click", saveOwner);

ownerUserInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    saveOwner();
  }
});

let ownerSaveTimer = null;
function scheduleOwnerAutosave() {
  if (ownerSaveTimer) {
    clearTimeout(ownerSaveTimer);
  }
  ownerSaveTimer = setTimeout(() => {
    saveOwner();
  }, 900);
}

ownerPrompt.addEventListener("input", scheduleOwnerAutosave);

let promptSaveTimer = null;
function schedulePromptAutosave() {
  if (isSyncingPrompts) {
    return;
  }
  if (promptSaveTimer) {
    clearTimeout(promptSaveTimer);
  }
  promptSaveTimer = setTimeout(() => {
    savePrompts("both");
  }, 650);
}

promptA.addEventListener("input", schedulePromptAutosave);
promptB.addEventListener("input", schedulePromptAutosave);

(async function boot() {
  await refreshState(false);
  setInterval(() => refreshState(true), 1200);
})();
