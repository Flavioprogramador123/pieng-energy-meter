async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

function el(id) { return document.getElementById(id); }

/** Potência no banco fica em W; na UI exibimos kW (mais usual). */
function wattsToKw(w) {
  if (w == null || Number.isNaN(Number(w))) return null;
  return Number(w) / 1000;
}
function fmtKw(w, digits = 2) {
  const k = wattsToKw(w);
  if (k == null) return '—';
  return `${k.toFixed(digits)} kW`;
}
function seriesValuesKw(arr) {
  return (arr || []).map((x) => wattsToKw(x.value));
}

function setLiveStatus(mode) {
  const box = el('liveStatus');
  const text = el('liveStatusText');
  if (!box || !text) return;
  box.classList.remove('is-updating', 'is-paused', 'is-error');
  if (mode === 'updating') {
    box.classList.add('is-updating');
    text.textContent = 'Atualizando gráficos…';
    return;
  }
  if (mode === 'paused') {
    box.classList.add('is-paused');
    text.textContent = 'Histórico fixo · auto-atualização pausada';
    return;
  }
  if (mode === 'error') {
    box.classList.add('is-error');
    text.textContent = 'Falha ao atualizar · tentando de novo em breve';
    return;
  }
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const ss = String(now.getSeconds()).padStart(2, '0');
  text.textContent = `Ao vivo · ${hh}:${mm}:${ss} · a cada ${AUTO_REFRESH_MS / 1000}s`;
}

let charts = {};
let currentPeriod = '1d';
const AUTO_REFRESH_MS = 30000;
let loadInFlight = false;

// Zoom de tempo compartilhado por todos os cards (gráficos e valores ao vivo).
// null = período completo carregado; senão {from, to} em epoch ms, absoluto
// (não normalizado), pra não derivar quando os dados são atualizados a cada 30s.
let timeWindow = null;
let fullRange = { min: null, max: null };
let rawCache = null; // último resultado bruto do fetch, pra reprocessar sem rede ao mexer no zoom

function filterWindow(arr) {
  if (!timeWindow || !arr) return arr;
  return arr.filter((d) => {
    const t = new Date(d.timestamp).getTime();
    return t >= timeWindow.from && t <= timeWindow.to;
  });
}

function computeFullRange(arrays) {
  let min = null, max = null;
  arrays.forEach((arr) => {
    (arr || []).forEach((d) => {
      const t = new Date(d.timestamp).getTime();
      if (min === null || t < min) min = t;
      if (max === null || t > max) max = t;
    });
  });
  return { min, max };
}

function fmtZoomTime(ms) {
  if (ms == null) return '--';
  return new Date(ms).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function updateZoomLabel() {
  const label = el('zoomRangeLabel');
  if (!label) return;
  if (fullRange.min == null) {
    label.textContent = '--';
  } else if (!timeWindow) {
    label.textContent = `${fmtZoomTime(fullRange.min)} — ${fmtZoomTime(fullRange.max)} (completo)`;
  } else {
    label.textContent = `${fmtZoomTime(timeWindow.from)} — ${fmtZoomTime(timeWindow.to)}`;
  }
}

function applyZoomFromSliders() {
  if (fullRange.min == null || fullRange.max == null || fullRange.max <= fullRange.min) return;
  const fromInput = el('zoomFrom');
  const toInput = el('zoomTo');
  let a = Number(fromInput.value);
  let b = Number(toInput.value);
  if (a > b) { const t = a; a = b; b = t; }
  const span = fullRange.max - fullRange.min;
  timeWindow = (a <= 0 && b >= 1000)
    ? null
    : { from: fullRange.min + (a / 1000) * span, to: fullRange.min + (b / 1000) * span };
  updateZoomLabel();
  if (rawCache) renderFromCache();
}

function resetZoom() {
  timeWindow = null;
  const fromInput = el('zoomFrom');
  const toInput = el('zoomTo');
  if (fromInput) fromInput.value = 0;
  if (toInput) toInput.value = 1000;
  updateZoomLabel();
  if (rawCache) renderFromCache();
}

// Âncora de navegação no histórico (dia/semana/mês anterior). null = "agora"
// (comportamento de sempre — janela terminando no momento atual). Setado,
// vira uma data ISO fixa que vira o "fim" da janela buscada no servidor.
let anchorEnd = null;

function periodDeltaMs() {
  return currentPeriod === '1m' ? 30 * 86400000 : (currentPeriod === '1w' ? 7 * 86400000 : 86400000);
}

function resetPeriodNav() {
  anchorEnd = null;
  resetZoom();
}

function navigatePeriod(direction) {
  const delta = periodDeltaMs();
  const base = anchorEnd != null ? anchorEnd : Date.now();
  const next = base + direction * delta;
  anchorEnd = next >= Date.now() ? null : next;
  resetZoom();
  updatePeriodRangeLabel();
  if (anchorEnd != null) setLiveStatus('paused');
  loadData();
}

function updatePeriodRangeLabel() {
  const label = el('periodRangeLabel');
  const nextBtn = el('periodNextBtn');
  const todayBtn = el('periodTodayBtn');
  if (!label) return;
  const isPast = anchorEnd != null;
  if (nextBtn) nextBtn.disabled = !isPast;
  if (todayBtn) todayBtn.disabled = !isPast;
  label.classList.toggle('is-past', isPast);
  if (!isPast) {
    label.textContent = 'Agora';
    return;
  }
  const end = new Date(anchorEnd);
  const start = new Date(anchorEnd - periodDeltaMs());
  const fmt = (d) => d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
  label.textContent = currentPeriod === '1d' ? fmt(end) : `${fmt(start)} – ${fmt(end)}`;
}

function toNaiveLocalISOString(ms) {
  // O backend grava timestamps com datetime.now() (hora local, sem timezone).
  // toISOString() do JS é sempre UTC — usar componentes locais aqui pra bater
  // com o que está gravado no banco (mesma máquina/fuso do app local).
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function metricsUrl(deviceId, metric, limit = 100) {
  const end = anchorEnd != null ? `&end=${encodeURIComponent(toNaiveLocalISOString(anchorEnd))}` : '';
  return `/api/metrics?device_id=${deviceId}&metric=${metric}&limit=${limit}&period=${currentPeriod}${end}`;
}

function resetCharts() {
  Object.keys(charts).forEach((k) => {
    if (k === '_wiring') return;
    try { if (charts[k] && typeof charts[k].destroy === 'function') charts[k].destroy(); } catch (_e) { /* ignore */ }
    charts[k] = null;
  });
  charts._wiring = null;
}

function ensureWiringMode(mode) {
  if (charts._wiring && charts._wiring !== mode) {
    resetCharts();
  }
  charts._wiring = mode;
}

function createChart(canvasId, label, color, yRange = {}) {
  const C = getChartColors();
  return new Chart(el(canvasId), {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: label,
        data: [],
        borderColor: color,
        backgroundColor: hexToRgba(color, 0.14),
        tension: 0.35,
        fill: true,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHitRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 280 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: tooltipConfig()
      },
      scales: {
        x: {
          ticks: { color: C.textMuted, maxTicksLimit: 7, maxRotation: 0, autoSkip: true, font: { size: 10 } },
          grid: { color: C.grid, drawBorder: false }
        },
        y: {
          beginAtZero: false,
          min: yRange.min,
          max: yRange.max,
          ticks: { color: C.textMuted, maxTicksLimit: 6, font: { size: 10 } },
          grid: { color: C.gridStrong, drawBorder: false }
        }
      }
    }
  });
}

