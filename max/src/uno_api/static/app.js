const api = {
  async get(path) {
    const response = await fetch(path);
    return parseResponse(response);
  },
  async post(path, payload) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return parseResponse(response);
  }
};

let playerId = localStorage.getItem("unoPlayerId") || "";
let pollHandle = null;

const els = {
  playerName: document.querySelector("#playerName"),
  createBtn: document.querySelector("#createBtn"),
  joinBtn: document.querySelector("#joinBtn"),
  drawBtn: document.querySelector("#drawBtn"),
  passBtn: document.querySelector("#passBtn"),
  chosenColor: document.querySelector("#chosenColor"),
  statusText: document.querySelector("#statusText"),
  players: document.querySelector("#players"),
  drawCount: document.querySelector("#drawCount"),
  topCard: document.querySelector("#topCard"),
  currentTurn: document.querySelector("#currentTurn"),
  message: document.querySelector("#message"),
  hand: document.querySelector("#hand")
};

els.createBtn.addEventListener("click", () => connect("create"));
els.joinBtn.addEventListener("click", () => connect("join"));
els.drawBtn.addEventListener("click", () => sendAction({ action: "draw" }));
els.passBtn.addEventListener("click", () => sendAction({ action: "pass" }));

if (playerId) {
  startPolling();
}

async function connect(mode) {
  const playerName = els.playerName.value.trim();
  if (!playerName) {
    setMessage("Enter a player name.");
    return;
  }
  const path = mode === "create" ? "/api/games" : "/api/games/join";
  try {
    const state = await api.post(path, { player_name: playerName });
    playerId = state.you.id;
    localStorage.setItem("unoPlayerId", playerId);
    render(state);
    startPolling();
  } catch (error) {
    setMessage(error.message);
  }
}

async function sendAction(payload) {
  if (!playerId) {
    setMessage("Connect first.");
    return;
  }
  try {
    const state = await api.post("/api/games/actions", { player_id: playerId, ...payload });
    render(state);
  } catch (error) {
    setMessage(error.message);
  }
}

async function playCard(index, card) {
  const payload = {
    action: "play",
    card_index: index,
    declare_uno: true
  };
  if (card.type === "wild") {
    if (!els.chosenColor.value) {
      setMessage("Choose a wild color first.");
      return;
    }
    payload.chosen_color = els.chosenColor.value;
  }
  await sendAction(payload);
}

function startPolling() {
  clearInterval(pollHandle);
  refresh();
  pollHandle = setInterval(refresh, 2000);
}

async function refresh() {
  if (!playerId) {
    return;
  }
  try {
    render(await api.get(`/api/games/state?player_id=${playerId}`));
  } catch (error) {
    setMessage(error.message);
  }
}

function render(state) {
  els.statusText.textContent = `${state.status.toUpperCase()} | Turn ${state.turn}`;
  els.players.innerHTML = state.players.map((player) => `
    <div class="player-row">
      <span>${escapeHtml(player.name)}${player.id === state.current_player_id ? " *" : ""}</span>
      <strong>${player.cards_in_hand}</strong>
    </div>
  `).join("");
  els.drawCount.textContent = state.draw_pile_count;
  els.currentTurn.textContent = state.current_player_name || "-";
  els.message.textContent = state.message;
  renderTopCard(state.top_card);
  renderHand(state);
  els.drawBtn.disabled = !state.you?.is_current_turn;
  els.passBtn.disabled = !state.you?.is_current_turn;
}

function renderTopCard(card) {
  const colorClass = colorFor(card);
  els.topCard.className = `pile discard-pile ${colorClass}`;
  els.topCard.innerHTML = `<span>Top</span><strong>${card ? label(card) : "-"}</strong>`;
}

function renderHand(state) {
  const hand = state.you?.hand || [];
  const playable = new Set(state.playable_indexes || []);
  els.hand.innerHTML = "";
  hand.forEach((card, index) => {
    const button = document.createElement("button");
    button.className = `card ${colorFor(card)}`;
    button.disabled = !state.you.is_current_turn || !playable.has(index);
    button.innerHTML = `${label(card)}<small>#${index}</small>`;
    button.addEventListener("click", () => playCard(index, card));
    els.hand.appendChild(button);
  });
}

function colorFor(card) {
  if (!card) {
    return "";
  }
  return card.chosen_color || card.color || "wild";
}

function label(card) {
  if (!card) {
    return "-";
  }
  const color = card.chosen_color || card.color;
  return color ? `${color} ${card.value}` : card.value;
}

function setMessage(message) {
  els.message.textContent = message;
}

async function parseResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed.");
  }
  return payload;
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;"
  }[char]));
}
