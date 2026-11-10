const CARD_TYPE = "strasbourg-piscines-card";

const STATUS = {
  GREEN: { label: "Affluence faible", colour: "#2b9b68" },
  ORANGE: { label: "Affluence modérée", colour: "#dc8b22" },
  RED: { label: "Forte affluence", colour: "#c94a45" },
  BLACK: { label: "Information indisponible", colour: "#65727d" },
  CLOSED: { label: "Fermée", colour: "#65727d" },
};

class StrasbourgPiscinesCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    const entities = this._entitiesFromConfig(config);
    if (!entities.length) {
      throw new Error("La carte Piscines nécessite une ou plusieurs entités.");
    }

    this._config = {
      max_rows: 6,
      show_schedule: true,
      ...config,
      entities,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    const rows = Math.min(this._entitiesFromConfig(this._config).length, this._maxRows());
    return Math.max(3, rows + 2);
  }

  _render() {
    if (!this._config) {
      return;
    }

    const rows = this._rows();
    const missing = this._config.entities.filter((entityId) => !this._hass?.states?.[entityId]);
    const title = this._config.title || "Piscines Strasbourg";
    const updatedAt = this._latestUpdate(rows);

    this.shadowRoot.innerHTML = `
      ${this._styles()}
      <ha-card>
        <header class="card-header">
          <div class="title"><span class="wave-mark" aria-hidden="true">≈</span>${this._escape(title)}</div>
          ${updatedAt ? `<div class="updated">Mis à jour à ${this._escape(updatedAt)}</div>` : ""}
        </header>
        ${rows.length ? this._renderRows(rows) : this._renderEmpty(missing)}
        ${missing.length && rows.length ? `<div class="missing">${this._escape(this._missingText(missing))}</div>` : ""}
      </ha-card>
    `;
  }

  _renderRows(rows) {
    return `
      <div class="column-headings" aria-hidden="true"><span>Piscine</span><span>Affluence</span></div>
      <div class="pools" role="list">${rows.map((row) => this._renderRow(row)).join("")}</div>
      <footer>Données temps réel de l'Eurométropole de Strasbourg</footer>
    `;
  }

  _renderRow(row) {
    const openLabel = row.isOpen === true ? "Ouverte" : row.isOpen === false ? "Fermée" : "État non communiqué";
    const schedule = this._config.show_schedule && row.schedule ? `<div class="schedule">${this._escape(row.schedule)}</div>` : "";

    return `
      <article class="pool-row" role="listitem">
        <div class="details">
          <div class="name">${this._escape(row.name)}</div>
          <div class="open-state ${row.isOpen === false ? "closed" : ""}"><span></span>${this._escape(openLabel)}</div>
          ${schedule}
        </div>
        <div class="status" style="--status-colour:${row.status.colour}">
          <span class="status-dot" aria-hidden="true"></span>
          <span>${this._escape(row.status.label)}</span>
        </div>
      </article>
    `;
  }

  _renderEmpty(missing) {
    if (missing.length) {
      return `<div class="empty">${this._escape(this._missingText(missing))}</div>`;
    }
    return '<div class="empty">Aucune piscine à afficher.</div>';
  }

  _rows() {
    return this._config.entities
      .map((entityId) => {
        const state = this._hass?.states?.[entityId];
        if (!state) {
          return null;
        }
        const attributes = state.attributes || {};
        const code = String(state.state || attributes.realtime_status || "").toUpperCase();
        return {
          name: attributes.pool_name || this._nameFromState(state, "Affluence"),
          isOpen: typeof attributes.is_open === "boolean" ? attributes.is_open : null,
          status: STATUS[code] || { label: code || "Information non communiquée", colour: "#65727d" },
          schedule: this._formatSchedule(attributes.today_schedule),
          updatedAt: attributes.data_fetched_at || attributes.source_updated_at,
        };
      })
      .filter(Boolean)
      .slice(0, this._maxRows());
  }

  _formatSchedule(schedule) {
    if (!Array.isArray(schedule) || !schedule.length) {
      return "";
    }
    const slots = schedule
      .map((slot) => {
        const startHour = Number(slot?.opening_hour);
        const startMinute = Number(slot?.opening_minute);
        const endHour = Number(slot?.closing_hour);
        const endMinute = Number(slot?.closing_minute);
        if (![startHour, startMinute, endHour, endMinute].every(Number.isFinite)) {
          return "";
        }
        return `${String(startHour).padStart(2, "0")}:${String(startMinute).padStart(2, "0")}–${String(endHour).padStart(2, "0")}:${String(endMinute).padStart(2, "0")}`;
      })
      .filter(Boolean);
    return slots.length ? `Aujourd'hui : ${slots.join(" · ")}` : "";
  }

  _latestUpdate(rows) {
    const dates = rows
      .map((row) => new Date(row.updatedAt))
      .filter((date) => !Number.isNaN(date.getTime()));
    if (!dates.length) {
      return "";
    }
    const latest = new Date(Math.max(...dates.map((date) => date.getTime())));
    return new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" }).format(latest);
  }

  _entitiesFromConfig(config) {
    const configured = config?.entities || (config?.entity ? [config.entity] : []);
    const values = Array.isArray(configured) ? configured : [configured];
    return values
      .map((item) => typeof item === "string" ? item : item?.entity)
      .filter((item) => typeof item === "string" && item.trim());
  }

  _nameFromState(state, suffix) {
    const name = state.attributes?.friendly_name || state.entity_id;
    return String(name).replace(new RegExp(`\\s*${suffix}$`, "i"), "");
  }

  _missingText(missing) {
    return missing.length === 1
      ? `Entité introuvable : ${missing[0]}`
      : `${missing.length} entités configurées sont introuvables.`;
  }

  _maxRows() {
    const value = Number(this._config?.max_rows);
    return Number.isInteger(value) && value > 0 ? value : 6;
  }

  _escape(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _styles() {
    return `
      <style>
        :host { display: block; }
        ha-card { overflow: hidden; }
        .card-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 18px 14px; border-bottom: 1px solid var(--divider-color); background: color-mix(in srgb, var(--card-background-color) 88%, var(--primary-text-color)); }
        .title { display: flex; align-items: center; gap: 9px; font-size: 15px; font-weight: 700; letter-spacing: .03em; text-transform: uppercase; }
        .wave-mark { display: grid; place-items: center; width: 25px; height: 25px; border-radius: 50%; background: #25aeb8; color: #fff; font-size: 25px; font-weight: 700; line-height: 1; }
        .updated { color: var(--secondary-text-color); font-size: 12px; white-space: nowrap; }
        .column-headings { display: flex; justify-content: space-between; padding: 14px 18px 7px; color: var(--secondary-text-color); font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
        .pools { margin: 0 18px; border-top: 1px solid var(--divider-color); }
        .pool-row { display: grid; grid-template-columns: minmax(0, 1fr) 122px; gap: 14px; align-items: center; min-height: 84px; border-bottom: 1px solid var(--divider-color); }
        .details { min-width: 0; }
        .name { overflow: hidden; color: var(--primary-text-color); font-size: 15px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
        .open-state { display: flex; align-items: center; gap: 5px; margin-top: 6px; color: #207c58; font-size: 12px; font-weight: 600; }
        .open-state span { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
        .open-state.closed { color: var(--error-color, #c94a45); }
        .schedule { overflow: hidden; margin-top: 4px; color: var(--secondary-text-color); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
        .status { display: flex; align-items: center; justify-content: flex-end; gap: 6px; color: var(--status-colour); font-size: 12px; font-weight: 700; line-height: 1.2; text-align: right; }
        .status-dot { width: 9px; height: 9px; flex: 0 0 auto; border-radius: 50%; background: currentColor; box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 16%, transparent); }
        footer { padding: 11px 18px 14px; color: var(--secondary-text-color); font-size: 11px; }
        .empty, .missing { margin: 0 18px 18px; padding: 15px 0; color: var(--secondary-text-color); border-top: 1px solid var(--divider-color); }
        .missing { margin-top: 0; color: var(--warning-color, #bd8500); font-size: 12px; }
        @media (max-width: 480px) {
          .card-header, .column-headings { padding-left: 14px; padding-right: 14px; }
          .pools, .empty, .missing { margin-left: 14px; margin-right: 14px; }
          footer { padding-left: 14px; padding-right: 14px; }
          .pool-row { grid-template-columns: minmax(0, 1fr) 105px; gap: 9px; }
          .updated { display: none; }
        }
      </style>
    `;
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, StrasbourgPiscinesCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === `custom:${CARD_TYPE}`)) {
  window.customCards.push({
    type: `custom:${CARD_TYPE}`,
    name: "Strasbourg Piscines",
    description: "Affiche l'ouverture, l'affluence et les horaires des piscines de Strasbourg.",
  });
}
