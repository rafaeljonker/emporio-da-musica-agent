// Shared mockup helpers: Lucide sprite, chat transcript rendering, metrics (collapsed "Métricas" in the demo strip).
// Mockup only. In the build these become React components fed by the /chat SSE stream.
const ICONS = {
  send: '<path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/><path d="m21.854 2.147-10.94 10.939"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
  flask: '<path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2"/><path d="M6.453 15h11.094"/><path d="M8.5 2h7"/>',
  check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  circle: '<circle cx="12" cy="12" r="10"/>',
  server: '<rect width="20" height="8" x="2" y="2" rx="2"/><rect width="20" height="8" x="2" y="14" rx="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/>',
  cpu: '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  user: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
  alert: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
  wifioff: '<path d="M12 20h.01"/><path d="M8.5 16.429a5 5 0 0 1 7 0"/><path d="M5 12.859a10 10 0 0 1 5.17-2.69"/><path d="M19 12.859a10 10 0 0 0-2.007-1.523"/><path d="M2 8.82a15 15 0 0 1 4.177-2.643"/><path d="M22 8.82a15 15 0 0 0-11.288-3.764"/><path d="m2 2 20 20"/>',
  gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
  laptop: '<path d="M18 5a2 2 0 0 1 2 2v8.526a2 2 0 0 0 .212.897l1.068 2.127a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45l1.068-2.127A2 2 0 0 0 4 15.526V7a2 2 0 0 1 2-2z"/><path d="M20.054 15.987H3.946"/>',
};
const AVATAR = "../../../../branding/emporio-da-musica/identity/assets/avatar-disc-concept.jpg";
const $ = (s) => document.querySelector(s);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const icon = (n, size = "") => `<svg class="icon ${size}" aria-hidden="true" focusable="false"><use href="#i-${n}"/></svg>`;
const esc = (t) => t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const brl = (v, d = 2) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: d, maximumFractionDigits: d });
const num = (v, d = 0) => v.toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const now = () => new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
// Pacing (backend-owned in the build): bubble 1 at 0 ms; bubbles 2-3 length-proportional; total capped at 3 s per reply.
const pace = (text = "") => Math.min(2400, Math.max(700, 400 + text.length * 22));
const PACE_CAP_MS = 3000;

document.body.insertAdjacentHTML("afterbegin",
  `<svg hidden aria-hidden="true">${Object.entries(ICONS).map(([k, v]) => `<symbol id="i-${k}" viewBox="0 0 24 24">${v}</symbol>`).join("")}</svg>`);
document.querySelectorAll("[data-icon]").forEach((el) => el.insertAdjacentHTML("afterbegin", icon(el.dataset.icon, el.dataset.size || "")));
const params = new URLSearchParams(location.search);
if (params.has("embed")) document.body.classList.add("embed");

