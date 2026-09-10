const state = {
  filter: "all",
  devices: [],
  busy: new Set(),
  loading: true,
  homeId: null,
  homeName: null,
  meta: null,
};

function $(sel) { return document.querySelector(sel); }
function $all(sel) { return [...document.querySelectorAll(sel)]; }

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setStatus(msg, isErr = false) {
  const bar = $("#statusBar");
  if (!msg) {
    bar.hidden = true;
    bar.textContent = "";
    return;
  }
  bar.hidden = false;
  bar.classList.toggle("err", !!isErr);
  bar.textContent = msg;
}

async function api(path, options) {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.message || `HTTP ${r.status}`);
  return data;
}

/* ---------------- ícones ---------------- */

const ICONS = {
  bulb: '<path d="M9 21h6M10 24h4" /><path d="M12 3a7 7 0 0 0-4 12.7V18h8v-2.3A7 7 0 0 0 12 3Z" />',
  switch: '<rect x="4" y="2.5" width="16" height="19" rx="3" /><path d="M12 7v5" /><circle cx="12" cy="16" r="1.4" />',
  plug: '<path d="M9 2v6M15 2v6" /><path d="M6 8h12v3a6 6 0 0 1-6 6 6 6 0 0 1-6-6V8Z" /><path d="M12 17v5" />',
  ac: '<rect x="2.5" y="4" width="19" height="8" rx="2.5" /><path d="M6 8.5h8" /><path d="M6 15.5c1.6 0 1.6 2 3.2 2s1.6-2 3.2-2 1.6 2 3.2 2 1.6-2 3.2-2" /><path d="M6 19.5c1.6 0 1.6 2 3.2 2s1.6-2 3.2-2" />',
  tv: '<rect x="2.5" y="4" width="19" height="13" rx="2.5" /><path d="M8 21h8M12 17v4" />',
  remote: '<rect x="7" y="2.5" width="10" height="19" rx="3" /><circle cx="12" cy="7" r="1.3" /><path d="M9.5 12h5M9.5 15.5h5M9.5 19h5" />',
  meter: '<circle cx="12" cy="12" r="9" /><path d="M12 12 16 8" /><path d="M12 3v2M21 12h-2M12 21v-2M3 12h2" />',
  thermo: '<path d="M14 14.8V5a2 2 0 1 0-4 0v9.8a4.5 4.5 0 1 0 4 0Z" /><path d="M12 9v6" />',
  hub: '<circle cx="12" cy="17" r="2.5" /><path d="M6.5 12.5a7.5 7.5 0 0 1 11 0" /><path d="M3 8.8a12 12 0 0 1 18 0" />',
  garage: '<path d="M3 21V9.5L12 4l9 5.5V21" /><path d="M6.5 21v-8h11v8" /><path d="M6.5 16.5h11" />',
  pump: '<circle cx="12" cy="13" r="6" /><path d="M12 9.5v3.5l2.4 1.6" /><path d="M5 5h6" />',
  alarm: '<path d="M12 3a6 6 0 0 0-6 6c0 4.5-2 6-2 6h16s-2-1.5-2-6a6 6 0 0 0-6-6Z" /><path d="M10 19a2 2 0 0 0 4 0" />',
  chip: '<rect x="6" y="6" width="12" height="12" rx="2.5" /><path d="M10 2.5v3.5M14 2.5v3.5M10 18v3.5M14 18v3.5M2.5 10H6M2.5 14H6M18 10h3.5M18 14h3.5" />',
};

function iconNameFor(d) {
  const n = (d.name || "").toLowerCase();
  if (d.kind === "light" || /\bluz\b|l(â|a)mpada/.test(n)) return "bulb";
  if (/port(ã|a)o|garagem/.test(n)) return "garage";
  if (/bomba/.test(n)) return "pump";
  if (/alarme|sensor barrilete/.test(n)) return "alarm";
  if (/\btv\b|televis/.test(n)) return "tv";
  if (d.kind === "ac") return "ac";
  if (d.kind === "sensor") return "thermo";
  if (d.kind === "meter") return "meter";
  if (d.kind === "gateway") return "hub";
  if (d.kind === "ir_hub") return "remote";
  if (d.kind === "ir") return "tv";
  if (d.kind === "switch") return /plug|tomada|dvr/.test(n) ? "plug" : "switch";
  return "chip";
}

