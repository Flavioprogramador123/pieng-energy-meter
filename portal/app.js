(function () {
  const statusEl = document.getElementById("status");
  const helpEl = document.getElementById("help");
  let chart;
  let base = (window.PIENG_API_BASE || "").replace(/\/$/, "");
  const deviceId = Number(window.PIENG_DEVICE_ID || 5);
  const refreshMs = Number(window.PIENG_REFRESH_MS || 180000);

  function setStatus(ok, text) {
    statusEl.textContent = text;
    statusEl.classList.toggle("ok", !!ok);
    statusEl.classList.toggle("err", !ok);
  }

  function showHelp(html) {
    if (helpEl) helpEl.innerHTML = html;
  }

  async function fetchJSON(path) {
    const r = await fetch(base + path, { mode: "cors" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  function fmt(n, digits, unit) {
    if (n == null || Number.isNaN(Number(n))) return "—";
    return Number(n).toLocaleString("pt-BR", { maximumFractionDigits: digits }) + (unit || "");
  }

  async function load() {
    if (!base) {
      setStatus(false, "API não configurada (PIENG_API_BASE vazio)");
      showHelp(
        "<strong>Por que não há dados?</strong> O Vercel só hospeda esta página. " +
        "Os números vêm da API na CCA/notebook. É preciso uma URL <em>HTTPS pública</em> " +
        "(Tailscale Funnel ou Cloudflare Tunnel), depois colar em <code>portal/config.js</code> e redeploy."
      );
      return;
    }
    if (base.startsWith("http://")) {
      setStatus(false, "API em HTTP — bloqueada pelo navegador neste site HTTPS");
      showHelp(
        "Página no Vercel = <strong>HTTPS</strong>. API em <code>http://…</code> ou IP <code>100.x</code> " +
        "é bloqueada (mixed content / rede privada). Ative o <strong>Tailscale Funnel</strong> e use a URL https://…ts.net"
      );
      return;
    }

    try {
      const [live, v1, p, e, series] = await Promise.all([
        fetchJSON("/api/db/collector-live").catch(() => null),
        fetchJSON(`/api/metrics?device_id=${deviceId}&metric=voltage_l1&limit=1`),
        fetchJSON(`/api/metrics?device_id=${deviceId}&metric=power_total&limit=1`),
        fetchJSON(`/api/metrics?device_id=${deviceId}&metric=energy_wh&limit=1`),
        fetchJSON(`/api/metrics?device_id=${deviceId}&metric=power_total&limit=500&period=1d`),
      ]);

      document.getElementById("kpiV").textContent = fmt(v1[0] && v1[0].value, 1, " V");
      const w = p[0] && p[0].value;
      document.getElementById("kpiP").textContent =
        w == null ? "—" : fmt(Math.abs(Number(w)) / 1000, 2, " kW");
      const wh = e[0] && e[0].value;
      document.getElementById("kpiE").textContent =
        wh == null ? "—" : fmt(Number(wh) / 1000, 2, " kWh");

      const points = (series || []).slice().reverse();
      const labels = points.map((x) =>
        new Date(x.timestamp).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
      );
      const values = points.map((x) => Math.abs(Number(x.value)) / 1000);

      const ctx = document.getElementById("chartPower");
      if (chart) chart.destroy();
      chart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [{
            label: "kW",
            data: values,
            borderColor: "#3dd6c6",
            backgroundColor: "rgba(61,214,198,0.12)",
            fill: true,
            tension: 0.25,
            pointRadius: 0,
          }],
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { maxTicksLimit: 8, color: "#8b9aab" }, grid: { color: "rgba(255,255,255,0.04)" } },
            y: { ticks: { color: "#8b9aab" }, grid: { color: "rgba(255,255,255,0.06)" } },
          },
        },
      });

      const last = live && live.last_collection_at
        ? new Date(live.last_collection_at).toLocaleTimeString("pt-BR")
        : (v1[0] && new Date(v1[0].timestamp).toLocaleTimeString("pt-BR")) || "—";
      const poll = (live && live.interval_seconds) || Math.round(refreshMs / 1000);
      setStatus(true, `Dados ok · última ${last} · poll ${poll}s · device ${deviceId}`);
      showHelp("");
    } catch (err) {
      setStatus(false, "Falha na API: " + (err.message || err));
      showHelp(
        "Confira se o Funnel/túnel está ligado e se o Meter responde em <code>" +
        base +
        "</code>. CORS já está liberado no FastAPI."
      );
    }
  }

  load();
  setInterval(load, refreshMs);
})();