const Chat = {
  busy: false, onSend: null, local: false, history: [], session: { turns: 0, tokens: 0, cost: 0, warm: null },
  init() {
    this.log = $("#log"); this.typing = $("#typing"); this.input = $("#msg"); this.send = $("#send"); this.body = this.log.closest(".body");
    // aria-disabled (not disabled): the button keeps focus after Space/Enter/click (SC 2.4.3).
    const sync = () => this.send.setAttribute("aria-disabled", String(this.busy || !this.input.value.trim()));
    this.input.addEventListener("input", () => { this.input.style.height = "auto"; this.input.style.height = this.input.scrollHeight + 2 + "px"; sync(); });
    this.input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.submit(); } });
    $("#composer").addEventListener("submit", (e) => { e.preventDefault(); this.submit(); });
    this.sync = sync; sync();
  },
  submit() {
    const text = this.input.value.trim();
    if (!text || this.busy) return;
    this.input.value = ""; this.input.style.height = "auto"; this.sync();
    this.onSend?.(text);
  },
  // Auto-scroll only when the reader is already near the bottom (build adds the "Novas mensagens" pill).
  add(node, force = false) {
    const b = this.body, stick = force || b.scrollHeight - b.scrollTop - b.clientHeight < 80;
    this.log.append(node);
    if (stick) b.scrollTop = b.scrollHeight;
    return node;
  },
  el(cls, html) { const d = document.createElement("div"); d.className = cls; d.innerHTML = html; return d; },
  user(text, queuedLine = "") {
    return this.add(this.el("group user", `<div class="bubble"><span class="sr-only">Você: </span>${esc(text)}</div>` +
      (queuedLine ? `<p class="queued meta">${icon("clock", "sm")}<span class="q-text">${esc(queuedLine)}</span></p>` : `<p class="meta tnum" aria-hidden="true">${now()}</p>`)), true);
  },
  divider(text) { const p = document.createElement("p"); p.className = "divider"; p.textContent = text; return this.add(p); },
  setTyping(on) {
    this.typing.classList.toggle("on", on);
    $("#typing-text").textContent = on ? "O assistente está digitando" : "";
  },
  render(item) {
    if (item.product) {
      const p = item.product, id = "p" + Math.random().toString(36).slice(2, 7);
      return `<article class="product" aria-labelledby="${id}"><p class="product-name" id="${id}">${esc(p.name)}</p>` +
        (p.honest ? `<span class="honest">${icon("check", "sm")}Na medida pro seu nível</span>` : "") +
        `<p class="price tnum">${brl(p.price, p.price % 1 ? 2 : 0)}</p><p class="pix tnum">${brl(p.price * 0.95)} no PIX (5% off)</p></article>`;
    }
    const label = item.handoff ? `<span class="handoff-label">${icon(item.handoff.icon || "user", "sm")}${esc(item.handoff.label)}</span>` : "";
    return `<div class="bubble"><span class="sr-only">Assistente: </span>${label}${esc(item.text)}</div>`;
  },
  // opts.failAfter = n: SSE error after n bubbles (partial reply). Bubbles already shown stay.
  async reply(items, m, opts = {}) {
    this.busy = true; this.sync(); this.setTyping(true);
    const server = m.guard + m.llm + m.tools + m.search;
    // ponytail: generation simulated with a capped sleep so the local variant does not wait 48 s in a mockup.
    await sleep(Math.min(3000, server * 1000));
    const g = this.el("group agent", "");
    let budget = PACE_CAP_MS, paced = 0;
    for (const [i, item] of items.entries()) {
      if (opts.failAfter === i) return this.partialError(g, opts.onRetry);
      if (i > 0) { const d = Math.min(budget, pace(item.text || "")); budget -= d; paced += d; await sleep(d); }
      if (i === 0) this.add(g);
      g.querySelector(".avatar")?.replaceWith(Object.assign(document.createElement("span"), { className: "spacer" }));
      g.insertAdjacentHTML("beforeend", `<div class="row"><img class="avatar" src="${AVATAR}" alt="">${this.render(item)}</div>`);
      this.add(g);
    }
    this.setTyping(false);
    g.insertAdjacentHTML("beforeend", `<p class="meta"><span class="tnum" aria-hidden="true">${now()}</span></p>`);
    this.recordMetrics({ ...m, server, screen: server + paced / 1000 });
    this.busy = false; this.sync();
  },
  partialError(g, onRetry) {
    this.setTyping(false);
    const p = document.createElement("p");
    p.className = "reply-error";
    p.innerHTML = `Perdi o fio no meio da resposta. <button class="btn-link" type="button">Manda de novo?</button>`;
    g.after(p);
    p.querySelector("button").addEventListener("click", () => { p.remove(); this.input.focus(); onRetry?.(); }, { once: true });
    this.busy = false; this.sync();
  },
  recordMetrics(m) {
    const s = this.session; s.turns++; s.tokens += m.tin + m.tout; s.cost += m.cost;
    this.history.unshift(`Resposta ${s.turns} · ${num(m.screen, 1)} s · ${brl(m.cost, 4)} · ${m.what}`);
    this.renderMetrics(m);
  },
  renderMetrics(m) {
    const s = this.session, sum = $("#metrics-sum"), body = $("#metrics-body");
    if (!body) return;
    if (sum) sum.textContent = s.turns ? ` · ${s.turns} ${s.turns === 1 ? "resposta" : "respostas"} · ${brl(s.cost, 4)}` : "";
    const basis = this.local ? "R$ 0 (rodando na sua máquina)" : "Estimado: segundos de GPU × preço do Modal";
    const last = m ? `<p class="mp-h">Última resposta</p><dl>` +
      `<dt>Tokens</dt><dd>${num(m.tin)} de entrada · ${num(m.tout)} de saída</dd>` +
      `<dt>Tempo</dt><dd>${num(m.server, 1)} s no modelo · ${num(m.screen, 1)} s na tela<br><span class="muted">filtro ${num(m.guard, 2)} · geração ${num(m.llm, 1)} · ferramentas ${num(m.tools, 2)} · busca ${num(m.search, 2)}</span></dd>` +
      `<dt>Custo</dt><dd>${this.local ? "R$ 0" : brl(m.cost, 4)}<br><span class="muted">${basis}</span></dd></dl>` : "";
    body.innerHTML = last +
      `<p class="mp-h">Sessão</p><dl><dt>Respostas</dt><dd>${s.turns}</dd><dt>Tokens</dt><dd>${num(s.tokens)}</dd><dt>Custo</dt><dd>${brl(s.cost, 4)}</dd>` +
      (s.warm != null ? `<dt>Aquecimento</dt><dd>${s.warm} s</dd>` : "") + `</dl>` +
      (this.history.length ? `<p class="mp-h">Histórico</p><ol class="history">${this.history.map((h) => `<li>${esc(h)}</li>`).join("")}</ol>` : "");
  },
};