function icon(name, cls = "") {
  const path = ICONS[name] || ICONS.chip;
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}

const POWER_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 3v9"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/></svg>';

/* ---------------- helpers de estado ---------------- */

function kindLabel(kind) {
  return ({
    light: "Iluminação",
    ac: "Ar-condicionado",
    switch: "Interruptor / Tomada",
    meter: "Medidor de energia",
    sensor: "Sensor",
    gateway: "Gateway Zigbee",
    ir_hub: "Hub infravermelho",
    ir: "Controle infravermelho",
    other: "Outro",
  })[kind] || kind;
}

function isOffline(d) { return d.online === false; }

function channelsFor(device) {
  if (Array.isArray(device.channels) && device.channels.length) return device.channels;
  if (["sensor", "gateway", "ir_hub", "meter", "ac", "ir"].includes(device.kind)) return [];
  return [{ code: device.switch_code || null, label: "Controle", on: device.on }];
}

function busyKey(deviceId, code) { return `${deviceId}:${code || "power"}`; }

function isBusy(d, code) { return state.busy.has(busyKey(d.id, code)); }

function blocked(d, code) { return isOffline(d) || isBusy(d, code) ? "disabled" : ""; }

function readingValue(device, key, fallback = "--") {
  const item = device.readings?.[key];
  if (!item || item.value == null || item.value === "") return fallback;
  return `${item.value}${item.unit || ""}`;
}

function deviceIsOn(d) {
  if (typeof d.on === "boolean") return d.on;
  return channelsFor(d).some((c) => c.on === true);
}

/* ---------------- blocos de card ---------------- */

function metric(label, value, sub = "", cls = "") {
  return `
    <div class="metric ${cls}">
      <span class="metric-label">${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      ${sub ? `<small>${escapeHtml(sub)}</small>` : ""}
    </div>`;
}

function renderSensorBody(d) {
  return `
    <div class="metrics">
      ${metric("Temperatura", readingValue(d, "temperature"))}
      ${metric("Umidade", readingValue(d, "humidity"))}
      ${metric("Bateria", readingValue(d, "battery"))}
    </div>
    <p class="hint">Alerta fora de ${escapeHtml(String(d.status?.minitemp_set ?? "--"))}–${escapeHtml(String(d.status?.maxtemp_set ?? "--"))}°C ou ${escapeHtml(String(d.status?.minihum_set ?? "--"))}–${escapeHtml(String(d.status?.maxhum_set ?? "--"))}% de umidade.</p>
  `;
}

function renderMeterBody(d) {
  if (d.card === "triphase_meter") {
    return `
      <div class="metrics">
        ${metric("Total", readingValue(d, "total_power"), readingValue(d, "frequency", ""))}
        ${metric("Rede", readingValue(d, "energy_import_total"))}
        ${metric("Solar", readingValue(d, "energy_export_total"))}
        ${metric("L1", readingValue(d, "voltage_a"), `${readingValue(d, "power_a")} · ${readingValue(d, "current_a")}`, "phase-l1")}
        ${metric("L2", readingValue(d, "voltage_b"), `${readingValue(d, "power_b")} · ${readingValue(d, "current_b")}`, "phase-l2")}
        ${metric("L3", readingValue(d, "voltage_c"), `${readingValue(d, "power_c")} · ${readingValue(d, "current_c")}`, "phase-l3")}
      </div>
      <p class="hint">Trifásico PC473 · leitura por shadow/properties.</p>
    `;
  }
  return `
    <div class="metrics">
      ${metric("Tensão", readingValue(d, "voltage"))}
      ${metric("Frequência", readingValue(d, "frequency"))}
      ${metric("Total", readingValue(d, "total_power"))}
      ${metric("Canal A", readingValue(d, "power_a"), `${readingValue(d, "current_a")} · ${d.readings?.direction_a?.value || "—"}`)}
      ${metric("Canal B", readingValue(d, "power_b"), `${readingValue(d, "current_b")} · ${d.readings?.direction_b?.value || "—"}`)}
      ${metric("Energia", readingValue(d, "energy_import_total"), `rev ${readingValue(d, "energy_export_total")}`)}
    </div>
    <p class="hint">Medidor solar dual · calibração e reset bloqueados.</p>
  `;
}

