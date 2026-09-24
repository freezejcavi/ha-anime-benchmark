const ANIME_BENCHMARK_UI_VERSION = "0.3.0";

class AnimeBenchmarkCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      title_entity: "text.anime_benchmark_title",
      rating_entity: "sensor.anime_benchmark_rating",
      height: 390,
      ...config,
    };
    const height = Math.max(320, Math.min(700, Number(this.config.height) || 390));
    this.style.setProperty("--anime-benchmark-card-height", `${height}px`);
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._ensureStructure();
  }

  set hass(hass) {
    this._hass = hass;
    this._ensureStructure();
    this._updateFromHass();
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

  catalogBadge(catalog) {
    if (!catalog) return "";
    const tracked = Boolean(catalog.tracked);
    const label = tracked ? "TRACKED" : "NEW";
    const cls = tracked ? "tracked" : "new";
    const detail = tracked
      ? `V trackeru: ${catalog.canonical_title || "známá franchise"} · ${catalog.match_type || "match"}`
      : "V lokálním tracker katalogu nenalezeno";
    return `<span class="catalog-badge ${cls}" title="${this.esc(detail)}">${label}</span>`;
  }

  _ensureStructure() {
    if (!this.shadowRoot || this._initialized) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block}
        ha-card{
          height:var(--anime-benchmark-card-height,390px);
          border-radius:var(--ha-card-border-radius,12px);
          overflow:hidden;
        }
        .layout{
          height:100%;
          box-sizing:border-box;
          padding:18px 16px 12px;
          display:flex;
          flex-direction:column;
          min-height:0;
        }
        .heading{
          flex:0 0 auto;
          font-size:24px;
          font-weight:500;
          line-height:1.2;
          margin:2px 0 16px;
        }
        .search{display:flex;gap:10px;flex:0 0 auto}
        .search input{
          flex:1;min-width:0;padding:11px 12px;
          border:1px solid var(--divider-color);
          border-radius:10px;
          background:var(--card-background-color);
          color:var(--primary-text-color);
          font:inherit
        }
        .search button,.pick{
          padding:0 16px;border:0;border-radius:10px;
          background:var(--primary-color);
          color:var(--text-primary-color,#fff);
          font-weight:600;cursor:pointer
        }
        .search button:disabled,.pick:disabled{opacity:.55;cursor:default}
        .status{
          display:flex;align-items:center;gap:8px;
          flex:0 0 auto;
          margin-top:12px;padding:9px 11px;border-radius:9px;
          background:var(--secondary-background-color);font-size:13px;
          min-width:0
        }
        #status-text{
          min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap
        }
        .dot{width:8px;height:8px;border-radius:50%;background:var(--secondary-text-color);flex:0 0 auto}
        .status.busy .dot{background:var(--primary-color);animation:pulse 1s ease-in-out infinite}
        .status.done .dot{background:var(--success-color,#4caf50)}
        .status.error .dot{background:var(--error-color)}
        @keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
        .elapsed{margin-left:auto;color:var(--secondary-text-color);flex:0 0 auto}
        .scroll-region{
          flex:1 1 auto;
          min-height:0;
          overflow-y:auto;
          overflow-x:hidden;
          scrollbar-gutter:stable;
          margin-top:10px;
          padding-right:4px;
        }
        .scroll-region:empty{margin-top:0}
        .result{display:flex;gap:14px;padding:2px 0 8px}
        .result img{width:82px;min-width:82px;aspect-ratio:2/3;border-radius:10px;object-fit:cover}
        .body{min-width:0}
        .found,.candidate .title{
          font-weight:700;
          display:-webkit-box;
          -webkit-box-orient:vertical;
          -webkit-line-clamp:2;
          overflow:hidden;
          overflow-wrap:anywhere
        }
        .rating{font-size:30px;font-weight:800;margin:4px 0}
        .meta,.genres{color:var(--secondary-text-color);font-size:13px;margin:3px 0}
        .genres{
          display:-webkit-box;
          -webkit-box-orient:vertical;
          -webkit-line-clamp:2;
          overflow:hidden;
          overflow-wrap:anywhere
        }
        .error{padding:6px 0;color:var(--error-color);overflow-wrap:anywhere}
        a{display:inline-block;margin-top:8px;color:var(--primary-color);font-weight:600;text-decoration:none}
        .candidates{display:grid;gap:8px;padding:2px 0 8px}
        .candidate{
          display:flex;align-items:center;gap:10px;
          padding:8px;border:1px solid var(--divider-color);
          border-radius:10px;min-height:64px;box-sizing:border-box
        }
        .candidate img{width:44px;height:62px;object-fit:cover;border-radius:6px;flex:0 0 auto}
        .candidate .info{min-width:0;flex:1}
        .candidate .sub{font-size:12px;color:var(--secondary-text-color);margin-top:2px}
        .candidate .pick{height:34px;padding:0 12px;flex:0 0 auto}
        .catalog-badge{
          display:inline-flex;align-items:center;
          margin-top:5px;padding:2px 7px;border-radius:999px;
          font-size:10px;font-weight:800;letter-spacing:.35px;
          line-height:1.5
        }
        .catalog-badge.tracked{
          background:color-mix(in srgb,var(--success-color,#4caf50) 18%,transparent);
          color:var(--success-color,#66bb6a)
        }
        .catalog-badge.new{
          background:color-mix(in srgb,var(--warning-color,#ff9800) 18%,transparent);
          color:var(--warning-color,#ffb74d)
        }
        .ui-version{
          float:right;
          margin-left:8px;
          opacity:.7;
          font-size:11px
        }
        details{
          flex:0 0 auto;
          margin-top:8px;border-top:1px solid var(--divider-color);padding-top:8px
        }
        summary{cursor:pointer;color:var(--secondary-text-color);font-size:13px}
        .log{
          margin-top:7px;
          display:grid;gap:4px;
          max-height:72px;overflow-y:auto;
          font-size:12px;color:var(--secondary-text-color)
        }
        .log div{overflow-wrap:anywhere}
      </style>
      <ha-card>
        <div class="layout">
          <div class="heading">Anime Benchmark</div>
          <div class="search">
            <input maxlength="160" placeholder="Název anime">
            <button>Vyhodnotit</button>
          </div>
          <div id="status" class="status">
            <span class="dot"></span>
            <span id="status-text">Připraveno</span>
            <span id="elapsed" class="elapsed"></span>
          </div>
          <div class="scroll-region">
            <div id="candidates"></div>
            <div id="output"></div>
          </div>
          <details id="activity-wrap">
            <summary>Aktivita <span class="ui-version">UI ${ANIME_BENCHMARK_UI_VERSION}</span></summary>
            <div id="activity" class="log"></div>
          </details>
        </div>
      </ha-card>`;

    this._input = this.shadowRoot.querySelector("input");
    this._button = this.shadowRoot.querySelector(".search button");
    this._status = this.shadowRoot.querySelector("#status");
    this._statusText = this.shadowRoot.querySelector("#status-text");
    this._elapsed = this.shadowRoot.querySelector("#elapsed");
    this._candidates = this.shadowRoot.querySelector("#candidates");
    this._output = this.shadowRoot.querySelector("#output");
    this._activity = this.shadowRoot.querySelector("#activity");

    this._button?.addEventListener("click", () => this.search());
    this._input?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") this.search();
    });
    this._candidates?.addEventListener("click", (event) => {
      const button = event.target.closest?.("button.pick");
      if (!button || button.disabled) return;
      this.selectCandidate(Number(button.dataset.id));
    });
    this._initialized = true;
  }

  _setLocalStatus(message, kind = "busy") {
    if (!this._status || !this._statusText) return;
    this._status.className = `status ${kind}`;
    this._statusText.textContent = message;
    if (this._elapsed) this._elapsed.textContent = "";
  }

  _updateFromHass() {
    if (!this._hass || !this._initialized) return;

    const titleState = this._hass.states[this.config.title_entity];
    const ratingState = this._hass.states[this.config.rating_entity];
    const a = ratingState?.attributes || {};

    if (
      this._input &&
      this.shadowRoot.activeElement !== this._input &&
      !this._input.value
    ) {
      this._input.value = titleState?.state || a.query || "";
    }

    const busy = Boolean(a.busy) || Boolean(this._localBusy);
    if (this._button) {
      this._button.disabled = busy;
      this._button.textContent = busy ? "Pracuji…" : "Vyhodnotit";
    }

    if (!this._localBusy) {
      const phase = a.phase || "idle";
      const kind = phase === "error" ? "error" : phase === "done" ? "done" : busy ? "busy" : "";
      this._status.className = `status ${kind}`;
      this._statusText.textContent = a.status_text || "Připraveno";
      this._elapsed.textContent = a.elapsed_ms != null ? `${(Number(a.elapsed_ms) / 1000).toFixed(2)} s` : "";
    }

    this._renderActivity(a.activity_log || []);
    this._renderCandidates(a.candidates || [], busy);
    this._renderResult(ratingState, a);
  }

  _renderActivity(log) {
    if (!this._activity) return;
    this._activity.innerHTML = (log || []).map((line) => `<div>↳ ${this.esc(line)}</div>`).join("");
  }

  _renderCandidates(candidates, busy) {
    if (!this._candidates) return;

    const list = Array.isArray(candidates) ? candidates : [];
    const signature = JSON.stringify(
      list.map((item) => [
        item.id,
        item.title,
        item.year,
        item.format,
        item.cover_url,
        item.anilist_url,
        item.catalog?.tracked,
        item.catalog?.franchise_id,
        item.catalog?.match_type,
      ])
    );

    // HA pushes the full hass object on every state change anywhere in the system.
    // Do not rebuild interactive candidate DOM unless the candidate payload itself changed.
    if (signature === this._candidateSignature) {
      this._candidates.querySelectorAll("button.pick").forEach((button) => {
        button.disabled = Boolean(busy);
      });
      return;
    }

    this._candidateSignature = signature;

    if (!list.length) {
      this._candidates.innerHTML = "";
      return;
    }

    this._candidates.innerHTML = `<div class="candidates">${list.map((item) => {
      const url = this.safeAniListUrl(item.anilist_url);
      const cover = item.cover_url ? `<img src="${this.esc(item.cover_url)}" alt="">` : "";
      const sub = [item.year, item.format].filter(Boolean).join(" · ");
      const catalog = this.catalogBadge(item.catalog);
      return `<div class="candidate">
        ${cover}
        <div class="info">
          <div class="title" title="${this.esc(item.title || "")}">${this.esc(item.title || "")}</div>
          <div class="sub">${this.esc(sub)}</div>
          ${catalog}
          ${url ? `<a href="${this.esc(url)}" target="_blank" rel="noopener noreferrer">AniList ↗</a>` : ""}
        </div>
        <button class="pick" data-id="${this.esc(item.id)}" ${busy ? "disabled" : ""}>Vybrat</button>
      </div>`;
    }).join("")}</div>`;
  }

  _renderResult(ratingState, a) {
    if (!this._output) return;
    if (a.error) {
      this._output.innerHTML = `<div class="error">${this.esc(a.error)}</div>`;
      return;
    }
    const rating =
      ratingState?.state && !["unknown", "unavailable"].includes(ratingState.state)
        ? ratingState.state
        : null;
    if (!rating || (a.candidates || []).length) {
      this._output.innerHTML = "";
      return;
    }

    const anilistUrl = this.safeAniListUrl(a.anilist_url);
    const link = anilistUrl
      ? `<a href="${this.esc(anilistUrl)}" target="_blank" rel="noopener noreferrer">AniList ↗</a>`
      : "";
    const cover = a.cover_url
      ? `<img src="${this.esc(a.cover_url)}" alt="${this.esc(a.title || "Anime cover")}" />`
      : "";
    const yearFormat = [a.year, a.format].filter(Boolean).join(" · ");
    const catalog = this.catalogBadge(a.catalog);

    this._output.innerHTML = `
      <div class="result">
        ${cover}
        <div class="body">
          <div class="found" title="${this.esc(a.title || "")}">${this.esc(a.title || "")}</div>
          ${catalog}
          <div class="rating">★ ${this.esc(rating)}</div>
          <div class="meta">${this.esc(yearFormat)}</div>
          <div class="meta">Confidence: ${this.esc(a.confidence || "—")} · ${this.esc(a.model_version || "")}</div>
          <div class="genres">${this.esc((a.genres || []).join(" · "))}</div>
          ${link}
        </div>
      </div>`;
  }

  async _callSearch(data) {
    if (!this._hass) return;
    this._localBusy = true;
    this._setLocalStatus("Odesílám dotaz…", "busy");
    this._updateFromHass();
    try {
      await this._hass.callService("anime_benchmark", "search", data);
    } catch (error) {
      this._setLocalStatus(`Chyba volání HA: ${error?.message || error}`, "error");
    } finally {
      this._localBusy = false;
      this._updateFromHass();
    }
  }

  async search() {
    const value = this._input?.value.trim();
    if (!value) {
      this._setLocalStatus("Zadej název anime", "error");
      return;
    }
    await this._callSearch({ query: value });
  }

  async selectCandidate(anilistId) {
    const ratingState = this._hass?.states[this.config.rating_entity];
    const query = ratingState?.attributes?.query || this._input?.value.trim();
    if (!query || !anilistId) return;
    await this._callSearch({ query, anilist_id: anilistId });
  }

  getCardSize() { return 5; }
}

if (!customElements.get("anime-benchmark-card")) {
  customElements.define("anime-benchmark-card", AnimeBenchmarkCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "anime-benchmark-card")) {
  window.customCards.push({
    type: "anime-benchmark-card",
    name: "Anime Benchmark",
    description: "AniList-based personal benchmark rating",
  });
}
