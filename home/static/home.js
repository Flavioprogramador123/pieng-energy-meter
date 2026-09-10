const state = {
  filter: "all",
  devices: [],
  busy: new Set(),
};

function $(sel) { return document.querySelector(sel); }
function $all(sel) { return [...document.querySelectorAll(sel)]; }

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
  if (!r.ok) {
    throw new Error(data.detail || data.message || `HTTP ${r.status}`);
  }
  return data;
}

function kindLabel(kind) {
  return ({
    light: "Luz",
    ac: "Ar",
    switch: "Tomada/Relé",
    meter: "Medidor",
    sensor: "Sensor",
    gateway: "Gateway",
    ir_hub: "Hub IR",
    ir: "IR",
    other: "Outro",
  })[kind] || kind;
}

function channelsFor(device) {
  if (Array.isArray(device.channels) && device.channels.length) {
    return device.channels;
  }
  if (["sensor", "gateway", "ir_hub", "meter"].includes(device.kind)) {
    return [];
  }
  return [{
    code: device.switch_code || null,
    label: device.kind === "light" ? "Luz" : "Controle",
    on: device.on,
  }];
}

function busyKey(deviceId, code) {
  return `${deviceId}:${code || "power"}`;
}

function readingValue(device, key, fallback = "--") {
  const item = device.readings?.[key];
  if (!item || item.value == null || item.value === "") return fallback;
  return `${item.value}${item.unit || ""}`;
}

function renderSensorBody(d) {
  return `
    <div class="metrics">
      <div class="metric">
        <span class="metric-label">Temperatura</span>
        <strong>${escapeHtml(readingValue(d, "temperature"))}</strong>
      </div>
      <div class="metric">
        <span class="metric-label">Umidade</span>
        <strong>${escapeHtml(readingValue(d, "humidity"))}</strong>
      </div>
      <div class="metric">
        <span class="metric-label">Bateria</span>
        <strong>${escapeHtml(readingValue(d, "battery"))}</strong>
      </div>
    </div>
    <p class="hint">Limites: temp ${escapeHtml(String(d.status?.minitemp_set ?? "--"))}–${escapeHtml(String(d.status?.maxtemp_set ?? "--"))}°C · umid ${escapeHtml(String(d.status?.minihum_set ?? "--"))}–${escapeHtml(String(d.status?.maxhum_set ?? "--"))}%</p>
  `;
}

function renderMeterBody(d) {
  if (d.card === "triphase_meter") {
    return `
      <div class="metrics meter-grid">
        <div class="metric">
          <span class="metric-label">Total</span>
          <strong>${escapeHtml(readingValue(d, "total_power"))}</strong>
          <small>${escapeHtml(readingValue(d, "frequency"))}</small>
        </div>
        <div class="metric">
          <span class="metric-label">Rede</span>
          <strong>${escapeHtml(readingValue(d, "energy_import_total"))}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Solar</span>
          <strong>${escapeHtml(readingValue(d, "energy_export_total"))}</strong>
        </div>
        <div class="metric phase-l1">
          <span class="metric-label">L1</span>
          <strong>${escapeHtml(readingValue(d, "voltage_a"))}</strong>
          <small>${escapeHtml(readingValue(d, "power_a"))} · ${escapeHtml(readingValue(d, "current_a"))}</small>
        </div>
        <div class="metric phase-l2">
          <span class="metric-label">L2</span>
          <strong>${escapeHtml(readingValue(d, "voltage_b"))}</strong>
          <small>${escapeHtml(readingValue(d, "power_b"))} · ${escapeHtml(readingValue(d, "current_b"))}</small>
        </div>
        <div class="metric phase-l3">
          <span class="metric-label">L3</span>
          <strong>${escapeHtml(readingValue(d, "voltage_c"))}</strong>
          <small>${escapeHtml(readingValue(d, "power_c"))} · ${escapeHtml(readingValue(d, "current_c"))}</small>
        </div>
      </div>
      <p class="hint">PC473 trifásico · shadow/properties · relé = switch_1</p>
    `;
  }
  return `
    <div class="metrics meter-grid">
      <div class="metric">
        <span class="metric-label">Tensão</span>
        <strong>${escapeHtml(readingValue(d, "voltage"))}</strong>
      </div>
      <div class="metric">
        <span class="metric-label">Freq.</span>
        <strong>${escapeHtml(readingValue(d, "frequency"))}</strong>
      </div>
      <div class="metric">
        <span class="metric-label">Total</span>
        <strong>${escapeHtml(readingValue(d, "total_power"))}</strong>
      </div>
      <div class="metric">
        <span class="metric-label">Canal A</span>
        <strong>${escapeHtml(readingValue(d, "power_a"))}</strong>
        <small>${escapeHtml(readingValue(d, "current_a"))} · ${escapeHtml(String(d.readings?.direction_a?.value || d.status?.direction_a || "—"))}</small>
      </div>
      <div class="metric">
        <span class="metric-label">Canal B</span>
        <strong>${escapeHtml(readingValue(d, "power_b"))}</strong>
        <small>${escapeHtml(readingValue(d, "current_b"))} · ${escapeHtml(String(d.readings?.direction_b?.value || d.status?.direction_b || "—"))}</small>
      </div>
      <div class="metric">
        <span class="metric-label">Energia fwd</span>
        <strong>${escapeHtml(readingValue(d, "energy_import_total"))}</strong>
        <small>rev ${escapeHtml(readingValue(d, "energy_export_total"))}</small>
      </div>
    </div>
    <p class="hint">Medidor dual solar · leitura via shadow/properties · calibragem/reset bloqueados</p>
  `;
}