function renderGatewayBody(d) {
  const st = d.readings?.master_state?.value || d.status?.master_state || "—";
  const alarm = d.readings?.alarm_active?.value || d.status?.alarm_active || "";
  return `
    <div class="metrics cols-2">
      ${metric("Estado", String(st))}
      ${metric("Alarme", String(alarm || "nenhum"))}
    </div>
    <p class="hint">Reset de fábrica bloqueado por segurança.</p>
  `;
}

function renderAcBody(d) {
  const chips = [];
  if (d.readings?.mode) chips.push(`<span class="chip">Modo <b>${escapeHtml(String(d.readings.mode.value))}</b></span>`);
  if (d.readings?.fan) chips.push(`<span class="chip">Vento <b>${escapeHtml(String(d.readings.fan.value))}</b></span>`);
  if (d.readings?.swing) chips.push(`<span class="chip">Swing <b>${escapeHtml(String(d.readings.swing.value))}</b></span>`);
  return `
    <div class="thermo">
      <button class="thermo-btn" type="button" data-act="temp-down" data-id="${d.id}" aria-label="Diminuir temperatura" ${blocked(d, "temp")}>−</button>
      <div class="thermo-value">
        ${d.temp != null ? `${d.temp}°` : "--°"}
        <small>TEMPERATURA</small>
      </div>
      <button class="thermo-btn" type="button" data-act="temp-up" data-id="${d.id}" aria-label="Aumentar temperatura" ${blocked(d, "temp")}>+</button>
    </div>
    ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
  `;
}

function renderToggle(d, code, label, on) {
  const stateText = on ? "LIGADO" : "DESLIGADO";
  return `
    <button class="toggle ${on ? "on" : ""}" type="button"
            data-act="toggle" data-id="${d.id}" data-code="${escapeHtml(code || "")}" data-next="${on ? "0" : "1"}"
            aria-pressed="${on}" ${blocked(d, code)}>
      <span class="toggle-text">
        <span class="toggle-label">${escapeHtml(label)}</span>
        <span class="toggle-state">${isBusy(d, code) ? "ENVIANDO..." : stateText}</span>
      </span>
      <span class="switch"><span class="knob"></span></span>
    </button>
  `;
}

function renderOnOffButtons(d, code, label) {
  return `
    <div>
      ${label ? `<span class="toggle-state" style="display:block;margin-bottom:6px">${escapeHtml(label)}</span>` : ""}
      <div class="btn-row">
        <button class="btn btn-on" type="button" data-act="on" data-id="${d.id}" data-code="${escapeHtml(code || "")}" ${blocked(d, code)}>Ligar</button>
        <button class="btn btn-off" type="button" data-act="off" data-id="${d.id}" data-code="${escapeHtml(code || "")}" ${blocked(d, code)}>Desligar</button>
      </div>
    </div>
  `;
}

