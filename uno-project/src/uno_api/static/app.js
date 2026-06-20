const api = {
  async get(path) {
    const response = await fetch(path);
    return parseResponse(response);
  }
};

const els = {
  statusText: document.querySelector("#statusText"),
  gameId: document.querySelector("#gameId"),
  agentTop: document.querySelector("#agentTop"),
  agentBottom: document.querySelector("#agentBottom"),
  drawPile: document.querySelector("#drawPile"),
  drawCount: document.querySelector("#drawCount"),
  topCard: document.querySelector("#topCard"),
  currentTurn: document.querySelector("#currentTurn"),
  message: document.querySelector("#message"),
  gameStatus: document.querySelector("#gameStatus"),
  turnCount: document.querySelector("#turnCount"),
  direction: document.querySelector("#direction"),
  impactLayer: document.querySelector("#impactLayer"),
  soundToggle: document.querySelector("#soundToggle"),
  ruleCount: document.querySelector("#ruleCount"),
  rulesVersion: document.querySelector("#rulesVersion"),
  rulesList: document.querySelector("#rulesList")
};

let previousState = null;
let audioContext = null;
let soundEnabled = false;
const rendered = {
  header: "",
  metrics: "",
  topCard: "",
  players: new Map(),
  message: "",
  rules: "",
};

els.soundToggle.addEventListener("click", async () => {
  audioContext = audioContext || new AudioContext();
  await audioContext.resume();
  soundEnabled = !soundEnabled;
  els.soundToggle.textContent = soundEnabled ? "Sound On" : "Enable Sound";
  if (soundEnabled) {
    playImpactSound("start");
    burst("READY", "zap");
  }
});

refresh();
setInterval(refresh, 1000);

async function refresh() {
  try {
    const [state, mutableRules] = await Promise.all([
      api.get("/api/games/observer"),
      api.get("/api/rules/mutable"),
    ]);
    render(state);
    renderRules(mutableRules);
  } catch (error) {
    setMessage(error.message);
  }
}

function render(state) {
  const eventType = detectEvent(previousState, state);
  const playedCardFlight = findPlayedCardFlight(previousState, state);

  renderHeader(state);
  renderMetrics(state);
  renderMessage(state.message);
  if (playedCardFlight) {
    animatePlayedCard(playedCardFlight, eventType);
  }
  renderAgentZone(els.agentTop, state.players[0], state);
  renderAgentZone(els.agentBottom, state.players[1], state);
  renderTopCard(state.top_card, playedCardFlight ? null : eventType);
  triggerEffects(eventType, state);

  previousState = structuredCloneSafe(state);
}

function renderHeader(state) {
  const signature = JSON.stringify([state.status, state.turn, state.game_id]);
  if (rendered.header === signature) {
    return;
  }
  els.statusText.textContent = `${state.status.toUpperCase()} | Turn ${state.turn}`;
  els.gameId.textContent = state.game_id || "-";
  rendered.header = signature;
}

function renderMetrics(state) {
  const direction = state.direction === 1 ? "clockwise" : "counter-clockwise";
  const signature = JSON.stringify([
    state.draw_pile_count,
    state.current_player_name,
    state.status,
    state.turn,
    direction,
  ]);
  if (rendered.metrics === signature) {
    return;
  }
  els.drawCount.textContent = state.draw_pile_count;
  els.currentTurn.textContent = state.current_player_name || "-";
  els.gameStatus.textContent = state.status;
  els.turnCount.textContent = state.turn;
  els.direction.textContent = direction;
  rendered.metrics = signature;
}

function renderMessage(message) {
  if (rendered.message === message) {
    return;
  }
  els.message.textContent = message;
  els.message.classList.remove("message-flash");
  void els.message.offsetWidth;
  els.message.classList.add("message-flash");
  rendered.message = message;
}

