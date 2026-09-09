// Tema claro/escuro - persistido em localStorage, aplicado antes do paint
// (o snippet inline no <head> do base.html já define data-theme cedo para
// evitar flash); este arquivo cuida dos botões e da paleta usada pelos
// gráficos Chart.js, que não seguem variáveis CSS automaticamente.

const EM_CHART_COLORS = {
  dark: {
    text: '#e6edf3', textMuted: '#8b98a8',
    grid: 'rgba(255,255,255,0.06)', gridStrong: 'rgba(255,255,255,0.08)',
    phaseL1: '#e5484d', phaseL2: '#f2b705', phaseL3: '#3b82f6',
    voltage: '#f2b705', current: '#3b82f6', power: '#2dd4bf', energy: '#8b7cf6',
    pf: '#3fb950', cost: '#d4a72c', switch: '#94a3b8',
    ok: '#3fb950', danger: '#e5484d', warn: '#d29922'
  },
  light: {
    text: '#1a2029', textMuted: '#5b6675',
    grid: 'rgba(0,0,0,0.06)', gridStrong: 'rgba(0,0,0,0.09)',
    phaseL1: '#dc2626', phaseL2: '#b45309', phaseL3: '#2563eb',
    voltage: '#b45309', current: '#2563eb', power: '#0f766e', energy: '#6d28d9',
    pf: '#15803d', cost: '#92660a', switch: '#64748b',
    ok: '#15803d', danger: '#dc2626', warn: '#92660a'
  }
};

function getTheme() {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
}

function getChartColors() {
  return EM_CHART_COLORS[getTheme()];
}

function hexToRgba(hex, alpha) {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function setTheme(name) {
  document.documentElement.dataset.theme = name;
  try { localStorage.setItem('em-theme', name); } catch (e) { /* ignore */ }
  document.querySelectorAll('.theme-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.theme === name);
  });
  window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme: name } }));
}

window.EM_THEME = { getTheme, getChartColors, setTheme };

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.theme-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.theme === getTheme());
    btn.addEventListener('click', () => setTheme(btn.dataset.theme));
  });
});