function lineDataset(label, data, color, extras = {}) {
  return {
    label,
    data,
    borderColor: color,
    backgroundColor: hexToRgba(color, extras.fillAlpha ?? 0.12),
    tension: extras.tension ?? 0.35,
    fill: extras.fill ?? false,
    borderWidth: extras.borderWidth ?? 2,
    pointRadius: extras.pointRadius ?? 0,
    pointHoverRadius: 4,
    pointHitRadius: 8,
    ...extras.more
  };
}

function chartScaleOpts(C, beginAtZero = false, yRange = {}) {
  return {
    x: {
      ticks: { color: C.textMuted, maxTicksLimit: 8, maxRotation: 0, autoSkip: true, font: { size: 10 } },
      grid: { color: C.grid, drawBorder: false }
    },
    y: {
      beginAtZero,
      min: yRange.min,
      max: yRange.max,
      ticks: { color: C.textMuted, maxTicksLimit: 6, font: { size: 10 } },
      grid: { color: C.gridStrong, drawBorder: false }
    }
  };
}

function buildPhaseChart(key, canvasId, s1, s2, s3, beginAtZero, asKw = false) {
  const canvas = el(canvasId);
  if (!canvas) return;
  const C = getChartColors();
  const s1r = (s1 || []).slice().reverse();
  const s2r = (s2 || []).slice().reverse();
  const s3r = (s3 || []).slice().reverse();
  const labels = s1r.map(x => new Date(x.timestamp).toLocaleTimeString());
  const scale = (v) => (asKw ? wattsToKw(v) : Number(v));

  if (!charts[key] || !charts[key].data.datasets[1]) {
    if (charts[key]) charts[key].destroy();
    charts[key] = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          lineDataset('L1', s1r.map(x => scale(x.value)), C.phaseL1),
          lineDataset('L2', s2r.map(x => scale(x.value)), C.phaseL2),
          lineDataset('L3', s3r.map(x => scale(x.value)), C.phaseL3)
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 280 },
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: C.text, boxWidth: 12, font: { size: 11 } } }, tooltip: tooltipConfig() },
        scales: chartScaleOpts(C, beginAtZero)
      }
    });
  } else {
    charts[key].data.labels = labels;
    charts[key].data.datasets[0].data = s1r.map(x => scale(x.value));
    charts[key].data.datasets[1].data = s2r.map(x => scale(x.value));
    charts[key].data.datasets[2].data = s3r.map(x => scale(x.value));
    charts[key].update('none');
  }
}

function tooltipConfig() {
  return {
    mode: 'index',
    intersect: false,
    callbacks: {
      label: (ctx) => {
        const v = ctx.parsed.y;
        return `${ctx.dataset.label}: ${v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 3 })}`;
      }
    }
  };
}

function destroyAllCharts() {
  Object.keys(charts).forEach((key) => {
    if (charts[key]) charts[key].destroy();
  });
  charts = {};
}

function updateChart(chart, labels, data) {
  chart.data.labels = labels;
  chart.data.datasets[0].data = data;
  chart.update('none');
}

function setIntegrityBanner(html, show) {
  const banner = el('dataIntegrityBanner');
  if (!banner) return;
  banner.style.display = show ? 'block' : 'none';
  banner.innerHTML = html || '';
}

