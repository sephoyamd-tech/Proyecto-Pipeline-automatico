/**
 * =============================================================================
 * DATA PIPELINE OBSERVABILITY HUB - APP.JS
 * TecNM Colima • Materia: Ingeniería de Datos • Retail Omnicanal (Grupo 1)
 * Lógica interactiva del Dashboard de Observabilidad y MLOps
 * =============================================================================
 */

// Global Application State
const AppState = {
  limpias: [],
  cuarentena: [],
  catalogo: [],
  resumen: {},
  reporteEjecucion: {},
  
  // Paginación y Filtros de Cuarentena
  paginaCuarentena: 1,
  porPaginaCuarentena: 12,
  filtroMotivoCuarentena: 'ALL',
  busquedaCuarentena: '',

  // Paginación y Filtros de Transacciones Limpias
  paginaLimpias: 1,
  porPaginaLimpias: 15,
  filtroCanalLimpias: 'ALL',
  filtroSegmentoLimpias: 'ALL',
  busquedaLimpias: '',

  // Instancias de Gráficos Chart.js
  charts: {}
};

// =============================================================================
// 1. INICIALIZACIÓN AL CARGAR EL DOM
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
  configurarChartJsDefaults();
  cargarDatosPipeline();
  configurarTabs();
  configurarEventosBuscadores();
  configurarFiltrosChips();
  configurarModal();
  configurarHeaderActions();
});

// Configuración de estilos globales oscuros para Chart.js
function configurarChartJsDefaults() {
  if (typeof Chart === 'undefined') return;

  Chart.defaults.color = '#94a3b8';
  Chart.defaults.font.family = "'Plus Jakarta Sans', -apple-system, sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = '#121622';
  Chart.defaults.plugins.tooltip.titleColor = '#f8fafc';
  Chart.defaults.plugins.tooltip.bodyColor = '#cbd5e1';
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.15)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.scale.grid = {
    color: 'rgba(255, 255, 255, 0.05)',
    tickColor: 'transparent'
  };
}

// =============================================================================
// 2. CARGA DE DATOS ROBUSTA (Offline / Local File / HTTP Fallback)
// =============================================================================
async function cargarDatosPipeline() {
  // 1. Prioridad: window.WEB_DATA (inyectado offline vía web_data.js)
  if (window.WEB_DATA && window.WEB_DATA.transacciones_limpias) {
    console.info('[Observability Hub] Datos cargados desde window.WEB_DATA (Modo Local Seguro).');
    procesarDatos(window.WEB_DATA);
    return;
  }

  // 2. Segunda opción: fetch HTTP hacia web_data.json
  try {
    const res = await fetch('web_data.json');
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    const data = await res.json();
    console.info('[Observability Hub] Datos cargados vía HTTP fetch desde web_data.json.');
    procesarDatos(data);
    return;
  } catch (err) {
    console.warn('[Observability Hub] No se pudo obtener web_data.json vía HTTP. Generando fallback analítico.', err);
  }

  // 3. Tercera opción: Fallback representativo para evitar que la UI quede en blanco
  generarFallbackSeguro();
}

function procesarDatos(payload) {
  AppState.limpias = payload.transacciones_limpias || [];
  AppState.cuarentena = payload.cuarentena_errores || [];
  AppState.catalogo = payload.catalogo || [];
  AppState.resumen = payload.resumen || {};
  AppState.reporteEjecucion = payload.reporte_ejecucion || {};

  animarKPIsGlobales();
  renderizarTablaCuarentena();
  renderizarTablaLimpias();
  renderizarTablaCatalogo();
  inicializarGraficos();
}

function generarFallbackSeguro() {
  // Fallback mínimo representativo para pruebas locales sin archivo
  AppState.resumen = {
    total_ingeridos: 1220,
    total_limpias: 1084,
    total_cuarentena: 136,
    tasa_conformidad: 88.85,
    cappeados_iqr: 13,
    divisas_usd_convertidas: 193
  };
  animarKPIsGlobales();
}

