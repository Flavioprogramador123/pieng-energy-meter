(function () {
  const $ = (sel) => document.querySelector(sel);

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}));
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch (e) { data = { detail: text }; }
    if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
    return data;
  }

  function fmt(v) {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  }

  async function refreshStatus() {
    const data = await api('/api/db/status');
    const m = data.mirror || {};
    const box = $('#mirror-status');
    if (!m.ok) {
      box.innerHTML = `<span class="badge badge-err">OFFLINE</span><div>${fmt(m.error)}</div><div class="muted">${fmt(m.url_host)}</div>`;
    } else {
      box.innerHTML = [
        `<span class="badge badge-ok">ONLINE</span>`,
        `<div>${fmt(m.version)}</div>`,
        `<div class="muted">host: ${fmt(m.url_host)}</div>`,
        `<div class="muted">data_directory: ${fmt(m.data_directory)}</div>`,
        `<div class="muted">hot_path: ${fmt(data.hot_path)} (Dashboard lê daqui)</div>`,
      ].join('');
    }

    const rt = data.flush || {};
    $('#flush-enabled').checked = !!rt.postgres_flush_enabled;
    $('#flush-minutes').value = rt.postgres_flush_interval_minutes || 30;
    if ($('#cache-max-mb')) $('#cache-max-mb').value = rt.sqlite_cache_max_mb || 200;
    const last = rt.last || {};
    $('#flush-last').textContent = last.last_run_at
      ? `Último flush: ${last.last_run_at} | ok=${last.ok} | ${JSON.stringify(last.copied || {})} | ${last.duration_ms || 0}ms${last.last_error ? ' | err=' + last.last_error : ''}`
      : 'Ainda não houve flush nesta sessão.';

    const cache = data.sqlite_cache || {};
    const cacheEl = $('#cache-status');
    if (cacheEl) {
      const flag = cache.over_limit ? '⚠ SOBRE O TETO' : 'OK';
      cacheEl.textContent = `Cache SQLite: ${cache.size_mb ?? '—'} MB / ${cache.max_mb ?? 200} MB (${cache.used_pct ?? 0}%) ${flag}`;
      cacheEl.style.color = cache.over_limit ? 'var(--danger)' : '';
    }

    const tbody = $('#counts-table tbody');
    tbody.innerHTML = '';
    const tables = ['clients', 'devices', 'measurements', 'alarm_rules', 'alarm_events'];
    const sqlite = data.sqlite_counts || {};
    const pg = (m.counts) || {};
    tables.forEach((t) => {
      const s = sqlite[t];
      const p = pg[t];
      const diff = (typeof s === 'number' && typeof p === 'number') ? (s - p) : '—';
      const tr = document.createElement('tr');
      tr.innerHTML = `<td><button type="button" class="linkish" data-table="${t}">${t}</button></td><td class="mono">${fmt(s)}</td><td class="mono">${fmt(p)}</td><td class="mono">${fmt(diff)}</td>`;
      tbody.appendChild(tr);
    });
    tbody.querySelectorAll('[data-table]').forEach((btn) => {
      btn.addEventListener('click', () => {
        $('#table-select').value = btn.getAttribute('data-table');
        loadTable();
      });
    });
  }

  async function loadTable() {
    const table = $('#table-select').value;
    const data = await api(`/api/db/tables/${encodeURIComponent(table)}?limit=50&offset=0`);
    $('#table-meta').textContent = `${data.total} linhas (mostrando ${data.rows.length})`;
    const thead = $('#rows-table thead');
    const tbody = $('#rows-table tbody');
    thead.innerHTML = '<tr>' + data.columns.map((c) => `<th>${c}</th>`).join('') + '</tr>';
    tbody.innerHTML = '';
    data.rows.forEach((row) => {
      const tr = document.createElement('tr');
      tr.innerHTML = data.columns.map((c) => `<td class="mono">${fmt(row[c])}</td>`).join('');
      tbody.appendChild(tr);
    });
  }

  $('#btn-refresh').addEventListener('click', () => refreshStatus().catch(alert));
  $('#btn-load-table').addEventListener('click', () => loadTable().catch(alert));
  $('#btn-flush').addEventListener('click', async () => {
    try {
      $('#btn-flush').disabled = true;
      await api('/api/db/flush', { method: 'POST', body: '{}' });
      await refreshStatus();
      await loadTable();
    } catch (e) {
      alert(e.message || e);
    } finally {
      $('#btn-flush').disabled = false;
    }
  });

  $('#flush-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      await api('/api/db/settings', {
        method: 'PATCH',
        body: JSON.stringify({
          postgres_flush_enabled: $('#flush-enabled').checked,
          postgres_flush_interval_minutes: Number($('#flush-minutes').value),
          sqlite_cache_max_mb: Number($('#cache-max-mb') && $('#cache-max-mb').value),
        }),
      });
      await refreshStatus();
      alert('Configuração salva. O intervalo do flush foi reaplicado.');
    } catch (e) {
      alert(e.message || e);
    }
  });

  refreshStatus().then(loadTable).catch((e) => {
    $('#mirror-status').textContent = e.message || String(e);
  });
})();