function renderControls(d) {
  const parts = [];

  if (d.kind === "ac") {
    if (typeof d.on === "boolean") {
      parts.push(renderToggle(d, "power", "Ar-condicionado", d.on));
    } else {
      parts.push(renderOnOffButtons(d, null, "Energia"));
    }
  } else if (d.kind === "ir") {
    if (d.power_mode === "toggle") {
      parts.push(`
        <button class="btn btn-power" type="button" data-act="ir-power" data-id="${d.id}" ${blocked(d, "power")}>
          ${POWER_ICON}<span>Power</span>
        </button>
        <p class="hint">Controle infravermelho: a tecla é alternada (liga/desliga no mesmo toque) e o aparelho não devolve estado.</p>
      `);
    } else {
      parts.push(renderOnOffButtons(d, null, "Energia"));
      parts.push(`<p class="hint">Controle infravermelho: sem realimentação de estado.</p>`);
    }
  } else if (d.kind !== "ir_hub") {
    for (const ch of channelsFor(d)) {
      if (typeof ch.on === "boolean") parts.push(renderToggle(d, ch.code, ch.label || "Controle", ch.on));
      else parts.push(renderOnOffButtons(d, ch.code, ch.label));
    }
  }

  for (const ctl of d.controls || []) {
    if (typeof ctl.on === "boolean") parts.push(renderToggle(d, ctl.code, ctl.label || ctl.code, ctl.on));
  }

  if (!parts.length) return "";
  return `<div class="controls">${parts.join("")}</div>`;
}

function renderPill(d) {
  if (d.online === true) return `<span class="pill online"><span class="dot live"></span>ONLINE</span>`;
  if (d.online === false) return `<span class="pill offline"><span class="dot dead"></span>OFFLINE</span>`;
  return `<span class="pill">—</span>`;
}

function renderCard(d) {
  const offline = isOffline(d);
  const on = deviceIsOn(d);

  let body = "";
  if (d.kind === "sensor") body += renderSensorBody(d);
  else if (d.kind === "meter") body += renderMeterBody(d);
  else if (d.kind === "gateway") body += renderGatewayBody(d);
  else if (d.kind === "ac") body += renderAcBody(d);
  else if (d.kind === "ir_hub") body += `<p class="hint">Emissor físico dos controles virtuais de ar e TV. Todo comando infravermelho sai por aqui.</p>`;

  if (offline) body += `<p class="hint warn">Aparelho offline na Tuya — comandos desativados até voltar.</p>`;

  return `
    <article class="card kind-${d.kind} ${on && !offline ? "is-on" : ""} ${offline ? "is-offline" : ""}" data-id="${d.id}">
      <div class="card-top">
        <span class="icon-wrap">${icon(iconNameFor(d))}</span>
        <div class="titles">
          <h2 class="name">${escapeHtml(d.name)}</h2>
          <p class="sub"><span class="cat">${escapeHtml(d.category || "—")}</span> · ${escapeHtml(kindLabel(d.kind))}</p>
        </div>
        ${renderPill(d)}
      </div>
      ${body}
      ${renderControls(d)}
    </article>
  `;
}

function renderSummary() {
  const total = state.devices.length;
  const online = state.devices.filter((d) => d.online === true).length;
  const offline = state.devices.filter((d) => d.online === false).length;
  const acesos = state.devices.filter((d) => d.online !== false && deviceIsOn(d)).length;
  const ms = state.meta?.elapsed_ms;
  const cached = state.meta?.cached;
  $("#summary").innerHTML = `
    <span class="stat"><b>${total}</b> aparelhos</span>
    <span class="stat"><span class="dot live"></span><b>${online}</b> online</span>
    <span class="stat"><span class="dot dead"></span><b>${offline}</b> offline</span>
    <span class="stat"><b>${acesos}</b> ligados</span>
    ${ms != null ? `<span class="stat"><b>${cached ? "cache" : ms + " ms"}</b></span>` : ""}
  `;
}

function updateHomeLabel() {
  const el = $("#homeLabel");
  if (!el) return;
  if (state.homeName) {
    el.hidden = false;
    el.textContent = state.homeName;
  } else {
    el.hidden = true;
    el.textContent = "";
  }
}

function render() {
  const grid = $("#deviceGrid");

  if (state.loading && !state.devices.length) {
    grid.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
    return;
  }

  updateHomeLabel();
  renderSummary();
  const list = state.devices.filter((d) => state.filter === "all" || d.kind === state.filter);

  if (!list.length) {
    grid.innerHTML = `<div class="empty">Nenhum aparelho neste filtro.<br>Toque em <b>Dispositivos</b> para escolher a residência e o que aparece na tela.</div>`;
    return;
  }
  grid.innerHTML = list.map(renderCard).join("");
}