function renderRules(mutableRules) {
  const rules = mutableRules.rules || [];
  const signature = JSON.stringify(mutableRules);
  if (rendered.rules === signature) {
    return;
  }

  const previousRules = rendered.rules ? JSON.parse(rendered.rules).rules || [] : [];
  const previousById = new Map(previousRules.map((rule) => [rule.id, JSON.stringify(rule)]));

  els.ruleCount.textContent = `${rules.length} active`;
  els.rulesVersion.textContent = mutableRules.version ?? "-";
  els.rulesList.innerHTML = rules.length
    ? rules.map((rule) => renderRuleCard(rule, previousById)).join("")
    : `<article class="rule-empty">No mutable rules have been applied yet.</article>`;

  rendered.rules = signature;
}

function renderRuleCard(rule, previousById) {
  const wasKnown = previousById.has(rule.id);
  const changed = wasKnown && previousById.get(rule.id) !== JSON.stringify(rule);
  const freshClass = !wasKnown || changed ? " rule-new" : "";
  return `
    <article class="rule-card${freshClass}">
      <header>
        <div>
          <span>${escapeHtml(rule.type)}</span>
          <strong>${escapeHtml(rule.title)}</strong>
        </div>
        <code>${escapeHtml(rule.id)}</code>
      </header>
      <p>${escapeHtml(rule.description)}</p>
      <div class="rule-grid">
        <section>
          <span>Condition</span>
          <pre>${escapeHtml(JSON.stringify(rule.condition || {}, null, 2))}</pre>
        </section>
        <section>
          <span>Effect</span>
          <pre>${escapeHtml(JSON.stringify(rule.effect || {}, null, 2))}</pre>
        </section>
      </div>
      <footer>
        <span>Created by ${escapeHtml(rule.created_by || "-")}</span>
        ${rule.modified_by ? `<span>Modified by ${escapeHtml(rule.modified_by)}</span>` : ""}
      </footer>
    </article>
  `;
}

function renderAgentZone(container, player, state) {
  if (!player) {
    renderEmptyAgent(container);
    return;
  }

  const signature = playerSignature(player);
  if (rendered.players.get(player.id) === signature) {
    return;
  }

  const previousPlayer = previousState?.players?.find((item) => item.id === player.id);
  const currentClass = player.is_current_turn ? " current" : "";
  const uno = player.uno_declared ? `<span class="uno-badge">UNO</span>` : "";
  container.innerHTML = `
    <div class="agent-card${currentClass}">
      <div class="agent-info">
        <div>
          <span>Agent</span>
          <strong>${escapeHtml(player.name)}</strong>
        </div>
        <div class="card-count">${player.cards_in_hand}</div>
      </div>
      ${uno}
      <div class="hand-row">
        ${player.hand.map((card, index) => renderCard(card, index, player.playable_indexes, previousPlayer, player.id)).join("")}
      </div>
    </div>
  `;
  rendered.players.set(player.id, signature);
}

function renderEmptyAgent(container) {
  const key = `empty:${container.id}`;
  if (rendered.players.get(key) === "empty") {
    return;
  }
  container.innerHTML = `<div class="agent-card empty-agent">Waiting for agent...</div>`;
  rendered.players.set(key, "empty");
}

function renderCard(card, index, playableIndexes, previousPlayer, playerId) {
  const playableClass = playableIndexes.includes(index) ? " playable" : "";
  const previousCard = previousPlayer?.hand?.[index];
  const stableClass = previousCard && cardSignature(previousCard) === cardSignature(card) ? " stable" : "";
  return `
    <div class="mini-card ${colorFor(card)}${playableClass}${stableClass}" data-player-id="${escapeHtml(playerId)}" data-card-index="${index}" style="--tilt:${tiltFor(index)}deg">
      <span>${label(card)}</span>
      <small>#${index}</small>
    </div>
  `;
}