async function loadData() {
  const deviceId = el('deviceSelect').value;
  if (!deviceId) return;
  if (loadInFlight) return;
  loadInFlight = true;
  setLiveStatus('updating');

  try {
    // Trifásico de verdade: precisa de ao menos L1 e L2.
    // Só voltage_l1 NÃO basta (medidor monofásico / dual não usa L2/L3).
    const [voltage_l1_check, voltage_l2_check, voltage_check] = await Promise.all([
      fetchJSON(`/api/metrics?device_id=${deviceId}&metric=voltage_l1&limit=1`),
      fetchJSON(`/api/metrics?device_id=${deviceId}&metric=voltage_l2&limit=1`),
      fetchJSON(`/api/metrics?device_id=${deviceId}&metric=voltage&limit=1`)
    ]);
    const isThreePhase = voltage_l1_check.length > 0 && voltage_l2_check.length > 0;
    const wiringMode = isThreePhase ? 'three' : 'single';

    let voltageData, currentData, powerData;

    let energyData, alarms, switchData;
    let solarData = null;
    const chartLimit = currentPeriod === '1m' ? 5000 : (currentPeriod === '1w' ? 2500 : 500);

    if (isThreePhase) {
      // Buscar métricas trifásicas
      const [[v1, v2, v3, i1, i2, i3, p1, p2, p3, pTotal, eData, alarmsData, swData,
              pExport, pImport, iExport, iImport, eExported, eImported],
             [pImpL1, pImpL2, pImpL3, pExpL1, pExpL2, pExpL3,
              iImpL1, iImpL2, iImpL3, iExpL1, iExpL2, iExpL3]] = await Promise.all([
        Promise.all([
          fetchJSON(metricsUrl(deviceId, 'voltage_l1', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'voltage_l2', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'voltage_l3', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_l1', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_l2', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_l3', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_l1', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_l2', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_l3', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_total', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'energy_wh', chartLimit)),
          fetchJSON(`/api/alarms/events?device_id=${deviceId}&limit=20`),
          fetchJSON(metricsUrl(deviceId, 'switch_status', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_export_total', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_import_total', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_export_total', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_import_total', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'energy_exported_total', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'energy_imported_total', chartLimit))
        ]),
        Promise.all([
          fetchJSON(metricsUrl(deviceId, 'power_import_l1', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_import_l2', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_import_l3', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_export_l1', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_export_l2', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'power_export_l3', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_import_l1', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_import_l2', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_import_l3', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_export_l1', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_export_l2', chartLimit)),
          fetchJSON(metricsUrl(deviceId, 'current_export_l3', chartLimit))
        ])
      ]);

      // Armazenar dados por fase para uso posterior
      window.phaseData = {
        v1, v2, v3, i1, i2, i3, p1, p2, p3, pTotal,
        pImpL1, pImpL2, pImpL3, pExpL1, pExpL2, pExpL3,
        iImpL1, iImpL2, iImpL3, iExpL1, iExpL2, iExpL3
      };
      voltageData = v1; // usar L1 como referência para status
      currentData = i1;
      powerData = pTotal.length > 0 ? pTotal : p1;
      energyData = eData;
      alarms = alarmsData;
      switchData = swData;
      solarData = { pExport, pImport, iExport, iImport, eExported, eImported };

    } else {
      // Monofásico / dual meter: tensão de linha + potências/energias padrão
      // (e totais Rede×Solar quando o poller grava import/export).
      const [vData, iData, pData, eData, alarmsData, swData,
             pExport, pImport, iExport, iImport, eExported, eImported] = await Promise.all([
        voltage_check.length
          ? fetchJSON(metricsUrl(deviceId, 'voltage', chartLimit))
          : fetchJSON(metricsUrl(deviceId, 'voltage_l1', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'current', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'power', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'energy_wh', chartLimit)),
        fetchJSON(`/api/alarms/events?device_id=${deviceId}&limit=20`),
        fetchJSON(metricsUrl(deviceId, 'switch_status', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'power_export_total', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'power_import_total', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'current_export_total', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'current_import_total', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'energy_exported_total', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'energy_imported_total', chartLimit))
      ]);
      voltageData = vData;
      currentData = iData;
      powerData = pData;
      energyData = eData;
      alarms = alarmsData;
      switchData = swData;
      window.phaseData = null;
      if (pExport.length || pImport.length) {
        solarData = { pExport, pImport, iExport, iImport, eExported, eImported };
      }
    }

    fullRange = computeFullRange([voltageData, powerData, energyData]);
    updateZoomLabel();

    rawCache = {
      deviceId, isThreePhase, wiringMode,
      voltageData, currentData, powerData, energyData, alarms, switchData,
      phaseData: isThreePhase ? window.phaseData : null,
      solarData
    };

    renderFromCache();
    setLiveStatus('live');
  } catch (error) {
    console.error('Erro ao carregar dados:', error);
    setLiveStatus('error');
  } finally {
    loadInFlight = false;
  }
}

function renderFromCache() {
  if (!rawCache) return;
  const C = getChartColors();
  const { deviceId, isThreePhase, alarms } = rawCache;
  const wiringMode = rawCache.wiringMode || (isThreePhase ? 'three' : 'single');
  ensureWiringMode(wiringMode);

  try {
    const voltageData = filterWindow(rawCache.voltageData);
    const currentData = filterWindow(rawCache.currentData);
    const powerData = filterWindow(rawCache.powerData);
    const energyData = filterWindow(rawCache.energyData);
    const switchData = filterWindow(rawCache.switchData);

    if (isThreePhase && rawCache.phaseData) {
      window.phaseData = {};
      Object.keys(rawCache.phaseData).forEach((k) => {
        window.phaseData[k] = filterWindow(rawCache.phaseData[k]);
      });
    } else {
      window.phaseData = null;
    }

    const cardSolar = el('cardSolar');
    if (rawCache.solarData && cardSolar) {
      const sd = rawCache.solarData;
      const pExport = filterWindow(sd.pExport);
      const pImport = filterWindow(sd.pImport);
      const iExport = filterWindow(sd.iExport);
      const iImport = filterWindow(sd.iImport);
      const eExported = filterWindow(sd.eExported);
      const eImported = filterWindow(sd.eImported);
      if (pExport.length || pImport.length) {
        cardSolar.style.display = '';
        const wPower = pExport[0]?.value ?? 0;
        const wImport = pImport[0]?.value ?? 0;
        const aExport = iExport[0]?.value ?? 0;
        const aImport = iImport[0]?.value ?? 0;
        const kwhExported = eExported[0]?.value ?? 0;
        const kwhImported = eImported[0]?.value ?? 0;
        el('liveGridSolar').innerHTML = `
          <span style="color:var(--warning,#f0a020)">Solar:</span> ${fmtKw(wPower, 2)} / ${aExport.toFixed(2)}A<br>
          <span style="color:var(--text-muted)">Rede:</span> ${fmtKw(wImport, 2)} / ${aImport.toFixed(2)}A<br>
          <span style="font-size:11px;color:var(--text-faint)">Acum.: ${kwhExported.toFixed(2)} kWh injet. / ${kwhImported.toFixed(2)} kWh cons.</span>
        `;
      } else {
        cardSolar.style.display = 'none';
      }
    } else if (cardSolar) {
      cardSolar.style.display = 'none';
    }

    const hasEnergyMetrics = voltageData.length > 0 || currentData.length > 0 || powerData.length > 0 || energyData.length > 0;
    const hasSwitch = switchData.length > 0;

    // Verificar status do dispositivo (dados nos últimos 120 segundos)
    const lastReading = voltageData[0] || currentData[0] || powerData[0] || switchData[0];
    const isOnline = lastReading && (Date.now() - new Date(lastReading.timestamp)) < 120000;

    const statusEl = el('deviceStatus');
    if (isOnline) {
      statusEl.className = 'status-indicator status-online';
      statusEl.title = 'Dispositivo online (última leitura há ' + Math.round((Date.now() - new Date(lastReading.timestamp))/1000) + 's)';
    } else {
      statusEl.className = 'status-indicator status-offline';
      statusEl.title = lastReading ?
        'Dispositivo offline (última leitura: ' + new Date(lastReading.timestamp).toLocaleString() + ')' :
        'Sem dados disponíveis';
    }

    if (el('liveSwitch')) {
      if (hasSwitch) {
        const on = Number(switchData[0].value) === 1;
        const age = Math.round((Date.now() - new Date(switchData[0].timestamp)) / 1000);
        el('liveSwitch').textContent = `${on ? 'LIGADO' : 'DESLIGADO'} (${age}s)`;
      } else {
        el('liveSwitch').textContent = '--';
      }
    }

    if (!hasEnergyMetrics && hasSwitch) {
      setIntegrityBanner(
        `<strong>Dados REAIS da Tuya:</strong> este aparelho só envia status de switch/relé (` +
        `${switchData.length} leituras). Não envia tensão/corrente/potência/energia pela Cloud API. ` +
        `Para medir consumo da residência, use um medidor com energia (plug Tuya com kWh, PZEM ou SDM630). ` +
        `Última leitura: ${new Date(switchData[0].timestamp).toLocaleString()}.`,
        true
      );
    } else if (!hasEnergyMetrics && !hasSwitch) {
      setIntegrityBanner(
        `<strong>Sem medições:</strong> o sistema não inventa dados. Cadastre/ative um medidor e aguarde o poller (30s).`,
        true
      );
    } else {
      setIntegrityBanner('', false);
    }

    // Valores atuais (só preenche se houver leitura real; senão "--")
    const v = voltageData[0]?.value;
    const i = currentData[0]?.value;
    const p = powerData[0]?.value;
    const e_wh = energyData[0]?.value;

    // Calcular energia integrada baseada em potência (mais confiável)
    // Energia = integral de potência ao longo do tempo
    let energy_integrated_wh = 0;
    if (powerData.length > 1) {
      for (let idx = 1; idx < powerData.length; idx++) {
        const power_avg = (powerData[idx].value + powerData[idx-1].value) / 2; // Watts
        const time_diff_ms = new Date(powerData[idx-1].timestamp) - new Date(powerData[idx].timestamp);
        const time_diff_h = Math.abs(time_diff_ms) / (1000 * 3600); // Horas
        energy_integrated_wh += power_avg * time_diff_h; // Wh
      }
    }

    const vNum = Number(v || 0);
    const iNum = Number(i || 0);
    const pNum = Number(p || 0);
    const eWhNum = Number(e_wh || 0);

    // Usar energia integrada se disponível, senão usar leitura do medidor (filtrar valores absurdos)
    const e_kwh = (energy_integrated_wh > 0) ? (energy_integrated_wh / 1000.0) :
                  (eWhNum > 0 && eWhNum < 100000) ? (eWhNum / 1000.0) : null;

    // Calcular potência aparente (trifásico vs monofásico)
    let apparent_power = 0;
    if (isThreePhase && window.phaseData) {
      // Trifásico: S = V1*I1 + V2*I2 + V3*I3
      const v1 = window.phaseData.v1[0]?.value || 0;
      const v2 = window.phaseData.v2[0]?.value || 0;
      const v3 = window.phaseData.v3[0]?.value || 0;
      const i1 = window.phaseData.i1[0]?.value || 0;
      const i2 = window.phaseData.i2[0]?.value || 0;
      const i3 = window.phaseData.i3[0]?.value || 0;
      apparent_power = (v1 * i1) + (v2 * i2) + (v3 * i3);
    } else if (hasEnergyMetrics) {
      // Monofásico: S = V * I
      apparent_power = vNum * iNum;
    }

    const power_factor = apparent_power > 0 ? Math.abs(pNum) / apparent_power : null;
    const cost = e_kwh != null ? e_kwh * 0.65 : null;

    // Médias
    const avgV = voltageData.length ? voltageData.reduce((sum, d) => sum + d.value, 0) / voltageData.length : null;
    const avgI = currentData.length ? currentData.reduce((sum, d) => sum + d.value, 0) / currentData.length : null;
    const avgP = powerData.length ? powerData.reduce((sum, d) => sum + d.value, 0) / powerData.length : null;

    // Atualizar valores em tempo real
    if (!hasEnergyMetrics) {
      el('liveVoltage').textContent = 'N/A';
      el('liveCurrent').textContent = 'N/A';
      el('livePower').textContent = 'N/A';
      el('liveEnergy').textContent = 'N/A';
      el('livePF').textContent = 'N/A';
      el('liveCost').textContent = 'N/A';
      el('averagesBox').innerHTML = `
        <strong>Sem métricas de energia neste device.</strong><br>
        Métrica real disponível: <code>switch_status</code> (${switchData.length} leituras).
      `;
    } else if (isThreePhase && window.phaseData) {
      // formatPhaseValue: para potência passe valor já em kW e unit 'kW'
      const formatPhaseValue = (val, unit, decimals = 1) => {
        const value = val || 0;
        const isInactive = Math.abs(value) < (unit === 'kW' ? 0.01 : 0.01);
        const color = isInactive ? 'var(--text-faint)' : 'inherit';
        const label = isInactive ? '(inativo)' : '';
        return `<span style="color:${color}">${value.toFixed(decimals)}${unit} ${label}</span>`;
      };

      // Exibir valores por fase para trifásicos
      el('liveVoltage').innerHTML = `
        <span style="color:var(--phase-l1)">L1:</span> ${formatPhaseValue(window.phaseData.v1[0]?.value, 'V', 1)}<br>
        <span style="color:var(--phase-l2)">L2:</span> ${formatPhaseValue(window.phaseData.v2[0]?.value, 'V', 1)}<br>
        <span style="color:var(--phase-l3)">L3:</span> ${formatPhaseValue(window.phaseData.v3[0]?.value, 'V', 1)}
      `;

      const i1 = window.phaseData.i1[0]?.value || 0;
      const i2 = window.phaseData.i2[0]?.value || 0;
      const i3 = window.phaseData.i3[0]?.value || 0;
      el('liveCurrent').innerHTML = `
        <span style="color:var(--phase-l1)">L1:</span> ${formatPhaseValue(i1, 'A', 2)}<br>
        <span style="color:var(--phase-l2)">L2:</span> ${formatPhaseValue(i2, 'A', 2)}<br>
        <span style="color:var(--phase-l3)">L3:</span> ${formatPhaseValue(i3, 'A', 2)}
      `;

      const p1 = window.phaseData.p1[0]?.value || 0;
      const p2 = window.phaseData.p2[0]?.value || 0;
      const p3 = window.phaseData.p3[0]?.value || 0;
      el('livePower').innerHTML = `
        <span style="color:var(--phase-l1)">L1:</span> ${formatPhaseValue(wattsToKw(p1), 'kW', 2)}<br>
        <span style="color:var(--phase-l2)">L2:</span> ${formatPhaseValue(wattsToKw(p2), 'kW', 2)}<br>
        <span style="color:var(--phase-l3)">L3:</span> ${formatPhaseValue(wattsToKw(p3), 'kW', 2)}<br>
        <strong>Total: ${fmtKw(pNum, 2)}</strong>
      `;
      el('liveEnergy').textContent = (e_kwh != null ? e_kwh.toFixed(3) : '0.000') + ' kWh';
      el('livePF').textContent = power_factor != null ? power_factor.toFixed(3) : '--';
      el('liveCost').textContent = cost != null ? ('R$ ' + cost.toFixed(2)) : 'R$ --';
      el('averagesBox').innerHTML = `
        <strong>Tensão média:</strong> ${(avgV ?? 0).toFixed(2)} V<br>
        <strong>Corrente média:</strong> ${(avgI ?? 0).toFixed(3)} A<br>
        <strong>Potência média:</strong> ${fmtKw(avgP, 2)}<br>
        <strong>Pot. Aparente:</strong> ${(apparent_power / 1000).toFixed(2)} kVA
      `;
    } else {
      // Exibir valores únicos para monofásicos (Linha)
      el('liveVoltage').innerHTML = v != null
        ? `<span style="color:var(--phase-l1)">Linha:</span> ${vNum.toFixed(1)} V`
        : 'N/A';
      el('liveCurrent').innerHTML = i != null
        ? `<span style="color:var(--phase-l1)">Linha:</span> ${iNum.toFixed(3)} A`
        : 'N/A';
      el('livePower').innerHTML = p != null
        ? `<span style="color:var(--phase-l1)">Linha:</span> ${fmtKw(pNum, 2)}`
        : 'N/A';
      el('liveEnergy').textContent = e_kwh != null ? (e_kwh.toFixed(3) + ' kWh') : 'N/A';
      el('livePF').textContent = power_factor != null ? power_factor.toFixed(3) : 'N/A';
      el('liveCost').textContent = cost != null ? ('R$ ' + cost.toFixed(2)) : 'R$ --';
      el('averagesBox').innerHTML = `
        <strong>Tensão média (Linha):</strong> ${(avgV ?? 0).toFixed(2)} V<br>
        <strong>Corrente média:</strong> ${(avgI ?? 0).toFixed(3)} A<br>
        <strong>Potência média:</strong> ${fmtKw(avgP, 2)}<br>
        <strong>Pot. Aparente:</strong> ${(apparent_power / 1000).toFixed(2)} kVA
      `;
    }

    // Criar ou atualizar gráficos individuais
    // IMPORTANTE: não mutar arrays originais com .reverse()
    const eSeries = energyData.slice().reverse();
    const eLabels = eSeries.map(x => new Date(x.timestamp).toLocaleTimeString());
    let vSeries = [];
    let iSeries = [];
    let pSeries = [];
    const swSeries = switchData.slice().reverse();

    if (isThreePhase && window.phaseData) {
      // Gráficos trifásicos com as 3 fases
      const v1_series = window.phaseData.v1.slice().reverse();
      const v2_series = window.phaseData.v2.slice().reverse();
      const v3_series = window.phaseData.v3.slice().reverse();
      const i1_series = window.phaseData.i1.slice().reverse();
      const i2_series = window.phaseData.i2.slice().reverse();
      const i3_series = window.phaseData.i3.slice().reverse();
      const p1_series = window.phaseData.p1.slice().reverse();
      const p2_series = window.phaseData.p2.slice().reverse();
      const p3_series = window.phaseData.p3.slice().reverse();

      vSeries = v1_series;
      iSeries = i1_series;
      pSeries = (window.phaseData.pTotal && window.phaseData.pTotal.length)
        ? window.phaseData.pTotal.slice().reverse()
        : p1_series;

      const vLabels = v1_series.map(x => new Date(x.timestamp).toLocaleTimeString());
      const iLabels = i1_series.map(x => new Date(x.timestamp).toLocaleTimeString());
      const pLabels = p1_series.map(x => new Date(x.timestamp).toLocaleTimeString());

      // Gráfico de Tensões (3 fases)
      if (!charts.voltage || !charts.voltage.data.datasets[1]) {
        if (charts.voltage) charts.voltage.destroy();
        charts.voltage = new Chart(el('chartVoltage'), {
          type: 'line',
          data: {
            labels: vLabels,
            datasets: [
              lineDataset('L1', v1_series.map(x => x.value), C.phaseL1),
              lineDataset('L2', v2_series.map(x => x.value), C.phaseL2),
              lineDataset('L3', v3_series.map(x => x.value), C.phaseL3)
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: { duration: 280 },
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { color: C.text, boxWidth: 12, font: { size: 11 } } }, tooltip: tooltipConfig() },
            scales: chartScaleOpts(C, false, { min: 0, max: 270 })
          }
        });
      } else {
        charts.voltage.data.labels = vLabels;
        charts.voltage.data.datasets[0].data = v1_series.map(x => x.value);
        charts.voltage.data.datasets[1].data = v2_series.map(x => x.value);
        charts.voltage.data.datasets[2].data = v3_series.map(x => x.value);
        charts.voltage.update('none');
      }

      // Gráfico de Correntes (3 fases)
      if (!charts.current || !charts.current.data.datasets[1]) {
        if (charts.current) charts.current.destroy();
        charts.current = new Chart(el('chartCurrent'), {
          type: 'line',
          data: {
            labels: iLabels,
            datasets: [
              lineDataset('L1', i1_series.map(x => x.value), C.phaseL1),
              lineDataset('L2', i2_series.map(x => x.value), C.phaseL2),
              lineDataset('L3', i3_series.map(x => x.value), C.phaseL3)
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: { duration: 280 },
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { color: C.text, boxWidth: 12, font: { size: 11 } } }, tooltip: tooltipConfig() },
            scales: chartScaleOpts(C, true)
          }
        });
      } else {
        charts.current.data.labels = iLabels;
        charts.current.data.datasets[0].data = i1_series.map(x => x.value);
        charts.current.data.datasets[1].data = i2_series.map(x => x.value);
        charts.current.data.datasets[2].data = i3_series.map(x => x.value);
        charts.current.update('none');
      }

      // Gráfico de Potências (3 fases) — eixo em kW
      if (!charts.power || !charts.power.data.datasets[1]) {
        if (charts.power) charts.power.destroy();
        charts.power = new Chart(el('chartPower'), {
          type: 'line',
          data: {
            labels: pLabels,
            datasets: [
              lineDataset('L1', seriesValuesKw(p1_series), C.phaseL1),
              lineDataset('L2', seriesValuesKw(p2_series), C.phaseL2),
              lineDataset('L3', seriesValuesKw(p3_series), C.phaseL3)
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: { duration: 280 },
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { color: C.text, boxWidth: 12, font: { size: 11 } } }, tooltip: tooltipConfig() },
            scales: chartScaleOpts(C, false)
          }
        });
      } else {
        charts.power.data.labels = pLabels;
        charts.power.data.datasets[0].data = seriesValuesKw(p1_series);
        charts.power.data.datasets[1].data = seriesValuesKw(p2_series);
        charts.power.data.datasets[2].data = seriesValuesKw(p3_series);
        charts.power.update('none');
      }

      // Gráficos separados de consumo (rede) x injeção (solar), por fase.
      // Só existem para devices que já fornecem power_import_*/power_export_*
      // (ex.: disjuntor trifásico Tuya "tdq"); ausência = sem geração solar cadastrada.
      const pd = window.phaseData;
      const hasSplit = ['pImpL1', 'pImpL2', 'pImpL3', 'pExpL1', 'pExpL2', 'pExpL3']
        .some((k) => pd[k] && pd[k].length > 0);

      el('cardCurrentCombined').style.display = hasSplit ? 'none' : '';
      el('cardPowerCombined').style.display = hasSplit ? 'none' : '';
      el('cardCurrentImport').style.display = hasSplit ? '' : 'none';
      el('cardCurrentExport').style.display = hasSplit ? '' : 'none';
      el('cardPowerImport').style.display = hasSplit ? '' : 'none';
      el('cardPowerExport').style.display = hasSplit ? '' : 'none';

      if (hasSplit) {
        buildPhaseChart('powerImport', 'chartPowerImport', pd.pImpL1, pd.pImpL2, pd.pImpL3, true, true);
        buildPhaseChart('powerExport', 'chartPowerExport', pd.pExpL1, pd.pExpL2, pd.pExpL3, true, true);
        buildPhaseChart('currentImport', 'chartCurrentImport', pd.iImpL1, pd.iImpL2, pd.iImpL3, true);
        buildPhaseChart('currentExport', 'chartCurrentExport', pd.iExpL1, pd.iExpL2, pd.iExpL3, true);
      } else {
        ['powerImport', 'powerExport', 'currentImport', 'currentExport'].forEach((k) => {
          if (charts[k]) { charts[k].destroy(); charts[k] = null; }
        });
      }

    } else {
      // Gráficos monofásicos — uma série "Linha" (nunca reaproveitar datasets L1/L2/L3)
      ['cardCurrentImport', 'cardCurrentExport', 'cardPowerImport', 'cardPowerExport'].forEach((id) => {
        el(id).style.display = 'none';
      });
      el('cardCurrentCombined').style.display = '';
      el('cardPowerCombined').style.display = '';
      vSeries = voltageData.slice().reverse();
      iSeries = currentData.slice().reverse();
      pSeries = powerData.slice().reverse();

      const vLabels = vSeries.map(x => new Date(x.timestamp).toLocaleTimeString());
      const iLabels = iSeries.map(x => new Date(x.timestamp).toLocaleTimeString());
      const pLabels = pSeries.map(x => new Date(x.timestamp).toLocaleTimeString());

      if (!charts.voltage || (charts.voltage.data.datasets && charts.voltage.data.datasets.length !== 1)) {
        if (charts.voltage) { charts.voltage.destroy(); charts.voltage = null; }
        if (charts.current) { charts.current.destroy(); charts.current = null; }
        if (charts.power) { charts.power.destroy(); charts.power = null; }
        charts.voltage = createChart('chartVoltage', 'Linha (V)', C.voltage, { min: 0, max: 270 });
        charts.current = createChart('chartCurrent', 'Linha (A)', C.current);
        charts.power = createChart('chartPower', 'Linha (kW)', C.power);
        if (charts.voltage?.options?.plugins?.legend) {
          charts.voltage.options.plugins.legend.display = true;
          charts.current.options.plugins.legend.display = true;
          charts.power.options.plugins.legend.display = true;
        }
      }

      updateChart(charts.voltage, vLabels, vSeries.map(x => x.value));
      updateChart(charts.current, iLabels, iSeries.map(x => x.value));
      updateChart(charts.power, pLabels, seriesValuesKw(pSeries));
    }

    // Gráfico de Energia (igual para ambos)
    if (!charts.energy) {
      charts.energy = createChart('chartEnergy', 'Energia (Wh)', C.energy);
    }
    updateChart(charts.energy, eLabels, eSeries.map(x => x.value));

    // Gráfico multi-métrica — monta datasets com o que existir de fato
    const multiSource = (vSeries.length && vSeries)
      || (pSeries.length && pSeries)
      || (iSeries.length && iSeries)
      || (swSeries.length && swSeries)
      || (eSeries.length && eSeries)
      || [];
    const multiSlice = multiSource.slice(0, 80);
    const multiLabels = multiSlice.map(x => new Date(x.timestamp).toLocaleTimeString());
    const multiDayEl = el('chartMultiDay');
    if (multiDayEl) {
      if (multiSlice.length) {
        const start = new Date(multiSlice[0].timestamp);
        const end = new Date(multiSlice[multiSlice.length - 1].timestamp);
        const fmt = (d) => d.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
        const startDay = fmt(start);
        const endDay = fmt(end);
        multiDayEl.textContent = startDay === endDay
          ? `Dados de ${startDay}`
          : `Dados de ${startDay} a ${endDay}`;
      } else {
        multiDayEl.textContent = '';
      }
    }
    const multiDatasets = [];
    if (vSeries.length) {
      multiDatasets.push(lineDataset(isThreePhase ? 'Tensão L1 (V)' : 'Tensão Linha (V)', vSeries.slice(0, 80).map(x => x.value), C.voltage, {
        more: { yAxisID: 'yV' }
      }));
    }
    if (iSeries.length) {
      multiDatasets.push(lineDataset('Corrente (A)', iSeries.slice(0, 80).map(x => x.value), C.current, {
        more: { yAxisID: 'yI' }
      }));
    }
    if (pSeries.length) {
      multiDatasets.push(lineDataset('Potência (kW)', seriesValuesKw(pSeries.slice(0, 80)), C.power, {
        more: { yAxisID: 'yP' }
      }));
    }
    if (swSeries.length) {
      multiDatasets.push(lineDataset('Switch (0/1)', swSeries.slice(0, 80).map(x => x.value), C.switch, {
        tension: 0,
        pointRadius: 2,
        fillAlpha: 0.08,
        more: { yAxisID: 'ySw', stepped: true }
      }));
    }
    if (!multiDatasets.length && eSeries.length) {
      multiDatasets.push(lineDataset('Energia (Wh)', eSeries.slice(0, 80).map(x => x.value), C.energy, {
        fill: true,
        fillAlpha: 0.14,
        more: { yAxisID: 'yP' }
      }));
    }

    const axisTick = (color) => ({ color, maxTicksLimit: 5, font: { size: 10 } });
    const multiScales = {
      x: {
        ticks: { color: C.textMuted, maxTicksLimit: 8, maxRotation: 0, autoSkip: true, font: { size: 10 } },
        grid: { color: C.grid, drawBorder: false }
      },
      yV: { type: 'linear', position: 'left', display: vSeries.length > 0, min: 0, max: 270, title: { display: true, text: 'V', color: C.voltage, font: { size: 11 } }, ticks: axisTick(C.voltage), grid: { color: C.grid, drawBorder: false } },
      yI: { type: 'linear', position: 'right', display: iSeries.length > 0, title: { display: true, text: 'A', color: C.current, font: { size: 11 } }, ticks: axisTick(C.current), grid: { drawOnChartArea: false } },
      yP: { type: 'linear', position: 'right', display: pSeries.length > 0 || eSeries.length > 0, title: { display: true, text: 'kW', color: C.power, font: { size: 11 } }, ticks: axisTick(C.power), grid: { drawOnChartArea: false } },
      ySw: { type: 'linear', position: 'right', display: swSeries.length > 0, min: 0, max: 1.2, title: { display: true, text: 'SW', color: C.switch, font: { size: 11 } }, ticks: { color: C.switch, stepSize: 1, font: { size: 10 } }, grid: { drawOnChartArea: false } }
    };

    if (charts.multi && charts.multi.data && charts.multi.data.datasets.length === multiDatasets.length) {
      charts.multi.data.labels = multiLabels;
      multiDatasets.forEach((ds, i) => {
        charts.multi.data.datasets[i].data = ds.data;
        charts.multi.data.datasets[i].label = ds.label;
      });
      charts.multi.options.scales = multiScales;
      charts.multi.update('none');
    } else {
      if (charts.multi) {
        try { charts.multi.destroy(); } catch (_) {}
        charts.multi = null;
      }
      const multiCanvas = el('chartMulti');
      if (multiCanvas && multiDatasets.length) {
        charts.multi = new Chart(multiCanvas, {
          type: 'line',
          data: { labels: multiLabels, datasets: multiDatasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 280 },
            interaction: { mode: 'index', intersect: false },
            plugins: {
              legend: { display: true, labels: { color: C.text, boxWidth: 12, font: { size: 11 } } },
              title: { display: false },
              tooltip: tooltipConfig()
            },
            scales: multiScales
          }
        });
      } else if (multiCanvas) {
        const ctx = multiCanvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, multiCanvas.width, multiCanvas.height);
        }
      }
    }

    // Alarmes
    const ul = el('alarmsList');
    ul.innerHTML = '';
    if (alarms.length === 0) {
      ul.innerHTML = '<li style="color:var(--text-faint);padding:8px">Nenhum alarme registrado</li>';
    } else {
      alarms.forEach(a => {
        const li = document.createElement('li');
        li.style.padding = '6px 0';
        li.style.borderBottom = '1px solid var(--border-soft)';
        li.innerHTML = `<span style="color:var(--danger)">&#9888;</span> ${new Date(a.timestamp).toLocaleString()} - <strong>${a.metric}</strong> = ${a.value}`;
        ul.appendChild(li);
      });
    }
  } catch (error) {
    console.error('Erro ao renderizar dados:', error);
  }
}

