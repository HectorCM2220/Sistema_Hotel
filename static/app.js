document.addEventListener('DOMContentLoaded', () => {
    const inicioInput = document.getElementById('inp-inicio');
    const finInput = document.getElementById('inp-fin');
    const tipoInput = document.getElementById('inp-tipo');
    
    // Configurar fechas iniciales: hoy y mañana
    const hoy = new Date();
    const mañana = new Date(hoy);
    mañana.setDate(hoy.getDate() + 1);
    
    inicioInput.value = hoy.toISOString().split('T')[0];
    finInput.value = mañana.toISOString().split('T')[0];

    fetchEstado();

    // Eventos de cambio de fecha
    [inicioInput, finInput].forEach(inp => {
        inp.addEventListener('change', () => {
            if (inicioInput.value >= finInput.value) {
                const newFin = new Date(inicioInput.value);
                newFin.setDate(newFin.getDate() + 1);
                finInput.value = newFin.toISOString().split('T')[0];
            }
            resetSelection();
            fetchEstado();
        });
    });

    // Sincronización: Si cambia el tipo, se limpia la habitación específica
    tipoInput.addEventListener('change', () => {
        const numHab = document.getElementById('inp-numero-habitacion').value;
        if (numHab) resetSelection();
        fetchEstado();
    });

    document.getElementById('reserva-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('cliente', document.getElementById('inp-cliente').value);
        formData.append('inicio', inicioInput.value);
        formData.append('fin', finInput.value);
        formData.append('tipo', tipoInput.value);
        
        const numHab = document.getElementById('inp-numero-habitacion').value;
        if (numHab) formData.append('numero_habitacion', numHab);

        try {
            const res = await fetch('/api/reservar', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok) {
                showToast(data.message, 'success');
                resetSelection();
                fetchEstado();
                e.target.reset();
                inicioInput.value = hoy.toISOString().split('T')[0];
                finInput.value = mañana.toISOString().split('T')[0];
            } else {
                showToast(data.detail, 'error');
            }
        } catch (err) { showToast('Error de red', 'error'); }
    });

    document.getElementById('undo-btn').addEventListener('click', async () => {
        try {
            const res = await fetch('/api/deshacer', { method: 'POST' });
            const data = await res.json();
            if (res.ok) { showToast(data.message, 'success'); fetchEstado(); }
            else showToast(data.detail, 'error');
        } catch (err) { showToast('Error de red', 'error'); }
    });

    document.getElementById('permanent-delete-btn').addEventListener('click', async () => {
        if (!confirm('¿Eliminar permanentemente? Esta acción es irreversible.')) return;
        try {
            const res = await fetch('/api/borrar_definitivo', { method: 'POST' });
            const data = await res.json();
            if (res.ok) { showToast(data.message, 'success'); fetchEstado(); }
            else showToast(data.detail, 'error');
        } catch (err) { showToast('Error de red', 'error'); }
    });

    // Búsqueda
    document.getElementById('btn-search').addEventListener('click', fetchSearch);
    document.getElementById('btn-clear-search').addEventListener('click', () => {
        document.getElementById('inp-search').value = '';
        document.getElementById('search-results').innerHTML = '';
    });
});

async function fetchSearch() {
    const query = document.getElementById('inp-search').value;
    if (!query) return;
    try {
        const res = await fetch(`/api/buscar?query=${query}`);
        const data = await res.json();
        renderSearchResults(data);
    } catch (err) { console.error('Error:', err); }
}

function renderSearchResults(results) {
    const container = document.getElementById('search-results');
    if (results.length === 0) {
        container.innerHTML = '<p class="empty">No se encontraron reservas.</p>';
        return;
    }
    container.innerHTML = results.map(r => `
        <div class="search-result-item">
            <div>
                <strong>${r.cliente}</strong> | Hab #${r.habitacion.numero}
                <br><small>${r.fecha_inicio} a ${r.fecha_fin}</small>
            </div>
            <span class="hab-type">${r.habitacion.tipo}</span>
        </div>
    `).join('');
}