function renderTopCard(card, eventType) {
  const signature = cardSignature(card);
  const unchanged = rendered.topCard === signature;
  if (unchanged && !(eventType === "play" || eventType === "power" || eventType === "win")) {
    return;
  }

  const colorClass = colorFor(card);
  const slam = eventType === "play" || eventType === "power" || eventType === "win" ? " slam" : "";
  els.topCard.className = `pile discard-pile ${colorClass}${slam}`;
  els.topCard.innerHTML = `<span>Top</span><strong>${card ? label(card) : "-"}</strong>`;
  rendered.topCard = signature;
  if (slam) {
    setTimeout(() => els.topCard.classList.remove("slam"), 650);
  }
}

function detectEvent(previous, state) {
  if (!previous) {
    return "start";
  }
  if (state.status === "finished" && previous.status !== "finished") {
    return "win";
  }
  if (state.turn === previous.turn) {
    return null;
  }

  const message = (state.message || "").toLowerCase();
  const topChanged = JSON.stringify(state.top_card) !== JSON.stringify(previous.top_card);
  const powerCard = state.top_card && ["skip", "reverse", "draw_two", "wild_draw_four"].includes(state.top_card.value);

  if (message.includes("drew")) {
    return "draw";
  }
  if (message.includes("passed")) {
    return "pass";
  }
  if (topChanged && powerCard) {
    return "power";
  }
  if (topChanged || message.includes("played")) {
    return "play";
  }
  return "tick";
}

function findPlayedCardFlight(previous, state) {
  if (!previous || state.turn === previous.turn) {
    return null;
  }
  const topChanged = cardSignature(state.top_card) !== cardSignature(previous.top_card);
  const playedMessage = (state.message || "").toLowerCase().includes("played");
  if (!topChanged && !playedMessage) {
    return null;
  }

  for (const previousPlayer of previous.players || []) {
    const currentPlayer = state.players.find((player) => player.id === previousPlayer.id);
    if (!currentPlayer || previousPlayer.hand.length <= currentPlayer.hand.length) {
      continue;
    }
    const removed = findRemovedCard(previousPlayer.hand, currentPlayer.hand);
    if (removed) {
      return {
        playerId: previousPlayer.id,
        cardIndex: removed.index,
        card: removed.card,
      };
    }
  }
  return null;
}

function findRemovedCard(previousHand, currentHand) {
  let currentIndex = 0;
  for (let previousIndex = 0; previousIndex < previousHand.length; previousIndex += 1) {
    const previousCard = previousHand[previousIndex];
    const currentCard = currentHand[currentIndex];
    if (currentCard && cardSignature(previousCard) === cardSignature(currentCard)) {
      currentIndex += 1;
      continue;
    }
    return {
      index: previousIndex,
      card: previousCard,
    };
  }
  return null;
}

function animatePlayedCard(flight, eventType) {
  const source = [...document.querySelectorAll(".mini-card")].find((card) => (
    card.dataset.playerId === flight.playerId && Number(card.dataset.cardIndex) === flight.cardIndex
  ));
  if (!source) {
    delayedStackSlam(eventType, 120);
    return;
  }

  const sourceRect = source.getBoundingClientRect();
  const targetRect = els.topCard.getBoundingClientRect();
  const clone = source.cloneNode(true);
  clone.classList.remove("stable", "playable");
  clone.classList.add("flying-card", "in-flight");
  clone.style.left = `${sourceRect.left}px`;
  clone.style.top = `${sourceRect.top}px`;
  clone.style.width = `${sourceRect.width}px`;
  clone.style.height = `${sourceRect.height}px`;
  document.body.appendChild(clone);
  source.classList.add("leaving");

  const targetX = targetRect.left + targetRect.width / 2 - (sourceRect.left + sourceRect.width / 2);
  const targetY = targetRect.top + targetRect.height / 2 - (sourceRect.top + sourceRect.height / 2);
  const rotation = flight.card.type === "wild" ? 18 : -10;
  const animation = clone.animate(
    [
      { transform: "translate(0, 0) scale(1) rotate(0deg)", offset: 0 },
      { transform: `translate(${targetX * 0.48}px, ${targetY * 0.36 - 80}px) scale(1.2) rotate(${rotation * 0.55}deg)`, offset: 0.55 },
      { transform: `translate(${targetX}px, ${targetY}px) scale(1.42) rotate(${rotation}deg)`, offset: 1 },
    ],
    {
      duration: 720,
      easing: "cubic-bezier(.16, .9, .25, 1)",
      fill: "forwards",
    }
  );

  animation.onfinish = () => {
    clone.remove();
    delayedStackSlam(eventType, 0);
  };
}