function updateDeviceStatus() {
  const select = el('deviceSelect');
  const option = select.options[select.selectedIndex];
  const isActive = option?.dataset.active === 'True';
  const indicator = el('deviceStatus');

  indicator.className = 'status-indicator ' + (isActive ? 'status-online' : 'status-offline');
  indicator.title = isActive ? 'Dispositivo em operação' : 'Dispositivo desativado';
}

function isDualMeterDevice(device) {
  const cfg = device?.config || {};
  const product = String(cfg.product_name || '').toLowerCase();
  return Boolean(cfg.channel_roles) || product.includes('dual');
}

function fillDualCtForm(cfg) {
  const roles = cfg?.channel_roles || {};
  const aOn = roles.a === 'injection' || roles.a === 'consumption';
  const bOn = roles.b === 'injection' || roles.b === 'consumption';
  el('ctAEnabled').checked = aOn;
  el('ctBEnabled').checked = bOn;
  el('ctARole').value = aOn ? roles.a : 'injection';
  el('ctBRole').value = bOn ? roles.b : 'consumption';
  el('ctARole').disabled = !aOn;
  el('ctBRole').disabled = !bOn;
}

function syncDualCtRoleDisabled() {
  el('ctARole').disabled = !el('ctAEnabled').checked;
  el('ctBRole').disabled = !el('ctBEnabled').checked;
}