async function fetchEstado() {
    const ini = document.getElementById('inp-inicio').value;
    const fin = document.getElementById('inp-fin').value;
    try {
        const res = await fetch(`/api/estado?inicio=${ini}&fin=${fin}`);
        const data = await res.json();
        renderHabitaciones(data.habitaciones);
        renderReservas(data.reservas);
        renderLogs(data.logs);
        updateUndo(data.deshacer_count);
    } catch (err) { console.error('Error:', err); }
}

function renderLogs(logs) {
    const container = document.getElementById('logs-list');
    if (!logs || logs.length === 0) {
        container.innerHTML = '<p class="empty">Sin actividad reciente.</p>';
        return;
    }
    container.innerHTML = logs.map(l => `
        <div class="log-entry">
            <span class="log-msg">• ${l.mensaje}</span>
        </div>
    `).join('');
}

function renderHabitaciones(habs) {
    const container = document.getElementById('hab-container');
    const tipoFiltro = document.getElementById('inp-tipo').value;

    container.innerHTML = habs.map(h => {
        const matchesFiltro = !tipoFiltro || h.tipo === tipoFiltro;
        const opacity = matchesFiltro ? 1 : 0.3;
        
        return `
            <div class="hab-card ${h.disponible ? 'disponible' : 'ocupada'}" 
                 style="opacity: ${opacity}"
                 ${h.disponible ? `onclick="selectRoom(${h.numero}, '${h.tipo}', ${h.precio_total})"` : ''}
                 id="hab-card-${h.numero}">
                <span class="hab-num">#${h.numero}</span>
                <span class="hab-type">${h.tipo}</span>
                <span class="hab-price">$${h.precio_total} total</span>
                <span class="hab-status">${h.disponible ? 'Libre' : 'Ocupada'}</span>
            </div>
        `;
    }).join('');
}

function selectRoom(num, tipo, precio) {
    // Sincronización: Si elijo habitación, limpio el filtro de tipo (o lo pongo en el tipo de la hab)
    const tipoInput = document.getElementById('inp-tipo');
    tipoInput.value = ""; // Limpiamos para que se vea toda la disponibilidad

    const previous = document.querySelector('.hab-card.selected');
    if (previous) previous.classList.remove('selected');

    const current = document.getElementById(`hab-card-${num}`);
    if (current) current.classList.add('selected');

    document.getElementById('inp-numero-habitacion').value = num;
    document.getElementById('room-selection-display').innerHTML = `<strong>#${num}</strong> (${tipo}) - $${precio}`;
}

function resetSelection() {
    document.getElementById('inp-numero-habitacion').value = '';
    document.getElementById('room-selection-display').innerText = 'Selecciona en el mapa';
    const sel = document.querySelector('.hab-card.selected');
    if (sel) sel.classList.remove('selected');
}

function renderReservas(reservas) {
    const container = document.getElementById('res-container');
    const deleteBtn = document.getElementById('permanent-delete-btn');
    
    if (reservas.length === 0) {
        container.innerHTML = '<p class="empty">No hay estancias programadas.</p>';
        deleteBtn.disabled = true;
        return;
    }
    
    deleteBtn.disabled = false;
    container.innerHTML = reservas.map((r, index) => `
        <div class="reserva-item ${index === 0 ? 'pila-top' : ''}">
            <div class="res-body">
                <strong>${r.cliente}</strong>
                <span>Hab ${r.habitacion.numero} (${r.habitacion.tipo})</span>
                <small>${r.fecha_inicio} al ${r.fecha_fin}</small>
            </div>
            ${index === 0 ? `<button class="btn-cancel" onclick="cancelarReservaLIFO()">Cancelar</button>` : ''}
        </div>
    `).join('');
}

async function cancelarReservaLIFO() {
    try {
        const res = await fetch(`/api/cancelar/lifo`, { method: 'POST' });
        const data = await res.json();
        if (res.ok) { showToast(data.message, 'success'); fetchEstado(); }
        else showToast(data.detail, 'error');
    } catch (err) { showToast('Error de red', 'error'); }
}

function updateUndo(count) {
    document.getElementById('undo-count').innerText = count;
    document.getElementById('undo-btn').disabled = count === 0;
}

function showToast(msg, type) {
    const container = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerText = msg;
    container.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}