function delayedStackSlam(eventType, delay) {
  if (!(eventType === "play" || eventType === "power" || eventType === "win")) {
    return;
  }
  setTimeout(() => {
    els.topCard.classList.remove("slam");
    void els.topCard.offsetWidth;
    els.topCard.classList.add("slam");
    setTimeout(() => els.topCard.classList.remove("slam"), 650);
  }, delay);
}

function triggerEffects(eventType, state) {
  if (!eventType) {
    return;
  }

  const effects = {
    start: ["READY", "zap"],
    draw: ["WHOOSH", "draw"],
    pass: ["SKIP", "pass"],
    play: ["KAPOW", "play"],
    power: ["BOOM", "power"],
    win: ["VICTORY", "win"],
    tick: ["ZAP", "tick"]
  };
  const [word, sound] = effects[eventType] || effects.tick;

  if (eventType !== "start") {
    burst(word, eventType);
    playImpactSound(sound);
  }

  if (state.players.some((player) => player.uno_declared)) {
    setTimeout(() => {
      burst("UNO", "uno");
      playImpactSound("uno");
    }, 220);
  }
}

function burst(word, type) {
  const element = document.createElement("div");
  element.className = `impact-word ${type}`;
  element.textContent = word;
  element.style.left = `${28 + Math.random() * 44}%`;
  element.style.top = `${18 + Math.random() * 54}%`;
  element.style.transform = `rotate(${Math.random() * 24 - 12}deg)`;
  els.impactLayer.appendChild(element);
  setTimeout(() => element.remove(), 900);
}

function playImpactSound(type) {
  if (!soundEnabled || !audioContext) {
    return;
  }

  const now = audioContext.currentTime;
  const gain = audioContext.createGain();
  gain.connect(audioContext.destination);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.18, now + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.28);

  const osc = audioContext.createOscillator();
  osc.type = type === "power" || type === "win" ? "sawtooth" : "square";
  osc.frequency.setValueAtTime(frequencyFor(type), now);
  osc.frequency.exponentialRampToValueAtTime(frequencyFor(type) * 0.55, now + 0.22);
  osc.connect(gain);
  osc.start(now);
  osc.stop(now + 0.3);

  if (type === "power" || type === "win") {
    const second = audioContext.createOscillator();
    second.type = "triangle";
    second.frequency.setValueAtTime(frequencyFor(type) * 1.7, now + 0.04);
    second.frequency.exponentialRampToValueAtTime(frequencyFor(type) * 0.9, now + 0.25);
    second.connect(gain);
    second.start(now + 0.04);
    second.stop(now + 0.32);
  }
}

function frequencyFor(type) {
  return {
    start: 520,
    draw: 360,
    pass: 240,
    play: 620,
    power: 110,
    win: 740,
    uno: 880,
    tick: 420
  }[type] || 420;
}

function tiltFor(index) {
  return ((index % 5) - 2) * 2.2;
}

function playerSignature(player) {
  return JSON.stringify({
    id: player.id,
    name: player.name,
    current: player.is_current_turn,
    uno: player.uno_declared,
    playable: player.playable_indexes,
    hand: player.hand.map(cardSignature),
  });
}

function cardSignature(card) {
  if (!card) {
    return "";
  }
  return JSON.stringify([card.color, card.value, card.type, card.chosen_color || null]);
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
  const value = card.value.replaceAll("_", " ");
  return color ? `${color} ${value}` : value;
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

function structuredCloneSafe(value) {
  return JSON.parse(JSON.stringify(value));
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
