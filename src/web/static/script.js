// ========================
// multiCAD-MCP Dashboard
// ========================

// State
let cadStatus = { connected: false, cad_type: 'None', drawings: [], current_drawing: 'None' };
let layers = [];
let blocks = [];
let entities = [];

// DOM refs
const navButtons = document.querySelectorAll('.nav-btn');
const connectionIndicator = document.querySelector('.status-indicator');
const connectionText = document.querySelector('.status-text');
const refreshBtn = document.getElementById('refresh-all');
const autoRefreshToggle = document.getElementById('auto-refresh-toggle');

// Refresh management
let refreshInterval = null;

function manageAutoRefresh() {
    if (autoRefreshToggle && autoRefreshToggle.checked) {
        if (!refreshInterval) {
            refreshInterval = setInterval(refreshData, 15000);
        }
    } else {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    refreshData();
    manageAutoRefresh();
});

function setupEventListeners() {
    // Sidebar nav — scroll to section
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            handleNavClick(tab);

            // Highlight active
            document.querySelectorAll('.nav-item').forEach(li => li.classList.remove('active'));
            btn.parentElement.classList.add('active');
        });
    });

    // Refresh
    refreshBtn?.addEventListener('click', handleManualRefresh);
    autoRefreshToggle?.addEventListener('change', manageAutoRefresh);

    // Filters
    document.getElementById('filter-entities')?.addEventListener('input', renderEntities);
    document.getElementById('filter-entities-layer')?.addEventListener('change', renderEntities);
    document.getElementById('filter-layers')?.addEventListener('input', renderLayers);
    document.getElementById('filter-blocks')?.addEventListener('input', renderBlocks);

    // Accordions
    document.getElementById('expand-all-entities')?.addEventListener('click', () => toggleAllAccordions('entities-container', true));
    document.getElementById('collapse-all-entities')?.addEventListener('click', () => toggleAllAccordions('entities-container', false));
    document.getElementById('expand-all-layers')?.addEventListener('click', () => toggleAllAccordions('layers-container', true));
    document.getElementById('collapse-all-layers')?.addEventListener('click', () => toggleAllAccordions('layers-container', false));
    document.getElementById('expand-all-blocks')?.addEventListener('click', () => toggleAllAccordions('blocks-container', true));
    document.getElementById('collapse-all-blocks')?.addEventListener('click', () => toggleAllAccordions('blocks-container', false));
}

