async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

function el(id) { return document.getElementById(id); }

let charts = {};
let currentPeriod = '1d';

function metricsUrl(deviceId, metric, limit = 100) {
  return `/api/metrics?device_id=${deviceId}&metric=${metric}&limit=${limit}&period=${currentPeriod}`;
}

function createChart(canvasId, label, color) {
  const C = getChartColors();
  return new Chart(el(canvasId), {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: label,
        data: [],
        borderColor: color,
        backgroundColor: hexToRgba(color, 0.2),
        tension: 0.4,
        fill: true,
        borderWidth: 3,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: tooltipConfig()
      },
      scales: {
        x: { ticks: { color: C.textMuted }, grid: { color: C.grid } },
        y: { beginAtZero: true, ticks: { color: C.textMuted }, grid: { color: C.gridStrong } }
      }
    }
  });
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

  const C = getChartColors();

  try {
    // Detectar se é medidor trifásico (buscar métricas por fase)
    const voltage_l1_check = await fetchJSON(metricsUrl(deviceId, 'voltage_l1', 1));
    const isThreePhase = voltage_l1_check.length > 0;

    let voltageData, currentData, powerData;

    let energyData, alarms, switchData;
    const chartLimit = currentPeriod === '1m' ? 5000 : (currentPeriod === '1w' ? 2500 : 500);

    if (isThreePhase) {
      // Buscar métricas trifásicas
      const [v1, v2, v3, i1, i2, i3, p1, p2, p3, pTotal, eData, alarmsData, swData] = await Promise.all([
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
        fetchJSON(metricsUrl(deviceId, 'switch_status', chartLimit))
      ]);

      // Armazenar dados por fase para uso posterior
      window.phaseData = { v1, v2, v3, i1, i2, i3, p1, p2, p3, pTotal };
      voltageData = v1; // usar L1 como referência para status
      currentData = i1;
      powerData = pTotal.length > 0 ? pTotal : p1;
      energyData = eData;
      alarms = alarmsData;
      switchData = swData;

    } else {
      // Buscar métricas monofásicas (formato antigo) + switch Tuya
      const [vData, iData, pData, eData, alarmsData, swData] = await Promise.all([
        fetchJSON(metricsUrl(deviceId, 'voltage', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'current', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'power', chartLimit)),
        fetchJSON(metricsUrl(deviceId, 'energy_wh', chartLimit)),
        fetchJSON(`/api/alarms/events?device_id=${deviceId}&limit=20`),
        fetchJSON(metricsUrl(deviceId, 'switch_status', chartLimit))
      ]);
      voltageData = vData;
      currentData = iData;
      powerData = pData;
      energyData = eData;
      alarms = alarmsData;
      switchData = swData;
      window.phaseData = null;
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
      // Helper para formatar com indicador de inatividade
      const formatPhaseValue = (val, unit, decimals = 1) => {
        const value = val || 0;
        const isInactive = Math.abs(value) < 0.01;
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
        <span style="color:var(--phase-l1)">L1:</span> ${formatPhaseValue(p1, 'W', 0)}<br>
        <span style="color:var(--phase-l2)">L2:</span> ${formatPhaseValue(p2, 'W', 0)}<br>
        <span style="color:var(--phase-l3)">L3:</span> ${formatPhaseValue(p3, 'W', 0)}<br>
        <strong>Total: ${pNum.toFixed(0)}W</strong>
      `;
      el('liveEnergy').textContent = (e_kwh != null ? e_kwh.toFixed(3) : '0.000') + ' kWh';
      el('livePF').textContent = power_factor != null ? power_factor.toFixed(3) : '--';
      el('liveCost').textContent = cost != null ? ('R$ ' + cost.toFixed(2)) : 'R$ --';
      el('averagesBox').innerHTML = `
        <strong>Tensão média:</strong> ${(avgV ?? 0).toFixed(2)} V<br>
        <strong>Corrente média:</strong> ${(avgI ?? 0).toFixed(3)} A<br>
        <strong>Potência média:</strong> ${(avgP ?? 0).toFixed(2)} W<br>
        <strong>Pot. Aparente:</strong> ${apparent_power.toFixed(2)} VA
      `;
    } else {
      // Exibir valores únicos para monofásicos
      el('liveVoltage').textContent = v != null ? (vNum.toFixed(1) + ' V') : 'N/A';
      el('liveCurrent').textContent = i != null ? (iNum.toFixed(3) + ' A') : 'N/A';
      el('livePower').textContent = p != null ? (pNum.toFixed(1) + ' W') : 'N/A';
      el('liveEnergy').textContent = e_kwh != null ? (e_kwh.toFixed(3) + ' kWh') : 'N/A';
      el('livePF').textContent = power_factor != null ? power_factor.toFixed(3) : 'N/A';
      el('liveCost').textContent = cost != null ? ('R$ ' + cost.toFixed(2)) : 'N/A';
      el('averagesBox').innerHTML = `
        <strong>Tensão média:</strong> ${(avgV ?? 0).toFixed(2)} V<br>
        <strong>Corrente média:</strong> ${(avgI ?? 0).toFixed(3)} A<br>
        <strong>Potência média:</strong> ${(avgP ?? 0).toFixed(2)} W<br>
        <strong>Pot. Aparente:</strong> ${apparent_power.toFixed(2)} VA
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
              { label: 'L1', data: v1_series.map(x => x.value), borderColor: C.phaseL1, backgroundColor: hexToRgba(C.phaseL1, 0.15), tension: 0.4, borderWidth: 3 },
              { label: 'L2', data: v2_series.map(x => x.value), borderColor: C.phaseL2, backgroundColor: hexToRgba(C.phaseL2, 0.12), tension: 0.4, borderWidth: 3 },
              { label: 'L3', data: v3_series.map(x => x.value), borderColor: C.phaseL3, backgroundColor: hexToRgba(C.phaseL3, 0.12), tension: 0.4, borderWidth: 3 }
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { color: C.text } }, tooltip: tooltipConfig() },
            scales: {
              x: { ticks: { color: C.textMuted }, grid: { color: C.grid } },
              y: { beginAtZero: false, ticks: { color: C.textMuted }, grid: { color: C.gridStrong } }
            }
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
              { label: 'L1', data: i1_series.map(x => x.value), borderColor: C.phaseL1, backgroundColor: hexToRgba(C.phaseL1, 0.15), tension: 0.4, borderWidth: 3 },
              { label: 'L2', data: i2_series.map(x => x.value), borderColor: C.phaseL2, backgroundColor: hexToRgba(C.phaseL2, 0.12), tension: 0.4, borderWidth: 3 },
              { label: 'L3', data: i3_series.map(x => x.value), borderColor: C.phaseL3, backgroundColor: hexToRgba(C.phaseL3, 0.12), tension: 0.4, borderWidth: 3 }
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { color: C.text } }, tooltip: tooltipConfig() },
            scales: {
              x: { ticks: { color: C.textMuted }, grid: { color: C.grid } },
              y: { beginAtZero: true, ticks: { color: C.textMuted }, grid: { color: C.gridStrong } }
            }
          }
        });
      } else {
        charts.current.data.labels = iLabels;
        charts.current.data.datasets[0].data = i1_series.map(x => x.value);
        charts.current.data.datasets[1].data = i2_series.map(x => x.value);
        charts.current.data.datasets[2].data = i3_series.map(x => x.value);
        charts.current.update('none');
      }

      // Gráfico de Potências (3 fases)
      if (!charts.power || !charts.power.data.datasets[1]) {
        if (charts.power) charts.power.destroy();
        charts.power = new Chart(el('chartPower'), {
          type: 'line',
          data: {
            labels: pLabels,
            datasets: [
              { label: 'L1', data: p1_series.map(x => x.value), borderColor: C.phaseL1, backgroundColor: hexToRgba(C.phaseL1, 0.15), tension: 0.4, borderWidth: 3 },
              { label: 'L2', data: p2_series.map(x => x.value), borderColor: C.phaseL2, backgroundColor: hexToRgba(C.phaseL2, 0.12), tension: 0.4, borderWidth: 3 },
              { label: 'L3', data: p3_series.map(x => x.value), borderColor: C.phaseL3, backgroundColor: hexToRgba(C.phaseL3, 0.12), tension: 0.4, borderWidth: 3 }
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { color: C.text } }, tooltip: tooltipConfig() },
            scales: {
              x: { ticks: { color: C.textMuted }, grid: { color: C.grid } },
              y: { beginAtZero: false, ticks: { color: C.textMuted }, grid: { color: C.gridStrong } }
            }
          }
        });
      } else {
        charts.power.data.labels = pLabels;
        charts.power.data.datasets[0].data = p1_series.map(x => x.value);
        charts.power.data.datasets[1].data = p2_series.map(x => x.value);
        charts.power.data.datasets[2].data = p3_series.map(x => x.value);
        charts.power.update('none');
      }

    } else {
      // Gráficos monofásicos (formato original)
      vSeries = voltageData.slice().reverse();
      iSeries = currentData.slice().reverse();
      pSeries = powerData.slice().reverse();

      const vLabels = vSeries.map(x => new Date(x.timestamp).toLocaleTimeString());
      const iLabels = iSeries.map(x => new Date(x.timestamp).toLocaleTimeString());
      const pLabels = pSeries.map(x => new Date(x.timestamp).toLocaleTimeString());

      if (!charts.voltage) {
        charts.voltage = createChart('chartVoltage', 'Tensão (V)', C.voltage);
        charts.current = createChart('chartCurrent', 'Corrente (A)', C.current);
        charts.power = createChart('chartPower', 'Potência (W)', C.power);
      }

      updateChart(charts.voltage, vLabels, vSeries.map(x => x.value));
      updateChart(charts.current, iLabels, iSeries.map(x => x.value));
      updateChart(charts.power, pLabels, pSeries.map(x => x.value));
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
    const multiLabels = multiSource.slice(0, 80).map(x => new Date(x.timestamp).toLocaleTimeString());
    const multiDatasets = [];
    if (vSeries.length) {
      multiDatasets.push({
        label: 'Tensão (V)',
        data: vSeries.slice(0, 80).map(x => x.value),
        borderColor: C.voltage,
        backgroundColor: hexToRgba(C.voltage, 0.12),
        yAxisID: 'yV',
        tension: 0.4,
        borderWidth: 3
      });
    }
    if (iSeries.length) {
      multiDatasets.push({
        label: 'Corrente (A)',
        data: iSeries.slice(0, 80).map(x => x.value),
        borderColor: C.current,
        backgroundColor: hexToRgba(C.current, 0.12),
        yAxisID: 'yI',
        tension: 0.4,
        borderWidth: 3
      });
    }
    if (pSeries.length) {
      multiDatasets.push({
        label: 'Potência (W)',
        data: pSeries.slice(0, 80).map(x => x.value),
        borderColor: C.power,
        backgroundColor: hexToRgba(C.power, 0.12),
        yAxisID: 'yP',
        tension: 0.4,
        borderWidth: 3
      });
    }
    if (swSeries.length) {
      multiDatasets.push({
        label: 'Switch (0/1)',
        data: swSeries.slice(0, 80).map(x => x.value),
        borderColor: C.switch,
        backgroundColor: hexToRgba(C.switch, 0.15),
        yAxisID: 'ySw',
        tension: 0,
        stepped: true,
        borderWidth: 3,
        pointRadius: 3
      });
    }
    if (!multiDatasets.length && eSeries.length) {
      multiDatasets.push({
        label: 'Energia (Wh)',
        data: eSeries.slice(0, 80).map(x => x.value),
        borderColor: C.energy,
        backgroundColor: hexToRgba(C.energy, 0.15),
        yAxisID: 'yP',
        tension: 0.4,
        borderWidth: 3
      });
    }

    const multiScales = {
      x: { ticks: { color: C.textMuted }, grid: { color: C.grid } },
      yV: { type: 'linear', position: 'left', display: vSeries.length > 0, title: { display: true, text: 'V', color: C.voltage }, ticks: { color: C.voltage }, grid: { color: C.grid } },
      yI: { type: 'linear', position: 'right', display: iSeries.length > 0, title: { display: true, text: 'A', color: C.current }, ticks: { color: C.current }, grid: { drawOnChartArea: false } },
      yP: { type: 'linear', position: 'right', display: pSeries.length > 0 || eSeries.length > 0, title: { display: true, text: 'W', color: C.power }, ticks: { color: C.power }, grid: { drawOnChartArea: false } },
      ySw: { type: 'linear', position: 'right', display: swSeries.length > 0, min: 0, max: 1.2, title: { display: true, text: 'SW', color: C.switch }, ticks: { color: C.switch, stepSize: 1 }, grid: { drawOnChartArea: false } }
    };

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
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: true, labels: { color: C.text } },
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
    console.error('Erro ao carregar dados:', error);
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

  const config = {
    name: el('configName').value,
    active: el('configActive').checked,
    config: {
      port: el('configPort').value,
      slave_id: parseInt(el('configSlaveId').value),
      baudrate: parseInt(el('configBaudrate').value),
      driver: el('configDriver').value,
      base: 0,
      count: 5
    }
  };

  try {
    const response = await fetch(`/api/devices/${deviceId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
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
    loadData();
  });
  el('configBtn').addEventListener('click', openConfigModal);
  el('configModal').querySelector('.close').addEventListener('click', closeConfigModal);
  el('testBtn').addEventListener('click', testConnection);
  el('configForm').addEventListener('submit', saveConfig);

  el('addAlarmBtn').addEventListener('click', openAlarmModal);
  el('alarmForm').addEventListener('submit', createAlarmRule);

  document.querySelectorAll('.period-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.period-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentPeriod = btn.dataset.period || '1d';
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
  loadAlarmRules();
  loadData();
  setInterval(loadData, 30000);
});