/* ---------------- dados e ações ---------------- */

async function loadDevices({ force = false } = {}) {
  state.loading = true;
  setStatus(force ? "Atualizando na Tuya..." : "Lendo aparelhos...");
  render();
  try {
    const q = force ? "?refresh=1" : "";
    const data = await api(`/home/api/devices${q}`);
    state.devices = data.devices || [];
    state.homeId = data.home_id ?? null;
    state.homeName = data.home_name || null;
    state.meta = {
      elapsed_ms: data.elapsed_ms,
      cached: data.cached,
      scanned: data.scanned,
    };
    state.loading = false;
    render();
    const tip = data.cached
      ? `Cache · ${state.homeName || "residência"}`
      : `${data.count || 0} aparelhos · ${data.elapsed_ms || "?"} ms`;
    setStatus(tip);
    setTimeout(() => setStatus(""), 2200);
  } catch (e) {
    state.loading = false;
    setStatus(String(e.message || e), true);
    render();
  }
}

async function withBusy(key, fn) {
  state.busy.add(key);
  render();
  try {
    await fn();
  } finally {
    state.busy.delete(key);
    render();
  }
}

function wait(ms) { return new Promise((r) => setTimeout(r, ms)); }

function applyFresh(local, fresh) {
  Object.assign(local, {
    on: fresh.on,
    temp: fresh.temp,
    status: fresh.status,
    readings: fresh.readings,
    controls: fresh.controls,
    channels: fresh.channels,
    online: fresh.online,
  });
}

async function confirmDeviceState(deviceId, code, expectedOn) {
  for (const ms of [1200, 1800, 2600]) {
    await wait(ms);
    try {
      const fresh = (await api(`/home/api/devices/${deviceId}`)).device;
      if (!fresh) continue;
      const local = state.devices.find((d) => d.id === deviceId);
      const actual = code === "power" || code == null
        ? fresh.on
        : [...channelsFor(fresh), ...(fresh.controls || [])].find((c) => c.code === code)?.on;
      if (actual === expectedOn) {
        if (local) applyFresh(local, fresh);
        render();
        return;
      }
    } catch (_e) { /* tenta de novo */ }
  }
  await loadDevices();
}

async function setPower(deviceId, code, on) {
  const device = state.devices.find((d) => d.id === deviceId);
  if (device && isOffline(device)) {
    setStatus("Aparelho offline — não dá para comandar agora.", true);
    return;
  }
  await withBusy(busyKey(deviceId, code), async () => {
    const isAcPower = device?.kind === "ac" && (code === "power" || code == null);
    const path = isAcPower
      ? `/home/api/devices/${deviceId}/ac/power`
      : `/home/api/devices/${deviceId}/switch`;
    const body = isAcPower ? { on } : { on, code: code && code !== "power" ? code : device?.switch_code || null };

    const res = await api(path, { method: "POST", body: JSON.stringify(body) });
    if (!res.ok) throw new Error(res.response?.msg || JSON.stringify(res.response || res));

    if (device) {
      if (isAcPower) device.on = on;
      const ch = [...channelsFor(device), ...(device.controls || [])].find((c) => c.code === code);
      if (ch) ch.on = on;
    }
    setStatus(`${device?.name || "Aparelho"}: ${on ? "ligar" : "desligar"} enviado`);
    render();
    confirmDeviceState(deviceId, code, on);
  });
}

async function sendIrPower(deviceId) {
  const device = state.devices.find((d) => d.id === deviceId);
  if (device && isOffline(device)) {
    setStatus("Hub infravermelho offline.", true);
    return;
  }
  await withBusy(busyKey(deviceId, "power"), async () => {
    const res = await api(`/home/api/devices/${deviceId}/switch`, {
      method: "POST",
      body: JSON.stringify({ on: true }),
    });
    if (!res.ok) throw new Error(res.response?.msg || JSON.stringify(res.response || res));
    setStatus(`${device?.name || "Controle"}: tecla Power enviada`);
  });
}