function renderGatewayBody(d) {
  const stateValue = d.readings?.master_state?.value || d.status?.master_state || "—";
  const alarm = d.readings?.alarm_active?.value || d.status?.alarm_active || "";
  return `
    <div class="metrics">
      <div class="metric">
        <span class="metric-label">Estado</span>
        <strong class="${stateValue === "alarm" ? "danger-text" : ""}">${escapeHtml(String(stateValue))}</strong>
      </div>
      <div class="metric wide">
        <span class="metric-label">Alarme ativo</span>
        <strong>${escapeHtml(alarm || "nenhum")}</strong>
      </div>
    </div>
    <p class="hint">Reset de fábrica bloqueado por segurança.</p>
  `;
}

function renderSafeControls(d) {
  const controls = Array.isArray(d.controls) ? d.controls : [];
  if (!controls.length) return "";
  return `
    <div class="channels">
      ${controls.map((control) => {
        const code = control.code || "";
        const key = busyKey(d.id, code);
        const known = typeof control.on === "boolean";
        return `
          <div class="channel">
            <div class="channel-head">
              <span>${escapeHtml(control.label || code)}</span>
              ${known ? `<span class="channel-state ${control.on ? "on" : "off"}">${control.on ? "LIGADO" : "DESLIGADO"}</span>` : ""}
            </div>
            <div class="actions">
              <button class="btn btn-on" type="button" data-act="on" data-id="${d.id}" data-code="${escapeHtml(code)}" ${disabledAttr(d, key)}>Ligar</button>
              <button class="btn btn-off" type="button" data-act="off" data-id="${d.id}" data-code="${escapeHtml(code)}" ${disabledAttr(d, key)}>Desligar</button>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderPowerControls(d) {
  const channels = channelsFor(d);
  if (!channels.length) return "";
  return `
    <div class="channels">
      ${channels.map((channel) => {
        const code = channel.code || "";
        const key = busyKey(d.id, code);
        const known = typeof channel.on === "boolean";
        const channelBadge = known
          ? `<span class="channel-state ${channel.on ? "on" : "off"}">${channel.on ? "LIGADA" : "DESLIGADA"}</span>`
          : "";
        return `
          <div class="channel">
            ${channels.length > 1 ? `
              <div class="channel-head">
                <span>${escapeHtml(channel.label || code || "Controle")}</span>
                ${channelBadge}
              </div>
            ` : ""}
            <div class="actions">
              <button class="btn btn-on" type="button" data-act="on" data-id="${d.id}" data-code="${escapeHtml(code)}" ${disabledAttr(d, key)}>Ligar</button>
              <button class="btn btn-off" type="button" data-act="off" data-id="${d.id}" data-code="${escapeHtml(code)}" ${disabledAttr(d, key)}>Desligar</button>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function isOnline(device) {
  return device?.online !== false;
}

function disabledAttr(device, key) {
  if (!isOnline(device) || state.busy.has(key)) return "disabled";
  return "";
}

function onlineBadge(d) {
  if (d.online === false) return `<span class="badge offline">OFFLINE</span>`;
  if (d.online === true) return `<span class="badge online">ONLINE</span>`;
  return `<span class="badge">—</span>`;
}

function renderBadge(d) {
  const link = onlineBadge(d);
  let stateBadge = "";
  if (d.kind === "sensor") {
    const temp = readingValue(d, "temperature", null);
    stateBadge = `<span class="badge on">${temp ? escapeHtml(temp) : "SENSOR"}</span>`;
  } else if (d.kind === "meter") {
    const total = readingValue(d, "total_power", null);
    stateBadge = `<span class="badge on">${total ? escapeHtml(total) : "MEDIDOR"}</span>`;
  } else if (d.kind === "gateway") {
    const st = d.readings?.master_state?.value || d.status?.master_state || "gateway";
    stateBadge = `<span class="badge ${st === "alarm" ? "off" : "on"}">${escapeHtml(String(st))}</span>`;
  } else if (d.kind === "ir_hub") {
    stateBadge = `<span class="badge">HUB IR</span>`;
  } else if (d.kind === "ac") {
    stateBadge = `<span class="badge">${d.temp != null ? `${d.temp}°C` : "AR"}</span>`;
  } else {
    const channels = channelsFor(d);
    const knownChannels = channels.filter((channel) => typeof channel.on === "boolean");
    const onCount = knownChannels.filter((channel) => channel.on).length;
    if (knownChannels.length === 1) {
      const on = knownChannels[0].on;
      stateBadge = `<span class="badge ${on ? "on" : "off"}">${on ? "LIGADO" : "DESLIGADO"}</span>`;
    } else if (knownChannels.length > 1) {
      stateBadge = `<span class="badge ${onCount ? "on" : "off"}">${onCount}/${knownChannels.length} LIGADOS</span>`;
    } else {
      stateBadge = `<span class="badge">${kindLabel(d.kind)}</span>`;
    }
  }
  return `<div class="badges">${link}${stateBadge}</div>`;
}

function render() {
  const grid = $("#deviceGrid");
  const list = state.devices.filter((d) => state.filter === "all" || d.kind === state.filter);

  if (!list.length) {
    grid.innerHTML = `<div class="empty">Nenhum dispositivo neste filtro.<br>Toque em Atualizar ou verifique o vínculo Tuya.</div>`;
    return;
  }

  grid.innerHTML = list.map((d) => {
    const offline = d.online === false;
    const tempBlock = d.kind === "ac" ? `
      <div class="temp-row">
        <button type="button" data-act="temp-down" data-id="${d.id}" aria-label="Diminuir temperatura" ${disabledAttr(d, `${d.id}:temp`)}>−</button>
        <div class="temp-value">${d.temp != null ? d.temp + "°C" : "--°C"}</div>
        <button type="button" data-act="temp-up" data-id="${d.id}" aria-label="Aumentar temperatura" ${disabledAttr(d, `${d.id}:temp`)}>+</button>
      </div>
    ` : "";

    let body = "";
    if (d.kind === "sensor") body += renderSensorBody(d);
    if (d.kind === "meter") body += renderMeterBody(d);
    if (d.kind === "gateway") body += renderGatewayBody(d);
    if (d.kind === "ir_hub") {
      body += `<p class="hint">Emissor físico de controles virtuais (ar/TV). Comandos saem por este hub.</p>`;
    }
    if (offline) body += `<p class="hint warn">Offline — comandos desabilitados até voltar online.</p>`;
    if (["sensor", "gateway", "meter"].includes(d.kind)) body += renderSafeControls(d);
    else if (d.kind !== "ir_hub") body += tempBlock + renderPowerControls(d);

    return `
      <article class="card ${d.kind}${offline ? " is-offline" : " is-online"}" data-id="${d.id}">
        <div class="card-head">
          <div>
            <h2 class="name">${escapeHtml(d.name)}</h2>
            <p class="meta"><span class="cat">${escapeHtml(d.category || "—")}</span> · ${escapeHtml(d.product || d.category_label || "tuya")}</p>
            <p class="meta soft">${kindLabel(d.kind)}</p>
          </div>
          ${renderBadge(d)}
        </div>
        ${body}
      </article>
    `;
  }).join("");
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function loadDevices() {
  setStatus("Carregando dispositivos Tuya...");
  try {
    const data = await api("/home/api/devices");
    state.devices = data.devices || [];
    const online = state.devices.filter((d) => d.online === true).length;
    const offline = state.devices.filter((d) => d.online === false).length;
    setStatus(`${state.devices.length} devices · ${online} online · ${offline} offline`);
    render();
  } catch (e) {
    setStatus(String(e.message || e), true);
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

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function confirmDeviceState(deviceId, code, expectedOn) {
  const delays = [1200, 1800, 2500];
  for (const ms of delays) {
    await wait(ms);
    try {
      const data = await api(`/home/api/devices/${deviceId}`);
      const fresh = data.device;
      if (!fresh) continue;
      const local = state.devices.find((d) => d.id === deviceId);
      const freshChannel = [
        ...channelsFor(fresh),
        ...(fresh.controls || []),
      ].find((channel) => channel.code === code);
      if (freshChannel?.on === expectedOn) {
        if (local) {
          Object.assign(local, {
            on: fresh.on,
            temp: fresh.temp,
            status: fresh.status,
            readings: fresh.readings,
            controls: fresh.controls,
            channels: fresh.channels,
          });
        }
        render();
        return;
      }
    } catch (_e) {
      // tenta de novo
    }
  }
  await loadDevices();
}

async function setPower(deviceId, code, on) {
  const device = state.devices.find((d) => d.id === deviceId);
  if (device && device.online === false) {
    setStatus("Dispositivo offline — não é possível comandar agora", true);
    return;
  }
  await withBusy(busyKey(deviceId, code), async () => {
    const path = device?.kind === "ac"
      ? `/home/api/devices/${deviceId}/ac/power`
      : `/home/api/devices/${deviceId}/switch`;
    const body = device?.kind === "ac"
      ? { on }
      : { on, code: code || device?.switch_code || null };
    const res = await api(path, { method: "POST", body: JSON.stringify(body) });
    if (!res.ok) {
      throw new Error(JSON.stringify(res.response || res));
    }
    if (device) {
      const channel = [...channelsFor(device), ...(device.controls || [])].find((item) => item.code === code);
      if (channel) channel.on = on;
      device.on = channelsFor(device)[0]?.on ?? on;
    }
    setStatus(on ? "Comando LIGAR enviado" : "Comando DESLIGAR enviado");
    render();
    confirmDeviceState(deviceId, code, on);
  });
}

async function bumpTemp(deviceId, delta) {
  const device = state.devices.find((d) => d.id === deviceId);
  if (!device) return;
  if (device.online === false) {
    setStatus("Dispositivo offline — não é possível comandar agora", true);
    return;
  }
  const current = device.temp != null ? Number(device.temp) : 24;
  const next = Math.max(16, Math.min(30, current + delta));
  await withBusy(`${deviceId}:temp`, async () => {
    setStatus(`Ajustando temperatura para ${next}°C...`);
    const res = await api(`/home/api/devices/${deviceId}/ac/temp`, {
      method: "POST",
      body: JSON.stringify({ temp: next }),
    });
    if (!res.ok) {
      throw new Error(JSON.stringify(res.response || res));
    }
    device.temp = next;
    setStatus(`Temperatura ${next}°C enviada`);
    render();
    setTimeout(loadDevices, 1200);
  });
}

function wire() {
  $all(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      $all(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.filter = btn.dataset.filter || "all";
      render();
    });
  });

  $("#btnRefresh").addEventListener("click", loadDevices);

  $("#deviceGrid").addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-act]");
    if (!btn) return;
    const id = btn.dataset.id;
    const code = btn.dataset.code || null;
    const act = btn.dataset.act;
    try {
      if (act === "on") await setPower(id, code, true);
      if (act === "off") await setPower(id, code, false);
      if (act === "temp-up") await bumpTemp(id, 1);
      if (act === "temp-down") await bumpTemp(id, -1);
    } catch (e) {
      setStatus(String(e.message || e), true);
      render();
    }
  });
}

wire();
loadDevices();