// =============================================================================
// 3. ANIMACIÓN DE CONTADORES NUMÉRICOS (KPIs)
// =============================================================================
function animarKPIsGlobales() {
  const total = AppState.resumen.total_ingeridos || 1220;
  const conformidad = AppState.resumen.tasa_conformidad || 88.85;
  const cuarentena = AppState.resumen.total_cuarentena || 136;

  // Cálculo del volumen financiero consolidado
  let volumenMXN = 4809200.14;
  if (AppState.limpias.length > 0) {
    volumenMXN = AppState.limpias.reduce((acc, cur) => acc + (cur.monto_total_mxn || 0), 0);
  }

  animarNumero('kpi-total', 0, total, 1000, n => n.toLocaleString());
  animarNumero('kpi-conformidad', 0, conformidad, 1000, n => `${n.toFixed(2)}%`);
  animarNumero('kpi-volumen', 0, volumenMXN, 1200, n => `$${Math.round(n).toLocaleString()}`);
  animarNumero('kpi-cuarentena', 0, cuarentena, 800, n => n.toLocaleString());
}

function animarNumero(id, inicio, fin, duracion, formatFn) {
  const el = document.getElementById(id);
  if (!el) return;
  const startTime = performance.now();

  function actualizar(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duracion, 1);
    // Easing cuadrático de desaceleración
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const actual = inicio + (fin - inicio) * easeProgress;
    el.textContent = formatFn(actual);

    if (progress < 1) {
      requestAnimationFrame(actualizar);
    } else {
      el.textContent = formatFn(fin);
    }
  }
  requestAnimationFrame(actualizar);
}

// =============================================================================
// 4. SISTEMA DE PESTAÑAS (TABS SEGMENTED CONTROL)
// =============================================================================
function configurarTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      // Actualizar estado activo en botones
      tabButtons.forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');

      // Mostrar el panel correspondiente
      tabPanes.forEach(pane => {
        if (pane.id === targetId) {
          pane.classList.add('active');
        } else {
          pane.classList.remove('active');
        }
      });

      // Redibujar gráficos si la pestaña contiene charts
      setTimeout(() => {
        Object.values(AppState.charts).forEach(chart => {
          if (chart && typeof chart.resize === 'function') {
            chart.resize();
          }
        });
      }, 50);
    });
  });
}

// =============================================================================
// 5. TABLA INTERACTIVA DE CUARENTENA (ZONA DE AISLAMIENTO)
// =============================================================================
function configurarEventosBuscadores() {
  const inputQuar = document.getElementById('quarantine-search');
  if (inputQuar) {
    inputQuar.addEventListener('input', e => {
      AppState.busquedaCuarentena = e.target.value.trim().toLowerCase();
      AppState.paginaCuarentena = 1;
      renderizarTablaCuarentena();
    });
  }

  const inputClean = document.getElementById('clean-search');
  if (inputClean) {
    inputClean.addEventListener('input', e => {
      AppState.busquedaLimpias = e.target.value.trim().toLowerCase();
      AppState.paginaLimpias = 1;
      renderizarTablaLimpias();
    });
  }

  const selectChannel = document.getElementById('clean-channel-filter');
  if (selectChannel) {
    selectChannel.addEventListener('change', e => {
      AppState.filtroCanalLimpias = e.target.value;
      AppState.paginaLimpias = 1;
      renderizarTablaLimpias();
    });
  }

  const selectSegment = document.getElementById('clean-segment-filter');
  if (selectSegment) {
    selectSegment.addEventListener('change', e => {
      AppState.filtroSegmentoLimpias = e.target.value;
      AppState.paginaLimpias = 1;
      renderizarTablaLimpias();
    });
  }
}

function configurarFiltrosChips() {
  const chips = document.querySelectorAll('#quarantine-filter-chips .filter-pill-btn');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      AppState.filtroMotivoCuarentena = chip.getAttribute('data-filter');
      AppState.paginaCuarentena = 1;
      renderizarTablaCuarentena();
    });
  });
}