function handleNavClick(tab) {
    const logsSection = document.getElementById('logs-section');

    if (tab === 'logs') {
        if (logsSection) logsSection.style.display = 'block';
        logsSection?.scrollIntoView({ behavior: 'smooth' });
    } else if (tab === 'entities') {
        if (logsSection) logsSection.style.display = 'none';
        document.getElementById('entities-container')?.scrollIntoView({ behavior: 'smooth' });
    } else if (tab === 'layers') {
        if (logsSection) logsSection.style.display = 'none';
        document.getElementById('layers-container')?.scrollIntoView({ behavior: 'smooth' });
    } else if (tab === 'blocks') {
        if (logsSection) logsSection.style.display = 'none';
        document.getElementById('blocks-container')?.scrollIntoView({ behavior: 'smooth' });
    } else {
        // overview — scroll to top
        if (logsSection) logsSection.style.display = 'none';
        document.querySelector('.content-area')?.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

async function handleManualRefresh() {
    if (!refreshBtn || refreshBtn.classList.contains('loading')) return;

    refreshBtn.classList.add('loading');
    const btnText = refreshBtn.querySelector('.btn-text');
    const orig = btnText ? btnText.textContent : 'Refrescar';
    if (btnText) btnText.textContent = 'Refrescando...';

    try {
        const res = await fetch('/api/cad/refresh', { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            await refreshData();
            showToast('✅ Datos actualizados', 'success');
        } else {
            showToast('❌ Error de refresco', 'error');
        }
    } catch (err) {
        showToast('❌ Error de conexión', 'error');
    } finally {
        setTimeout(() => {
            refreshBtn.classList.remove('loading');
            if (btnText) btnText.textContent = orig;
        }, 300);
    }
}

// ========================
// Data
// ========================

async function refreshData() {
    try {
        const res = await fetch('/api/cad/status');
        const data = await res.json();
        if (data.success) {
            cadStatus = data.status;
            if (cadStatus.connected) {
                await fetchDetails();
            } else {
                layers = []; blocks = []; entities = [];
            }
            updateUI();
        }
    } catch (err) {
        console.error('Refresh error:', err);
    }
}

async function fetchDetails() {
    try {
        const [lR, bR, eR] = await Promise.all([
            fetch('/api/cad/layers'),
            fetch('/api/cad/blocks'),
            fetch('/api/cad/entities')
        ]);
        const [lD, bD, eD] = await Promise.all([lR.json(), bR.json(), eR.json()]);
        layers = lD.success ? lD.layers : [];
        blocks = bD.success ? bD.blocks : [];
        entities = eD.success ? eD.entities : [];
    } catch (err) {
        console.error('Details error:', err);
    }
}

// ========================
// UI
// ========================

function updateUI() {
    const c = cadStatus.connected;

    // Sidebar status
    if (connectionIndicator) connectionIndicator.className = `status-indicator ${c ? 'green' : 'red'}`;
    if (connectionText) connectionText.textContent = c ? 'Conectado' : 'Desconectado';

    // Stat cards
    const cadType = document.getElementById('cad-type-display');
    const drawShort = document.getElementById('current-drawing-name-short');
    const entCount = document.getElementById('entities-count');
    if (cadType) cadType.textContent = cadStatus.cad_type || 'Ninguno';
    if (drawShort) drawShort.textContent = cadStatus.current_drawing || 'Ninguno';
    if (entCount) entCount.textContent = entities.length;

    // Drawing card
    const drawName = document.getElementById('current-drawing-name');
    const drawPath = document.getElementById('current-drawing-path');
    if (drawName) drawName.textContent = c ? (cadStatus.current_drawing || 'Sin dibujo') : 'Esperando conexión...';
    if (drawPath) drawPath.textContent = c ? 'Documento activo' : 'Conecta a ZWCAD a través de MCP';

    // Badges
    const layBadge = document.getElementById('total-layers-count');
    const blkBadge = document.getElementById('total-blocks-count');
    if (layBadge) layBadge.textContent = layers.length;
    if (blkBadge) blkBadge.textContent = blocks.length;

    populateLayerFilter();
    renderEntities();
    renderLayers();
    renderBlocks();
}

function populateLayerFilter() {
    const sel = document.getElementById('filter-entities-layer');
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = '<option value="">Todas las capas</option>';
    [...new Set(entities.map(e => e.Layer).filter(Boolean))].sort().forEach(n => {
        const o = document.createElement('option');
        o.value = n; o.textContent = n;
        sel.appendChild(o);
    });
    sel.value = cur;
}

// ========================
// Renderers
// ========================

function renderEntities() {
    const container = document.getElementById('entities-container');
    if (!container) return;

    const ft = (document.getElementById('filter-entities')?.value || '').toLowerCase();
    const fl = document.getElementById('filter-entities-layer')?.value || '';

    let filtered = entities;
    if (ft) filtered = filtered.filter(e =>
        (e.Handle || '').toLowerCase().includes(ft) || (e.ObjectType || '').toLowerCase().includes(ft) ||
        (e.Layer || '').toLowerCase().includes(ft) || (e.Name || '').toLowerCase().includes(ft)
    );
    if (fl) filtered = filtered.filter(e => e.Layer === fl);

    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">No hay entidades disponibles</div>';
        return;
    }

    const groups = {};
    filtered.forEach(e => { const t = e.ObjectType || '?'; if (!groups[t]) groups[t] = []; groups[t].push(e); });

    container.innerHTML = '';
    Object.keys(groups).sort().forEach(type => {
        const items = groups[type];
        container.appendChild(createAccordionSection(`🔹 ${type}`, `${items.length}`, makeEntityTable(items)));
    });
}

function makeEntityTable(items) {
    const t = document.createElement('table');
    t.innerHTML = '<thead><tr><th>Handle</th><th>Capa</th><th>Color</th><th>Longitud</th><th>Área</th></tr></thead><tbody></tbody>';
    const tb = t.querySelector('tbody');
    items.forEach(e => {
        const r = document.createElement('tr');
        const ch = getColorHex(e.Color);
        r.innerHTML = `<td class="mono">${esc(e.Handle || '')}</td><td>${esc(e.Layer || '')}</td><td><span class="color-preview" style="background-color:${ch}"></span> ${esc(String(e.Color || ''))}</td><td class="num">${fmtNum(e.Length)}</td><td class="num">${fmtNum(e.Area)}</td>`;
        tb.appendChild(r);
    });
    return t;
}

function renderLayers() {
    const container = document.getElementById('layers-container');
    if (!container) return;
    const ft = (document.getElementById('filter-layers')?.value || '').toLowerCase();
    const filtered = layers.filter(l => l.Name.toLowerCase().includes(ft));

    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">No hay datos de capas disponibles</div>';
        return;
    }

    container.innerHTML = '';
    const t = document.createElement('table');
    t.innerHTML = '<thead><tr><th>Capa</th><th>Color</th><th>Estado</th><th>Entidades</th></tr></thead><tbody></tbody>';
    const tb = t.querySelector('tbody');
    filtered.forEach(l => {
        const r = document.createElement('tr');
        const ch = getColorHex(l.Color);
        r.innerHTML = `<td><strong>${esc(l.Name)}</strong></td><td><span class="color-preview" style="background-color:${ch}"></span> ${esc(String(l.Color || ''))}</td><td><span class="badge ${l.On ? 'visible' : 'hidden'}">${l.On ? 'Visible' : 'Oculta'}</span></td><td class="num">${l.ObjectCount || 0}</td>`;
        tb.appendChild(r);
    });
    container.appendChild(t);
}

function renderBlocks() {
    const container = document.getElementById('blocks-container');
    if (!container) return;
    const ft = (document.getElementById('filter-blocks')?.value || '').toLowerCase();
    const filtered = blocks.filter(b => b.Name.toLowerCase().includes(ft));

    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">No hay bloques disponibles</div>';
        return;
    }

    container.innerHTML = '';
    filtered.forEach(b => {
        const body = document.createElement('div');
        body.className = 'block-detail';
        body.innerHTML = `<div><strong>Instancias:</strong> ${b.Count || 0} · <strong>Entidades:</strong> ${b.ObjectCount || 0}</div>`;
        container.appendChild(createAccordionSection(`📦 ${b.Name}`, `${b.Count || 0}`, body));
    });
}