function openConfigModal() {
  const select = el('deviceSelect');
  const deviceId = select.value;
  if (!deviceId) return;

  // Buscar config atual do dispositivo
  fetch(`/api/devices`)
    .then(r => r.json())
    .then(devices => {
      const device = devices.find(d => d.id == deviceId);
      if (device) {
        el('configName').value = device.name;
        el('configPort').value = device.config?.port || 'COM3';
        el('configSlaveId').value = device.config?.slave_id || 1;
        el('configBaudrate').value = device.config?.baudrate || 9600;
        el('configDriver').value = device.config?.driver || 'pzem004t';
        el('configActive').checked = device.active;

        const dual = isDualMeterDevice(device);
        el('dualCtConfig').hidden = !dual;
        if (dual) fillDualCtForm(device.config || {});

        el('configModal').dataset.deviceType = device.device_type || '';
        el('configModal').dataset.deviceId = String(device.id);
        el('configModal').style.display = 'block';
      }
    });
}

function closeConfigModal() {
  el('configModal').style.display = 'none';
  el('testResult').style.display = 'none';
}

async function testConnection() {
  const port = el('configPort').value;
  const slaveId = el('configSlaveId').value;
  const baudrate = el('configBaudrate').value;

  const resultDiv = el('testResult');
  resultDiv.textContent = '🔄 Testando conexão...';
  resultDiv.className = '';
  resultDiv.style.display = 'block';

  try {
    // Simular teste (em produção, criar endpoint específico)
    await new Promise(resolve => setTimeout(resolve, 1500));
    resultDiv.textContent = `✅ Conexão OK! Porta ${port}, Slave ${slaveId}, ${baudrate} baud`;
    resultDiv.className = 'success';
  } catch (error) {
    resultDiv.textContent = '❌ Falha na conexão. Verifique porta e configurações.';
    resultDiv.className = 'error';
  }
}