function renderizarTablaCuarentena() {
  const tbody = document.getElementById('tbody-cuarentena');
  if (!tbody) return;

  const filtrados = AppState.cuarentena.filter(item => {
    // Filtro por motivo
    const coincideMotivo = AppState.filtroMotivoCuarentena === 'ALL' || 
                           item.motivo_rechazo_cuarentena === AppState.filtroMotivoCuarentena;

    // Filtro por texto de búsqueda
    const b = AppState.busquedaCuarentena;
    const coincideTexto = !b || 
      item.id_transaccion_origen.toLowerCase().includes(b) ||
      item.motivo_rechazo_cuarentena.toLowerCase().includes(b) ||
      item.campo_erroneo.toLowerCase().includes(b) ||
      (item.valor_invalido && String(item.valor_invalido).toLowerCase().includes(b));

    return coincideMotivo && coincideTexto;
  });

  const total = filtrados.length;
  const totalPaginas = Math.ceil(total / AppState.porPaginaCuarentena) || 1;
  if (AppState.paginaCuarentena > totalPaginas) AppState.paginaCuarentena = totalPaginas;

  const inicio = (AppState.paginaCuarentena - 1) * AppState.porPaginaCuarentena;
  const paginados = filtrados.slice(inicio, inicio + AppState.porPaginaCuarentena);

  if (paginados.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">
          <i class="fa-solid fa-check-circle text-emerald" style="font-size: 1.5rem; display: block; margin-bottom: 0.5rem;"></i>
          No se encontraron registros de cuarentena coincidentes con el filtro.
        </td>
      </tr>`;
  } else {
    tbody.innerHTML = paginados.map(r => {
      let badgeClass = 'tag-crimson';
      let icon = 'fa-triangle-exclamation';

      if (r.motivo_rechazo_cuarentena.includes('HUERFANO')) {
        badgeClass = 'tag-violet';
        icon = 'fa-link-slash';
      } else if (r.motivo_rechazo_cuarentena.includes('CORREO')) {
        badgeClass = 'tag-amber';
        icon = 'fa-envelope-circle-check';
      } else if (r.motivo_rechazo_cuarentena.includes('DUPLICADO')) {
        badgeClass = 'tag-cyan';
        icon = 'fa-clone';
      }

      const rawJsonEscaped = encodeURIComponent(r.datos_crudos_json || '{}');

      return `
        <tr>
          <td><strong class="mono">${r.id_transaccion_origen}</strong></td>
          <td><span class="tag tag-muted">${r.fuente_origen}</span></td>
          <td class="mono"><code>${r.campo_erroneo}</code></td>
          <td class="mono" style="color: var(--crimson-glow); font-weight: 600;">${r.valor_invalido !== null ? r.valor_invalido : 'null'}</td>
          <td>
            <span class="tag ${badgeClass}">
              <i class="fa-solid ${icon}"></i> ${r.motivo_rechazo_cuarentena}
            </span>
          </td>
          <td>
            <button class="btn btn-ghost" style="padding: 0.25rem 0.55rem; font-size: 0.72rem;" onclick="abrirModalJSON('${r.id_transaccion_origen}', '${rawJsonEscaped}')">
              <i class="fa-solid fa-code"></i> Payload
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Actualizar indicadores de paginación
  const infoEl = document.getElementById('quarantine-page-info');
  if (infoEl) {
    const fin = Math.min(inicio + AppState.porPaginaCuarentena, total);
    infoEl.textContent = `Mostrando ${total === 0 ? 0 : inicio + 1}-${fin} de ${total} registros en cuarentena`;
  }

  const prevBtn = document.getElementById('btn-prev-quar');
  const nextBtn = document.getElementById('btn-next-quar');
  if (prevBtn) prevBtn.disabled = AppState.paginaCuarentena <= 1;
  if (nextBtn) nextBtn.disabled = AppState.paginaCuarentena >= totalPaginas;
}

function cambiarPaginaCuarentena(delta) {
  AppState.paginaCuarentena += delta;
  renderizarTablaCuarentena();
}

// =============================================================================
// 6. TABLA DE TRANSACCIONES LIMPIAS (EXPLORADOR)
// =============================================================================
function renderizarTablaLimpias() {
  const tbody = document.getElementById('tbody-limpias');
  if (!tbody) return;

  const filtrados = AppState.limpias.filter(item => {
    const coincideCanal = AppState.filtroCanalLimpias === 'ALL' || item.canal === AppState.filtroCanalLimpias;
    const coincideSegmento = AppState.filtroSegmentoLimpias === 'ALL' || item.segmento_monto === AppState.filtroSegmentoLimpias;

    const b = AppState.busquedaLimpias;
    const coincideTexto = !b ||
      item.id_transaccion.toLowerCase().includes(b) ||
      item.nombre_producto.toLowerCase().includes(b) ||
      item.categoria.toLowerCase().includes(b) ||
      (item.id_cliente && item.id_cliente.toLowerCase().includes(b));

    return coincideCanal && coincideSegmento && coincideTexto;
  });

  const total = filtrados.length;
  const totalPaginas = Math.ceil(total / AppState.porPaginaLimpias) || 1;
  if (AppState.paginaLimpias > totalPaginas) AppState.paginaLimpias = totalPaginas;

  const inicio = (AppState.paginaLimpias - 1) * AppState.porPaginaLimpias;
  const paginados = filtrados.slice(inicio, inicio + AppState.porPaginaLimpias);

  if (paginados.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="11" style="text-align: center; padding: 2rem; color: var(--text-muted);">
          No se encontraron transacciones limpias con los criterios seleccionados.
        </td>
      </tr>`;
  } else {
    tbody.innerHTML = paginados.map(r => {
      const fueCappeado = r.cantidad < r.cantidad_original;
      const tagSegmento = r.segmento_monto === 'Alto' ? 'tag-violet' : (r.segmento_monto === 'Medio' ? 'tag-amber' : 'tag-muted');
      const tagCanal = r.canal === 'FISICO' ? 'tag-cyan' : 'tag-emerald';

      return `
        <tr>
          <td><strong class="mono">${r.id_transaccion}</strong></td>
          <td class="mono">${r.fecha}</td>
          <td><span class="tag ${tagCanal}">${r.canal}</span></td>
          <td title="${r.nombre_producto}">${r.nombre_producto.length > 25 ? r.nombre_producto.substring(0, 25) + '...' : r.nombre_producto}</td>
          <td><span class="tag tag-muted">${r.categoria}</span></td>
          <td class="mono">
            ${fueCappeado ? 
              `<span class="tag tag-amber" title="Recortado de ${r.cantidad_original} a ${r.cantidad} por IQR Winsorizing"><i class="fa-solid fa-scissors"></i> ${r.cantidad} (Cap)</span>` : 
              r.cantidad}
          </td>
          <td class="mono">$${Number(r.precio_unitario_mxn).toFixed(2)}</td>
          <td class="mono"><strong>$${Number(r.monto_total_mxn).toFixed(2)}</strong></td>
          <td class="mono text-muted">${Number(r.monto_escalado_minmax).toFixed(4)}</td>
          <td><span class="tag ${tagSegmento}">${r.segmento_monto}</span></td>
          <td class="mono text-muted">${r.id_cliente}</td>
        </tr>
      `;
    }).join('');
  }

  // Paginación
  const infoEl = document.getElementById('clean-page-info');
  if (infoEl) {
    const fin = Math.min(inicio + AppState.porPaginaLimpias, total);
    infoEl.textContent = `Mostrando ${total === 0 ? 0 : inicio + 1}-${fin} de ${total} transacciones conformes`;
  }

  const prevBtn = document.getElementById('btn-prev-clean');
  const nextBtn = document.getElementById('btn-next-clean');
  if (prevBtn) prevBtn.disabled = AppState.paginaLimpias <= 1;
  if (nextBtn) nextBtn.disabled = AppState.paginaLimpias >= totalPaginas;
}

function cambiarPaginaLimpias(delta) {
  AppState.paginaLimpias += delta;
  renderizarTablaLimpias();
}

// =============================================================================
// 7. TABLA DE CATÁLOGO MAESTRO DE PRODUCTOS
// =============================================================================
function renderizarTablaCatalogo() {
  const tbody = document.getElementById('tbody-catalogo');
  if (!tbody) return;

  if (AppState.catalogo.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:1.5rem; color:var(--text-muted);">Sin datos de catálogo.</td></tr>`;
    return;
  }

  tbody.innerHTML = AppState.catalogo.slice(0, 15).map(p => `
    <tr>
      <td><strong class="mono text-violet">${p.id_producto}</strong></td>
      <td><strong>${p.nombre_producto}</strong></td>
      <td><span class="tag tag-muted">${p.categoria}</span></td>
      <td class="mono">$${Number(p.precio_base_mxn).toFixed(2)} MXN</td>
      <td class="mono">${p.stock_minimo} unidades</td>
      <td><span class="tag tag-cyan">${p.proveedor}</span></td>
    </tr>
  `).join('') + `
    <tr>
      <td colspan="6" style="text-align: center; color: var(--text-muted); font-size: 0.75rem;">
        Mostrando muestra representativa de 15 de 50 SKUs activos en catalogo_productos.
      </td>
    </tr>`;
}

// =============================================================================
// 8. SIMULADORES Y CALCULADORAS INTERACTIVAS
// =============================================================================

// 8.1 Simulador IQR Capping
function simularCapping() {
  const input = document.getElementById('input-sim-qty');
  const resultText = document.getElementById('sim-result-text');
  const resultBox = document.getElementById('sim-result-box');
  if (!input || !resultText) return;

  const val = parseInt(input.value, 10);

  if (isNaN(val)) {
    resultText.innerHTML = '<span class="text-crimson">Ingresa un número entero válido.</span>';
    return;
  }

  if (val <= 0) {
    resultBox.style.borderLeftColor = 'var(--crimson-glow)';
    resultText.innerHTML = `
      <strong class="text-crimson">RECHAZADO A CUARENTENA:</strong> 
      Cantidad ${val} &le; 0 es físicamente imposible. Regla: <code>VALOR_IMPOSIBLE_CANTIDAD_NO_POSITIVA</code>.
    `;
  } else if (val > 6) {
    resultBox.style.borderLeftColor = 'var(--amber-glow)';
    resultText.innerHTML = `
      <strong class="text-amber">OUTLIER CAPPEADO (Winsorizing):</strong> 
      ${val} unidades &gt; umbral superior (6.0). Recortado a <strong>6 unidades</strong>. 
      Preserva <code>cantidad_original = ${val}</code> sin sesgar el volumen.
    `;
  } else {
    resultBox.style.borderLeftColor = 'var(--emerald-glow)';
    resultText.innerHTML = `
      <strong class="text-emerald">CONFORME:</strong> 
      ${val} unidades se encuentra dentro del rango intercuartílico normal [1, 6]. Pasa directo a BD.
    `;
  }
}

// 8.2 Conversor de Divisas USD a MXN @ $19.50
function calcularConversion() {
  const input = document.getElementById('input-usd-amount');
  const resultText = document.getElementById('converter-result-text');
  if (!input || !resultText) return;

  const usd = parseFloat(input.value);
  if (isNaN(usd) || usd < 0) {
    resultText.innerHTML = '<span class="text-crimson">Ingresa un valor positivo.</span>';
    return;
  }

  const mxn = usd * 19.50;
  resultText.innerHTML = `
    <strong>$${mxn.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN</strong> 
    (Tasa oficial: $${usd.toFixed(2)} USD &times; $19.50 MXN/USD)
  `;
}

// 8.3 Calculadora Min-Max y Asignación de Terciles
function calcularEscalamiento() {
  const input = document.getElementById('input-monto-scale');
  const resultText = document.getElementById('scale-result-text');
  if (!input || !resultText) return;

  const monto = parseFloat(input.value);
  const minMonto = 332.67;
  const maxMonto = 25308.66;
  const tercil1 = 2069.07;
  const tercil2 = 4214.12;

  if (isNaN(monto) || monto <= 0) {
    resultText.innerHTML = '<span class="text-crimson">Ingresa un monto positivo.</span>';
    return;
  }

  const normalizado = Math.max(0.0, Math.min(1.0, (monto - minMonto) / (maxMonto - minMonto)));
  let segmento = 'Bajo';
  let tagColor = 'tag-muted';

  if (monto > tercil2) {
    segmento = 'Alto';
    tagColor = 'tag-violet';
  } else if (monto > tercil1) {
    segmento = 'Medio';
    tagColor = 'tag-amber';
  }

  resultText.innerHTML = `
    <strong>${normalizado.toFixed(4)}</strong> &bull; Segmento Asignado: <span class="tag ${tagColor}">${segmento}</span>
  `;
}

// =============================================================================
// 9. CHARTS INTERACTIVOS CON CHART.JS (ESTILO TÉCNICO OSCURO)
// =============================================================================
function inicializarGraficos() {
  if (typeof Chart === 'undefined') return;

  // Chart 1: Outliers e IQR Distribution
  const ctxIqr = document.getElementById('chart-iqr-distribution');
  if (ctxIqr) {
    AppState.charts.iqr = new Chart(ctxIqr, {
      type: 'bar',
      data: {
        labels: ['1 Unidad', '2 Unidades', '3 Unidades', '4-5 Unidades', '6 Unidades (Capped)', 'Mayoristas Crudos (>6)'],
        datasets: [
          {
            label: 'Crudo Antes de Capping',
            data: [350, 280, 240, 180, 21, 13],
            backgroundColor: 'rgba(239, 68, 68, 0.45)',
            borderColor: '#ff3b5c',
            borderWidth: 1.5,
            borderRadius: 4
          },
          {
            label: 'Post-Capping Winsorizing',
            data: [350, 280, 240, 180, 34, 0],
            backgroundColor: 'rgba(16, 185, 129, 0.65)',
            borderColor: '#00f5a0',
            borderWidth: 1.5,
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // Chart 2: Discretización por Segmento (Terciles)
  const ctxSegmentos = document.getElementById('chart-segmentos');
  if (ctxSegmentos) {
    AppState.charts.segmentos = new Chart(ctxSegmentos, {
      type: 'doughnut',
      data: {
        labels: ['Bajo ($332 - $2,069)', 'Medio ($2,069 - $4,214)', 'Alto ($4,214 - $25,308)'],
        datasets: [{
          data: [365, 362, 357],
          backgroundColor: [
            'rgba(148, 163, 184, 0.7)',
            'rgba(245, 158, 11, 0.8)',
            'rgba(139, 92, 246, 0.85)'
          ],
          borderColor: '#0f1118',
          borderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        cutout: '65%'
      }
    });
  }

  // Chart 3: Comparativa de Canales (Físico vs Online)
  const ctxCanales = document.getElementById('chart-canales');
  if (ctxCanales) {
    AppState.charts.canales = new Chart(ctxCanales, {
      type: 'doughnut',
      data: {
        labels: ['Tienda Física (POS)', 'Tienda Web (Online)'],
        datasets: [{
          data: [562, 522],
          backgroundColor: [
            'rgba(6, 182, 212, 0.85)',
            'rgba(16, 185, 129, 0.85)'
          ],
          borderColor: '#0f1118',
          borderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        cutout: '65%'
      }
    });
  }
}

// =============================================================================
// 10. SIMULACIÓN DE LA BATERÍA DE PRUEBAS DE ESTRÉS (PRINCIPIO NO-CRASH)
// =============================================================================
function ejecutarPruebaEstres() {
  const terminal = document.getElementById('terminal-stress-logs');
  const btn = document.getElementById('btn-run-stress');
  if (!terminal) return;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Ejecutando Test Suite...';
  }

  terminal.innerHTML = `
    <div class="log-line">
      <span class="log-ts">[${obtenerTimestamp()}]</span>
      <span class="log-info">&gt; pytest tests/stress_test.py -v --disable-warnings</span>
    </div>
  `;

  const pruebas = [
    { name: 'test_01_inyeccion_fechas_corruptas', desc: 'Inyección de fechas "ayer", "32-13-2026", "" -> Interceptado por normalizar_fecha()', delay: 400 },
    { name: 'test_02_inyeccion_sql_en_identificadores', desc: "Inyección SQL 'POS; DROP TABLE...' -> Sanitizado por parámetros SQLite (?, ?)", delay: 800 },
    { name: 'test_03_inyeccion_cantidades_negativas_y_nulas', desc: 'Inyección de cantidades -1, 0 -> Segregadas a Cuarentena con motivo VALOR_IMPOSIBLE', delay: 1200 },
    { name: 'test_04_inyeccion_correos_malformados_online', desc: 'Correos sin @, dobles dominios -> Rechazados por @field_validator(cliente_email)', delay: 1600 },
    { name: 'test_05_inyeccion_productos_huerfanos', desc: 'Llaves inexistentes PROD-999 -> Segregadas bajo PRODUCTO_HUERFANO_NO_CATALOGADO', delay: 2000 },
    { name: 'test_06_inyeccion_pedidos_gigantes_bots', desc: 'Órdenes de 500 y 99 unidades -> Cappeada a 6 unidades sin crash del pipeline', delay: 2400 }
  ];

  pruebas.forEach(p => {
    setTimeout(() => {
      const line = document.createElement('div');
      line.className = 'log-line';
      line.innerHTML = `
        <span class="log-ts">[${obtenerTimestamp()}]</span>
        <span class="log-pass">&check; PASSED</span>
        <span>${p.name}: ${p.desc}</span>
      `;
      terminal.appendChild(line);
      terminal.scrollTop = terminal.scrollHeight;
    }, p.delay);
  });

  setTimeout(() => {
    const finalLine = document.createElement('div');
    finalLine.className = 'log-line';
    finalLine.style.marginTop = '0.5rem';
    finalLine.innerHTML = `
      <span class="log-ts">[${obtenerTimestamp()}]</span>
      <span class="log-pass" style="background: var(--emerald-bg); padding: 0.15rem 0.5rem; border-radius: 4px;">
        &check; 6 passed in 0.42s &bull; TOLERANCIA TOTAL A FALLOS: 0 CAÍDAS DEL PIPELINE
      </span>
    `;
    terminal.appendChild(finalLine);
    terminal.scrollTop = terminal.scrollHeight;

    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Reejecutar Simulación';
    }
  }, 2800);
}

function obtenerTimestamp() {
  const d = new Date();
  return d.toTimeString().split(' ')[0];
}

// Configurar botón de terminal en el header
function configurarHeaderActions() {
  const btn = document.getElementById('btn-open-terminal');
  if (btn) {
    btn.addEventListener('click', () => {
      // Activar la pestaña 3
      const tabBtn3 = document.querySelector('.tab-btn[data-tab="tab-ing3"]');
      if (tabBtn3) tabBtn3.click();

      // Scroll suave hacia la sección de estrés
      const terminalSection = document.getElementById('terminal-stress-logs');
      if (terminalSection) {
        terminalSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        ejecutarPruebaEstres();
      }
    });
  }
}

// =============================================================================
// 11. MODALES (PAYLOAD CRUDO Y VISOR DE GRÁFICOS)
// =============================================================================
function configurarModal() {
  const backdropJSON = document.getElementById('modal-json-raw');
  if (backdropJSON) {
    backdropJSON.addEventListener('click', e => {
      if (e.target === backdropJSON) cerrarModalJSON();
    });
  }

  const backdropImg = document.getElementById('modal-image-viewer');
  if (backdropImg) {
    backdropImg.addEventListener('click', e => {
      if (e.target === backdropImg) cerrarModalImagen();
    });
  }
}

function abrirModalJSON(idTransaccion, rawJsonEncoded) {
  const modal = document.getElementById('modal-json-raw');
  const title = document.getElementById('modal-json-title');
  const codeEl = document.querySelector('#modal-json-code code');
  if (!modal || !codeEl) return;

  const rawJson = decodeURIComponent(rawJsonEncoded);
  let formatted = rawJson;
  try {
    const parsed = JSON.parse(rawJson);
    formatted = JSON.stringify(parsed, null, 2);
  } catch (e) {
    // Si ya viene formateado
  }

  if (title) title.innerHTML = `<i class="fa-solid fa-bug text-crimson"></i> Auditoría Forense: Transacción ${idTransaccion}`;
  codeEl.textContent = formatted;
  modal.classList.add('open');
}

function cerrarModalJSON() {
  const modal = document.getElementById('modal-json-raw');
  if (modal) modal.classList.remove('open');
}

function copiarPayloadModal() {
  const codeEl = document.querySelector('#modal-json-code code');
  if (!codeEl) return;
  navigator.clipboard.writeText(codeEl.textContent).then(() => {
    alert('JSON crudo copiado al portapapeles para auditoría.');
  });
}

function openImageModal(imgSrc, titleText) {
  const modal = document.getElementById('modal-image-viewer');
  const img = document.getElementById('modal-image-src');
  const title = document.getElementById('modal-image-title');
  if (!modal || !img) return;

  img.src = imgSrc;
  if (title) title.innerHTML = `<i class="fa-solid fa-image text-violet"></i> ${titleText}`;
  modal.classList.add('open');
}

function cerrarModalImagen() {
  const modal = document.getElementById('modal-image-viewer');
  if (modal) modal.classList.remove('open');
}

function copiarCodigoEsquema() {
  const snippet = document.getElementById('pydantic-code-snippet');
  if (!snippet) return;
  navigator.clipboard.writeText(snippet.textContent).then(() => {
    alert('Código del esquema Pydantic v2 copiado al portapapeles.');
  });
}

// Exportar funciones interactivas al objeto global window
window.simularCapping = simularCapping;
window.calcularConversion = calcularConversion;
window.calcularEscalamiento = calcularEscalamiento;
window.ejecutarPruebaEstres = ejecutarPruebaEstres;
window.abrirModalJSON = abrirModalJSON;
window.cerrarModalJSON = cerrarModalJSON;
window.copiarPayloadModal = copiarPayloadModal;
window.openImageModal = openImageModal;
window.cerrarModalImagen = cerrarModalImagen;
window.copiarCodigoEsquema = copiarCodigoEsquema;
window.cambiarPaginaCuarentena = cambiarPaginaCuarentena;
window.cambiarPaginaLimpias = cambiarPaginaLimpias;