// ========================
// Components
// ========================

function createAccordionSection(title, badge, contentEl) {
    const s = document.createElement('div');
    s.className = 'accordion-section';
    const h = document.createElement('div');
    h.className = 'accordion-header';
    h.innerHTML = `<span class="accordion-arrow">▶</span><span class="accordion-title">${title}</span><span class="accordion-badge">${badge}</span>`;
    const b = document.createElement('div');
    b.className = 'accordion-body';
    b.appendChild(contentEl);
    h.addEventListener('click', () => { h.classList.toggle('open'); b.classList.toggle('open'); });
    s.appendChild(h);
    s.appendChild(b);
    return s;
}

function toggleAllAccordions(id, expand) {
    const c = document.getElementById(id);
    if (!c) return;
    c.querySelectorAll('.accordion-header').forEach(h => h.classList.toggle('open', expand));
    c.querySelectorAll('.accordion-body').forEach(b => b.classList.toggle('open', expand));
}

// ========================
// Utils
// ========================

function addLog(msg, type = 'info') {
    const c = document.getElementById('console-output');
    if (!c) return;
    const e = document.createElement('div');
    e.className = `log-entry ${type}`;
    e.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    c.appendChild(e);
    c.scrollTop = c.scrollHeight;
}

function showToast(msg, type = 'success') {
    const t = document.getElementById('message-box');
    if (!t) return;
    t.textContent = msg;
    t.className = `toast show`;
    t.style.backgroundColor = type === 'success' ? '#10b981' : '#ef4444';
    setTimeout(() => { t.className = 'toast'; }, 3000);
}

function esc(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function fmtNum(val) {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return Number(val).toLocaleString('es-ES', { maximumFractionDigits: 2 });
}

function getColorHex(color) {
    const m = { white: '#fff', red: '#f00', yellow: '#ff0', green: '#0f0', cyan: '#0ff', blue: '#00f', magenta: '#f0f', black: '#000' };
    return m[String(color).toLowerCase()] || '#94a3b8';
}
