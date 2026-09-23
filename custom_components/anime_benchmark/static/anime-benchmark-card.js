class AnimeBenchmarkCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      title_entity: "text.anime_benchmark_title",
      button_entity: "button.anime_benchmark_calculate",
      rating_entity: "sensor.anime_benchmark_rating",
      ...config,
    };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  safeAniListUrl(value) {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === "anilist.co" ? url.href : null;
    } catch (_) {
      return null;
    }
  }

  async calculate() {
    const input = this.shadowRoot.querySelector("input");
    const value = input?.value.trim();
    if (!value) return;
    await this._hass.callService("text", "set_value", {
      entity_id: this.config.title_entity,
      value,
    });
    await this._hass.callService("button", "press", {
      entity_id: this.config.button_entity,
    });
  }

  render() {
    if (!this._hass || !this.shadowRoot) return;
    const titleState = this._hass.states[this.config.title_entity];
    const ratingState = this._hass.states[this.config.rating_entity];
    const a = ratingState?.attributes || {};
    const rating = ratingState?.state && !["unknown", "unavailable"].includes(ratingState.state)
      ? ratingState.state
      : null;
    const anilistUrl = this.safeAniListUrl(a.anilist_url);
    const link = anilistUrl
      ? `<a href="${this.esc(anilistUrl)}" target="_blank" rel="noopener noreferrer">AniList ↗</a>`
      : "";
    const cover = a.cover_url
      ? `<img src="${this.esc(a.cover_url)}" alt="${this.esc(a.title || "Anime cover")}" />`
      : "";
    const yearFormat = [a.year, a.format].filter(Boolean).join(" · ");
    const result = a.error
      ? `<div class="error">${this.esc(a.error)}</div>`
      : rating
        ? `<div class="result">${cover}<div class="body"><div class="found">${this.esc(a.title || "")}</div><div class="rating">★ ${this.esc(rating)}</div><div class="meta">${this.esc(yearFormat)}</div><div class="meta">Confidence: ${this.esc(a.confidence || "—")} · ${this.esc(a.model_version || "")}</div><div class="genres">${this.esc((a.genres || []).join(" · "))}</div>${link}</div></div>`
        : "";

    this.shadowRoot.innerHTML = `
      <style>
        ha-card{padding:16px;border-radius:var(--ha-card-border-radius,12px)}
        .search{display:flex;gap:10px}.search input{flex:1;min-width:0;padding:11px 12px;border:1px solid var(--divider-color);border-radius:10px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}.search button{padding:0 16px;border:0;border-radius:10px;background:var(--primary-color);color:var(--text-primary-color,#fff);font-weight:600;cursor:pointer}.search button:disabled{opacity:.55;cursor:default}.result{display:flex;gap:14px;margin-top:16px}.result img{width:82px;min-width:82px;aspect-ratio:2/3;border-radius:10px;object-fit:cover}.body{min-width:0}.found{font-weight:700}.rating{font-size:30px;font-weight:800;margin:4px 0}.meta,.genres{color:var(--secondary-text-color);font-size:13px;margin:3px 0}.error{margin-top:12px;color:var(--error-color)}a{display:inline-block;margin-top:8px;color:var(--primary-color);font-weight:600;text-decoration:none}
      </style>
      <ha-card header="Anime Benchmark">
        <div class="search"><input value="${this.esc(titleState?.state || "")}" placeholder="Název anime"><button ${a.busy ? "disabled" : ""}>${a.busy ? "Počítám…" : "Vyhodnotit"}</button></div>
        ${result}
      </ha-card>`;
    this.shadowRoot.querySelector("button")?.addEventListener("click", () => this.calculate());
    this.shadowRoot.querySelector("input")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") this.calculate();
    });
  }

  getCardSize() { return 3; }
}

customElements.define("anime-benchmark-card", AnimeBenchmarkCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "anime-benchmark-card",
  name: "Anime Benchmark",
  description: "AniList-based personal benchmark rating",
});