async function saveConfig(e) {
  e.preventDefault();
  const deviceId = el('deviceSelect').value;

  try {
    const devices = await fetch('/api/devices').then(r => r.json());
    const device = devices.find(d => d.id == deviceId);
    if (!device) {
      alert('❌ Dispositivo não encontrado');
      return;
    }

    // Merge: nunca apagar config Tuya (device_id, category, channel_roles…)
    const merged = { ...(device.config || {}) };
    const isTuya = (device.device_type || '').toLowerCase() === 'tuya';

    if (!isTuya) {
      merged.port = el('configPort').value;
      merged.slave_id = parseInt(el('configSlaveId').value, 10);
      merged.baudrate = parseInt(el('configBaudrate').value, 10);
      merged.driver = el('configDriver').value;
      merged.base = merged.base ?? 0;
      merged.count = merged.count ?? 5;
    }

    if (!el('dualCtConfig').hidden) {
      merged.channel_roles = {
        a: el('ctAEnabled').checked ? el('ctARole').value : null,
        b: el('ctBEnabled').checked ? el('ctBRole').value : null,
      };
      merged.phases = 1;
      merged.wiring = 'single';
    }

    const payload = {
      name: el('configName').value,
      active: el('configActive').checked,
      config: merged,
    };

    const response = await fetch(`/api/devices/${deviceId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      alert('✅ Configuração salva com sucesso!');
      closeConfigModal();
      location.reload();
    } else {
      alert('❌ Erro ao salvar configuração');
    }
  } catch (error) {
    alert('❌ Erro: ' + error.message);
  }
}

async function openAlarmModal() {
  el('alarmModal').style.display = 'block';
}

function closeAlarmModal() {
  el('alarmModal').style.display = 'none';
  el('alarmForm').reset();
}

async function createAlarmRule(e) {
  e.preventDefault();
  const deviceId = el('deviceSelect').value;

  const payload = {
    client_id: null,  // será inferido do dispositivo no backend
    device_id: parseInt(deviceId),
    name: el('alarmName').value,
    metric: el('alarmMetric').value,
    operator: el('alarmOperator').value,
    threshold: parseFloat(el('alarmThreshold').value),
    enabled: el('alarmEnabled').checked
  };

  try {
    const response = await fetch('/api/alarms/rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      alert('✅ Regra de alarme criada com sucesso!');
      closeAlarmModal();
      loadAlarmRules();
      loadData();
    } else {
      const error = await response.json();
      alert('❌ Erro ao criar alarme: ' + JSON.stringify(error));
    }
  } catch (error) {
    alert('❌ Erro: ' + error.message);
  }
}

async function loadAlarmRules() {
  const deviceId = el('deviceSelect').value;
  if (!deviceId) return;

  try {
    const rules = await fetchJSON(`/api/alarms/rules?device_id=${deviceId}`);
    const container = el('alarmRulesList');

    if (rules.length === 0) {
      container.innerHTML = '<em style="color:var(--text-faint)">Nenhuma regra configurada</em>';
      return;
    }

    container.innerHTML = '<strong>Regras ativas:</strong><br>' + rules.map(r => {
      const status = r.enabled ? '🟢' : '🔴';
      return `${status} ${r.name}: ${r.metric} ${r.operator} ${r.threshold}`;
    }).join('<br>');
  } catch (error) {
    console.error('Erro ao carregar regras de alarme:', error);
  }
}

async function deleteAlarmRule(ruleId) {
  if (!confirm('Tem certeza que deseja remover esta regra de alarme?')) return;

  try {
    const response = await fetch(`/api/alarms/rules/${ruleId}`, { method: 'DELETE' });
    if (response.ok) {
      alert('✅ Regra removida!');
      loadAlarmRules();
    } else {
      alert('❌ Erro ao remover regra');
    }
  } catch (error) {
    alert('❌ Erro: ' + error.message);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  el('refreshBtn').addEventListener('click', loadData);
  el('deviceSelect').addEventListener('change', () => {
    updateDeviceStatus();
    loadAlarmRules();
    resetPeriodNav();
    updatePeriodRangeLabel();
    loadData();
  });

  el('zoomFrom').addEventListener('input', applyZoomFromSliders);
  el('zoomTo').addEventListener('input', applyZoomFromSliders);
  el('periodPrevBtn').addEventListener('click', () => navigatePeriod(-1));
  el('periodNextBtn').addEventListener('click', () => navigatePeriod(1));
  el('periodTodayBtn').addEventListener('click', () => {
    resetPeriodNav();
    updatePeriodRangeLabel();
    setLiveStatus('live');
    loadData();
  });
  el('zoomResetBtn').addEventListener('click', resetZoom);
  el('configBtn').addEventListener('click', openConfigModal);
  el('configModal').querySelector('.close').addEventListener('click', closeConfigModal);
  el('testBtn').addEventListener('click', testConnection);
  el('configForm').addEventListener('submit', saveConfig);
  el('ctAEnabled').addEventListener('change', syncDualCtRoleDisabled);
  el('ctBEnabled').addEventListener('change', syncDualCtRoleDisabled);

  el('addAlarmBtn').addEventListener('click', openAlarmModal);
  el('alarmForm').addEventListener('submit', createAlarmRule);

  document.querySelectorAll('.period-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.period-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentPeriod = btn.dataset.period || '1d';
      resetPeriodNav();
      updatePeriodRangeLabel();
      destroyAllCharts();
      loadData();
    });
  });

  // Recriar gráficos com as cores certas ao trocar de tema
  window.addEventListener('theme-changed', () => {
    destroyAllCharts();
    loadData();
  });

  window.onclick = (e) => {
    if (e.target === el('configModal')) closeConfigModal();
    if (e.target === el('alarmModal')) closeAlarmModal();
  };

  updateDeviceStatus();
  updatePeriodRangeLabel();
  loadAlarmRules();
  loadData();
  setInterval(() => {
    // Período passado fixo: não auto-atualiza (evita “pular” o histórico).
    if (anchorEnd != null) {
      setLiveStatus('paused');
      return;
    }
    loadData();
  }, AUTO_REFRESH_MS);
});