async function bumpTemp(deviceId, delta) {
  const device = state.devices.find((d) => d.id === deviceId);
  if (!device) return;
  if (isOffline(device)) {
    setStatus("Aparelho offline — não dá para comandar agora.", true);
    return;
  }
  const current = device.temp != null ? Number(device.temp) : 24;
  const next = Math.max(16, Math.min(30, current + delta));
  if (next === current) return;

  await withBusy(busyKey(deviceId, "temp"), async () => {
    const res = await api(`/home/api/devices/${deviceId}/ac/temp`, {
      method: "POST",
      body: JSON.stringify({ temp: next }),
    });
    if (!res.ok) throw new Error(res.response?.msg || JSON.stringify(res.response || res));
    device.temp = next;
    setStatus(`Temperatura ${next}°C enviada`);
    render();
    setTimeout(async () => {
      try {
        const fresh = (await api(`/home/api/devices/${deviceId}`)).device;
        if (fresh) { applyFresh(device, fresh); render(); }
      } catch (_e) { /* mantém o valor enviado */ }
    }, 2000);
  });
}

/* ---------------- eventos ---------------- */

function wire() {
  $all(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      $all(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.filter = btn.dataset.filter || "all";
      render();
    });
  });

  $("#btnRefresh").addEventListener("click", () => loadDevices({ force: true }));
  $("#btnDevices")?.addEventListener("click", openDevicesModal);
  $("#btnCloseDevices")?.addEventListener("click", closeDevicesModal);
  $("#btnCancelDevices")?.addEventListener("click", closeDevicesModal);
  $("#btnSaveDevices")?.addEventListener("click", saveDevicesModal);
  $("#btnEnableAll")?.addEventListener("click", () => setInventoryChecks({ homes: true, devices: true }));
  $("#btnEnableNone")?.addEventListener("click", () => setInventoryChecks({ homes: false, devices: false }));
  $("#btnEnableUseful")?.addEventListener("click", () => {
    setInventoryChecks({
      homes: true,
      devicePred: (row) => row.dataset.kind !== "other" && row.dataset.auto === "1",
    });
  });
  $("#devicesModal")?.addEventListener("click", (ev) => {
    if (ev.target === $("#devicesModal")) closeDevicesModal();
  });
  $("#inventoryList")?.addEventListener("change", (ev) => {
    const homeCb = ev.target.closest(".home-check");
    if (homeCb && ev.target.classList.contains("home-check")) {
      const section = homeCb.closest(".home-section");
      const on = homeCb.checked;
      section?.querySelectorAll(".inv-row input[type=checkbox]").forEach((cb) => {
        cb.checked = on && (cb.closest(".inv-row")?.dataset.kind !== "other" || on);
        if (on) {
          // ao ligar residência, marca só úteis por padrão
          const row = cb.closest(".inv-row");
          cb.checked = row?.dataset.kind !== "other" && row?.dataset.auto === "1";
        } else {
          cb.checked = false;
        }
      });
      section?.classList.toggle("is-off", !on);
    }
  });

  $("#deviceGrid").addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-act]");
    if (!btn || btn.disabled) return;
    const id = btn.dataset.id;
    const code = btn.dataset.code || null;
    try {
      switch (btn.dataset.act) {
        case "toggle": await setPower(id, code, btn.dataset.next === "1"); break;
        case "on": await setPower(id, code, true); break;
        case "off": await setPower(id, code, false); break;
        case "ir-power": await sendIrPower(id); break;
        case "temp-up": await bumpTemp(id, 1); break;
        case "temp-down": await bumpTemp(id, -1); break;
      }
    } catch (e) {
      setStatus(String(e.message || e), true);
      render();
    }
  });
}

/* ---------------- modal Dispositivos ---------------- */

let _modalScrollY = 0;

function lockPageScroll() {
  _modalScrollY = window.scrollY || window.pageYOffset || 0;
  document.documentElement.classList.add("modal-open");
  document.body.style.top = `-${_modalScrollY}px`;
}

function unlockPageScroll() {
  document.documentElement.classList.remove("modal-open");
  document.body.style.top = "";
  window.scrollTo(0, _modalScrollY);
}

