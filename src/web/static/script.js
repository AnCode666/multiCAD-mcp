// Dashboard State
let activeTab = 'overview';
let cadStatus = { connected: false, cad_type: 'None', drawings: [], current_drawing: 'None' };
let layers = [];
let blocks = [];

// DOM Elements
const navButtons = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');
const connectionIndicator = document.querySelector('.status-indicator');
const connectionText = document.querySelector('.status-text');
const cadTypeDisplay = document.getElementById('cad-type-display');
const drawingsCount = document.getElementById('drawings-count');
const currentDrawingName = document.getElementById('current-drawing-name');
const currentDrawingPath = document.getElementById('current-drawing-path');
const refreshBtn = document.getElementById('refresh-all');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    refreshData();
    // Auto-refresh every 10 seconds
    setInterval(refreshData, 10000);
});

function setupEventListeners() {
    // Tab Switching
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            switchTab(tabId);
        });
    });

    // Refresh button
    refreshBtn.addEventListener('click', refreshData);

    // Filters
    document.getElementById('filter-layers').addEventListener('input', (e) => {
        renderLayersTable(e.target.value);
    });

    document.getElementById('filter-blocks').addEventListener('input', (e) => {
        renderBlocksGrid(e.target.value);
    });
}

function switchTab(tabId) {
    activeTab = tabId;

    // Update active button
    navButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update active content
    tabContents.forEach(content => {
        if (content.id === `tab-${tabId}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });

    addLog(`Cambiado a pestaña: ${tabId}`, 'system');
}

async function refreshData() {
    addLog('Refrescando datos...', 'system');

    try {
        await Promise.all([
            fetchStatus(),
            fetchLayers(),
            fetchBlocks()
        ]);

        updateUI();
        addLog('Datos actualizados correctamente.', 'info');
    } catch (error) {
        console.error('Error refreshing data:', error);
        addLog(`Error al refrescar: ${error.message}`, 'error');
        showToast('Error al conectar con el servidor', 'error');
    }
}

async function fetchStatus() {
    const response = await fetch('/api/cad/status');
    cadStatus = await response.json();
}

async function fetchLayers() {
    const response = await fetch('/api/cad/layers');
    const result = await response.json();
    if (result.success) {
        layers = result.layers;
        document.getElementById('total-layers-count').textContent = layers.length;
    }
}

async function fetchBlocks() {
    const response = await fetch('/api/cad/blocks');
    const result = await response.json();
    if (result.success && result.blocks) {
        blocks = result.blocks;
        document.getElementById('total-blocks-count').textContent = blocks.length;
    }
}

function updateUI() {
    // Update Connection Stats
    if (cadStatus.connected) {
        connectionIndicator.className = 'status-indicator green';
        connectionText.textContent = `Conectado a ${cadStatus.cad_type}`;
        cadTypeDisplay.textContent = cadStatus.cad_type;
        drawingsCount.textContent = cadStatus.drawings.length;
        currentDrawingName.textContent = cadStatus.current_drawing;
        currentDrawingPath.textContent = 'Activo';
    } else {
        connectionIndicator.className = 'status-indicator red';
        connectionText.textContent = 'Desconectado';
        cadTypeDisplay.textContent = 'Ninguno';
        drawingsCount.textContent = '0';
        currentDrawingName.textContent = 'No hay dibujos activos';
        currentDrawingPath.textContent = 'Conéctate a través de MCP';
    }

    // Render components
    renderLayersTable();
    renderBlocksGrid();
}

function renderLayersTable(filter = '') {
    const tbody = document.querySelector('#layers-table tbody');
    tbody.innerHTML = '';

    const sortedLayers = layers.filter(l =>
        l.Name.toLowerCase().includes(filter.toLowerCase())
    );

    if (sortedLayers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No se encontraron capas</td></tr>';
        return;
    }

    sortedLayers.forEach(layer => {
        const row = document.createElement('tr');

        // Color bubble
        const colorStyle = `background-color: ${getColorHex(layer.Color)}`;

        row.innerHTML = `
            <td><span class="layer-name" style="font-weight: 600;">${layer.Name}</span></td>
            <td><span class="color-preview" style="${colorStyle}"></span> ${layer.Color}</td>
            <td>
                <span class="badge ${layer.IsVisible ? 'visible' : 'hidden'}">
                    ${layer.IsVisible ? '👁️ Visible' : '🌑 Oculta'}
                </span>
                ${layer.IsLocked ? '🔒 Bloqueada' : ''}
            </td>
            <td>${layer.ObjectCount}</td>
        `;
        tbody.appendChild(row);
    });
}

function renderBlocksGrid(filter = '') {
    const container = document.getElementById('blocks-container');
    container.innerHTML = '';

    const filteredBlocks = blocks.filter(b =>
        b.Name.toLowerCase().includes(filter.toLowerCase())
    );

    if (filteredBlocks.length === 0) {
        container.innerHTML = '<div class="empty-state" style="grid-column: 1/-1">No se encontraron bloques</div>';
        return;
    }

    filteredBlocks.forEach(block => {
        const card = document.createElement('div');
        card.className = 'block-card';
        card.innerHTML = `
            <span class="block-name">${block.Name}</span>
            <div class="block-count">
                ${block.ReferenceCount} instancias | ${block.ObjectCount} entidades
            </div>
        `;
        container.appendChild(card);
    });
}

function addLog(message, type = 'info') {
    const consoleOutput = document.getElementById('console-output');
    const entry = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString();
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${timestamp}] ${message}`;

    consoleOutput.appendChild(entry);
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('message-box');
    toast.textContent = message;
    toast.style.display = 'block';
    toast.style.backgroundColor = type === 'success' ? '#10b981' : '#ef4444';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Utility to convert common CAD colors to HEX
function getColorHex(color) {
    const colors = {
        'white': '#ffffff',
        'red': '#ff0000',
        'yellow': '#ffff00',
        'green': '#00ff00',
        'cyan': '#00ffff',
        'blue': '#0000ff',
        'magenta': '#ff00ff',
        'black': '#000000'
    };
    return colors[color.toLowerCase()] || '#94a3b8';
}