function closeDevicesModal() {
  const modal = $("#devicesModal");
  if (modal) modal.hidden = true;
  unlockPageScroll();
}

async function openDevicesModal() {
  const modal = $("#devicesModal");
  if (!modal) return;
  lockPageScroll();
  modal.hidden = false;
  setStatus("Carregando residências...");
  try {
    await loadInventoryAll();
    setStatus("");
    // Foca a lista rolável para o scroll do dedo cair nela, não no fundo
    $("#inventoryList")?.focus?.({ preventScroll: true });
  } catch (e) {
    setStatus(String(e.message || e), true);
  }
}

async function loadInventoryAll() {
  const box = $("#inventoryList");
  box.innerHTML = `<p class="hint">Carregando inventário de todas as residências...</p>`;
  const data = await api("/home/api/devices/inventory");
  const homes = data.homes || [];
  if (!homes.length) {
    box.innerHTML = `<p class="hint warn">Nenhuma residência encontrada na conta Tuya.</p>`;
    return;
  }
  box.innerHTML = homes.map((home) => {
    const devices = home.devices || [];
    const rows = devices.map((d) => `
      <label class="inv-row" data-kind="${escapeHtml(d.kind)}" data-auto="${d.auto_show ? "1" : "0"}" data-home="${home.id}">
        <input type="checkbox" class="device-check" value="${escapeHtml(d.id)}" ${d.enabled ? "checked" : ""} ${home.selected ? "" : ""} />
        <span class="inv-main">
          <b>${escapeHtml(d.name)}</b>
          <small>${escapeHtml(d.kind)} · ${d.online === true ? "online" : d.online === false ? "offline" : "?"}</small>
        </span>
      </label>
    `).join("");
    return `
      <section class="home-section ${home.selected ? "" : "is-off"}" data-home-id="${home.id}">
        <label class="home-head">
          <input type="checkbox" class="home-check" value="${home.id}" ${home.selected ? "checked" : ""} />
          <span>
            <b>${escapeHtml(home.name)}</b>
            <small>${devices.length} aparelhos na Tuya</small>
          </span>
        </label>
        <div class="home-devices">${rows || `<p class="hint">Sem aparelhos.</p>`}</div>
      </section>
    `;
  }).join("");
}

function setInventoryChecks({ homes, devices, devicePred } = {}) {
  if (typeof homes === "boolean") {
    $all("#inventoryList .home-check").forEach((cb) => {
      cb.checked = homes;
      cb.closest(".home-section")?.classList.toggle("is-off", !homes);
    });
  }
  $all("#inventoryList .inv-row").forEach((row) => {
    const cb = row.querySelector("input.device-check");
    if (!cb) return;
    if (typeof devicePred === "function") {
      const homeOn = row.closest(".home-section")?.querySelector(".home-check")?.checked;
      cb.checked = !!homeOn && !!devicePred(row);
    } else if (typeof devices === "boolean") {
      const homeOn = row.closest(".home-section")?.querySelector(".home-check")?.checked;
      cb.checked = devices && !!homeOn;
    }
  });
}

async function saveDevicesModal() {
  const homeIds = $all("#inventoryList .home-check:checked").map((el) => Number(el.value));
  const ids = [];
  $all("#inventoryList .home-section").forEach((section) => {
    const homeOn = section.querySelector(".home-check")?.checked;
    if (!homeOn) return;
    section.querySelectorAll("input.device-check:checked").forEach((el) => ids.push(el.value));
  });
  if (!homeIds.length) {
    setStatus("Marque ao menos uma residência para a tela principal.", true);
    return;
  }
  setStatus("Salvando preferências...");
  try {
    await api("/home/api/prefs", {
      method: "PUT",
      body: JSON.stringify({
        selected_home_ids: homeIds,
        enabled_device_ids: ids,
        skip_offline_status: true,
      }),
    });
    closeDevicesModal();
    await loadDevices({ force: true });
  } catch (e) {
    setStatus(String(e.message || e), true);
  }
}

wire();
loadDevices();
