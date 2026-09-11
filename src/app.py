"""
Semáforo de Inversión Social · CDMX
Dashboard Interactivo para Toma de Decisiones en Infraestructura Social
Optimizada para Modo Claro, Navegación Intuitiva y Animaciones Suaves.

Ejecutar:
    streamlit run src/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que src/ esté en el path para imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine import (
    CATEGORIES,
    EDITION_YEARS,
    HORIZONS_YEARS,
    POBLACION_2020_ALCALDIA,
    build_dataset,
    get_zones_dataframe,
    ols_fit,
)

# ---------------------------------------------------------------------------
# 1. Configuración de página y estilos Light Mode
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Semáforo de Inversión Social · CDMX",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inyección de CSS para forzar Light Mode, tipografía refinada y micro-animaciones
CUSTOM_CSS = """
<style>
/* Forzar tema claro global y colores limpios */
:root {
    --bg-page: #F8FAF9;
    --bg-surface: #FFFFFF;
    --border-soft: #E2E8F0;
    --border-strong: #CBD5E1;
    --text-primary: #0F172A;
    --text-secondary: #475569;
    --text-muted: #64748B;
    --accent-teal: #1F4B44;
    --accent-light: #E8F1EE;
    --green-badge: #DCFCE7;
    --green-text: #166534;
    --green-border: #86EFAC;
    --yellow-badge: #FEF3C7;
    --yellow-text: #92400E;
    --yellow-border: #FCD34D;
    --red-badge: #FEE2E2;
    --red-text: #991B1B;
    --red-border: #FCA5A5;
}

/* Fondo de aplicación */
.stApp {
    background-color: var(--bg-page) !important;
    color: var(--text-primary) !important;
}

/* Sidebar refinada */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid var(--border-soft) !important;
}

/* Animaciones suaves */
@keyframes slideFadeIn {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.fade-in {
    animation: slideFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Tarjetas de métricas modernas */
.metric-box {
    background: #FFFFFF;
    border: 1px solid var(--border-soft);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03), 0 1px 2px rgba(0,0,0,0.02);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.metric-box:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.06);
    border-color: var(--border-strong);
}

.metric-title {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: 4px;
}

.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.1;
}

.metric-subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-top: 4px;
}

/* Badges del semáforo */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.82rem;
    font-weight: 600;
    border: 1px solid transparent;
}

.badge-verde {
    background: var(--green-badge);
    color: var(--green-text);
    border-color: var(--green-border);
}

.badge-amarillo {
    background: var(--yellow-badge);
    color: var(--yellow-text);
    border-color: var(--yellow-border);
}

.badge-rojo {
    background: var(--red-badge);
    color: var(--red-text);
    border-color: var(--red-border);
}

/* Tarjetas de recomendación */
.rec-card {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid var(--border-soft);
    padding: 16px 18px;
    margin-bottom: 12px;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.rec-card:hover {
    transform: translateX(4px);
    box-shadow: 0 6px 14px rgba(0,0,0,0.06);
    border-color: #CBD5E1;
}

/* Callout suave */
.info-callout {
    background: #F0FDF4;
    border-left: 4px solid #166534;
    border-radius: 6px;
    padding: 12px 16px;
    font-size: 0.9rem;
    color: #14532D;
    margin-bottom: 16px;
}

/* Tabs refinados */
button[data-baseweb="tab"] {
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    padding: 10px 16px !important;
    transition: all 0.2s ease !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    font-weight: 700 !important;
    color: var(--accent-teal) !important;
    border-bottom-color: var(--accent-teal) !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2. Carga y preparación de datos
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Calculando proyecciones insesgadas...")
def get_cached_dataset():
    ds = build_dataset(horizons=HORIZONS_YEARS)
    df = get_zones_dataframe(ds)
    return ds, df

dataset, df_zones = get_cached_dataset()

# Inicializar estados de sesión para interactividad entre vistas
if "selected_alcaldia" not in st.session_state:
    st.session_state["selected_alcaldia"] = "Iztapalapa"
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "🗺️ Mapa & Prioridades"

# ---------------------------------------------------------------------------
# 3. Barra Lateral (Filtros Estratégicos & Contexto)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🚦 Semáforo de Inversión")
    st.caption("Herramienta de decisión pública y social para CDMX")
    st.markdown("---")

    st.markdown("#### 🎯 Filtros Principales")

    # Filtro por Categoría
    categoria_options = ["Todas"] + CATEGORIES
    categoria_sel = st.selectbox(
        "Categoría de Infraestructura",
        options=categoria_options,
        index=0,
        help="Selecciona una categoría de equipamiento social para el análisis.",
    )

    # Filtro por Horizonte de Proyección
    st.markdown("#### 🔮 Horizonte Temporal")
    horizonte = st.segmented_control(
        "Años a proyectar",
        options=[3, 5, 7],
        default=3,
        format_func=lambda h: f"{h} años",
        help="Proyecciones a futuro con intervalos insesgados basados en t de Student.",
    )
    if horizonte is None:
        horizonte = 3

    # Filtro por Clasificación Semáforo
    st.markdown("#### 🔍 Estado del Semáforo")
    filtro_estados = st.multiselect(
        "Filtrar por clasificación",
        options=["verde", "amarillo", "rojo"],
        default=["verde", "amarillo", "rojo"],
        format_func=lambda s: {
            "verde": "🟢 Oportunidad (Alta prioridad)",
            "amarillo": "🟡 Transición (Monitorear)",
            "rojo": "🔴 Saturada (Capacidad cubierta)",
        }[s],
    )

    st.markdown("---")

    # Guía ejecutiva rápida
    with st.expander("📖 ¿Cómo interpretar el Semáforo?", expanded=False):
        st.markdown("""
        - 🟢 **Oportunidad**: Territorios con **baja oferta per cápita** y alta demanda insatisfecha. Candidatos primarios para nuevas aperturas o inversión pública.
        - 🟡 **Transición**: Crecimiento equilibrado o en proceso de densificación. Requieren seguimiento para anticipar déficits.
        - 🔴 **Saturada**: Densidad de oferta alta y crecimiento estancado. Invertir aquí puede canibalizar servicios existentes.
        """)

    st.markdown("---")
    st.caption(
        "📊 **Garantía Metodológica**: Intervalos insesgados calculados con $t_{0.975,\\, 3} = 3.182$ "
        "para corregir el sesgo en series pequeñas ($n=5$ puntos censales DENUE)."
    )

# ---------------------------------------------------------------------------
# 4. Filtrado reactivo de datos
# ---------------------------------------------------------------------------
df_filtered = df_zones.copy()
if categoria_sel != "Todas":
    df_filtered = df_filtered[df_filtered["Categoría"] == categoria_sel]
if filtro_estados:
    df_filtered = df_filtered[df_filtered["Semáforo"].isin(filtro_estados)]

zones_filtered = [
    z for z in dataset["zonas"]
    if (categoria_sel == "Todas" or z["categoria"] == categoria_sel)
    and z["semaforo"] in filtro_estados
]

# ---------------------------------------------------------------------------
# 5. Header y Resumen Ejecutivo
# ---------------------------------------------------------------------------
st.markdown("""
<div class="fade-in" style="margin-bottom: 24px;">
    <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 4px;">
        <h1 style="margin: 0; font-size: 2rem; font-weight: 700; color: #0F172A; letter-spacing: -0.02em;">
            Semáforo de Inversión Social · CDMX
        </h1>
        <span class="badge badge-verde">Datos DENUE + Censo INEGI</span>
    </div>
    <p style="margin: 0; font-size: 1.05rem; color: #475569; max-width: 850px; line-height: 1.5;">
        Identificación estratégica de <strong>islas de carencia</strong> en infraestructura comunitaria, deportiva y geriátrica. 
        Proyecciones insesgadas a <strong>3, 5 y 7 años</strong> para orientar la asignación de recursos.
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 6. KPI Cards Ejecutivas
# ---------------------------------------------------------------------------
total_analizadas = len(df_filtered)
n_oportunidad = len(df_filtered[df_filtered["Semáforo"] == "verde"])
n_saturadas = len(df_filtered[df_filtered["Semáforo"] == "rojo"])

# Calcular alcaldía con mayor urgencia de oportunidad
if not df_filtered[df_filtered["Semáforo"] == "verde"].empty:
    top_urgente = df_filtered[df_filtered["Semáforo"] == "verde"].sort_values(
        "Oferta per cápita (100k)", ascending=True
    ).iloc[0]
    top_alcaldia_nombre = f"{top_urgente['Alcaldía']}"
    top_alcaldia_sub = f"{top_urgente['Oferta per cápita (100k)']:.1f} est./100k hab"
else:
    top_alcaldia_nombre = "N/A"
    top_alcaldia_sub = "Sin zonas filtradas"

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Zonas en Análisis</div>
        <div class="metric-value">{total_analizadas}</div>
        <div class="metric-subtitle">Combinaciones alcaldía-categoría</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-box" style="border-left: 4px solid #166534;">
        <div class="metric-title" style="color: #166534;">🟢 Zonas de Oportunidad</div>
        <div class="metric-value" style="color: #166534;">{n_oportunidad}</div>
        <div class="metric-subtitle">Prioritarias para nueva inversión</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-box" style="border-left: 4px solid #991B1B;">
        <div class="metric-title" style="color: #991B1B;">🔴 Zonas Saturadas</div>
        <div class="metric-value" style="color: #991B1B;">{n_saturadas}</div>
        <div class="metric-subtitle">Alta oferta o estancamiento</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-box" style="border-left: 4px solid #1F4B44;">
        <div class="metric-title">Mayor Déficit Relativo</div>
        <div class="metric-value" style="font-size: 1.45rem;">{top_alcaldia_nombre}</div>
        <div class="metric-subtitle">{top_alcaldia_sub}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 7. Navegación Principal por Pestañas (Estructura Limpia y Focalizada)
# ---------------------------------------------------------------------------
tab_mapa, tab_simulador, tab_matriz, tab_auditoria = st.tabs([
    "🗺️ Mapa & Prioridades",
    "📈 Simulador de Proyecciones (3, 5 y 7 años)",
    "⚖️ Matriz de Decisión",
    "🛡️ Metodología & Rigor Estadístico",
])

# ===========================================================================
# TAB 1: MAPA & PRIORIDADES
# ===========================================================================
with tab_mapa:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 600; color: #0F172A;">
            Distribución Territorial de Oportunidad Social
        </h3>
        <p style="margin: 2px 0 0 0; font-size: 0.9rem; color: #64748B;">
            Haz clic en los puntos del mapa o utiliza la lista de prioridades a la derecha para seleccionar un territorio.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_map, col_priority = st.columns([1.6, 1.0], gap="medium")

    with col_map:
        if not df_filtered.empty:
            # Crear mapa interactivo Plotly en Light Mode
            fig_map = go.Figure()

            # Mapeo de colores del semáforo
            color_palette = {
                "verde": {"color": "#166534", "name": "🟢 Oportunidad (Invertir)"},
                "amarillo": {"color": "#D97706", "name": "🟡 Transición (Vigilar)"},
                "rojo": {"color": "#DC2626", "name": "🔴 Saturada (Evitar saturar)"},
            }

            for sem_key, meta in color_palette.items():
                sub = df_filtered[df_filtered["Semáforo"] == sem_key]
                if sub.empty:
                    continue

                custom_hover = [
                    (
                        f"<b>{row['Alcaldía']}</b><br>"
                        f"Categoría: {row['Categoría']}<br>"
                        f"Oferta per cápita: <b>{row['Oferta per cápita (100k)']:.1f}</b> por 100k hab<br>"
                        f"Conteo actual (2026): <b>{row['Conteo actual']}</b> establecimientos<br>"
                        f"Proyección a {horizonte} años: <b>{row[f'Proy. {horizonte}a (est.)']:.0f}</b> (±{row[f'Proy. {horizonte}a (±95%)']:.1f})<br>"
                        f"Semáforo: <b>{sem_key.upper()}</b>"
                    )
                    for _, row in sub.iterrows()
                ]

                fig_map.add_trace(go.Scattermap(
                    lat=sub["Lat"],
                    lon=sub["Lon"],
                    mode="markers",
                    name=meta["name"],
                    marker=dict(
                        size=np.clip(sub["Conteo actual"] / 3.0, 14, 45),
                        color=meta["color"],
                        opacity=0.88,
                    ),
                    text=custom_hover,
                    hoverinfo="text",
                ))

            fig_map.update_layout(
                map_style="carto-positron",
                map_zoom=9.8,
                map_center=dict(lat=19.37, lon=-99.14),
                margin=dict(l=0, r=0, t=0, b=0),
                height=480,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=0.02,
                    xanchor="left",
                    x=0.02,
                    bgcolor="rgba(255, 255, 255, 0.92)",
                    bordercolor="#E2E8F0",
                    borderwidth=1,
                    font=dict(size=12, color="#0F172A"),
                ),
                transition=dict(duration=400, easing="cubic-in-out"),
            )

            st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No hay datos que coincidan con los filtros seleccionados.")

    with col_priority:
        st.markdown("#### 🎯 Zonas Prioritarias de Intervención")
        st.caption("Ordenadas de menor a mayor oferta relativa (mayor necesidad social).")

        df_top_oport = df_filtered[df_filtered["Semáforo"] == "verde"].sort_values(
            "Oferta per cápita (100k)", ascending=True
        )

        if not df_top_oport.empty:
            for idx, (_, row) in enumerate(df_top_oport.head(4).iterrows()):
                st.markdown(f"""
                <div class="rec-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <span style="font-weight: 700; font-size: 1rem; color: #0F172A;">
                            #{idx+1} {row['Alcaldía']}
                        </span>
                        <span class="badge badge-verde">Oportunidad</span>
                    </div>
                    <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 8px;">
                        {row['Categoría']}
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.85rem; background: #F8FAF9; padding: 8px 10px; border-radius: 6px;">
                        <div>
                            <span style="color: #64748B;">Oferta actual:</span><br>
                            <strong>{row['Oferta per cápita (100k)']:.1f} / 100k</strong>
                        </div>
                        <div>
                            <span style="color: #64748B;">Proy. {horizonte}a:</span><br>
                            <strong>{row[f'Proy. {horizonte}a (est.)']:.0f} (±{row[f'Proy. {horizonte}a (±95%)']:.0f})</strong>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón interactivo para examinar ficha
                if st.button(f"🔍 Ver ficha de {row['Alcaldía']} ({row['Categoría'][:16]}...)", key=f"btn_focus_{row['Alcaldía']}_{row['Categoría']}_{idx}"):
                    st.session_state["selected_alcaldia"] = row["Alcaldía"]
                    st.rerun()
        else:
            st.warning("No hay zonas de oportunidad con el filtro actual.")

# ===========================================================================
# TAB 2: SIMULADOR DE PROYECCIONES (3, 5 Y 7 AÑOS)
# ===========================================================================
with tab_simulador:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 600; color: #0F172A;">
            Simulador de Proyecciones Insesgadas a 3, 5 y 7 Años
        </h3>
        <p style="margin: 2px 0 0 0; font-size: 0.9rem; color: #64748B;">
            Estimación de mínimos cuadrados con intervalos de predicción corregidos por t de Student (df=3) para garantizar insesgadez estadística.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Selector reactivo de Alcaldía
    alcaldias_list = sorted(list(POBLACION_2020_ALCALDIA.keys()))
    default_idx = alcaldias_list.index(st.session_state.get("selected_alcaldia", "Iztapalapa")) if st.session_state.get("selected_alcaldia") in alcaldias_list else 0

    sel_col1, sel_col2, sel_col3 = st.columns([1.5, 1.5, 1.0])
    with sel_col1:
        alcaldia_seleccionada = st.selectbox(
            "Alcaldía para análisis a profundidad",
            options=alcaldias_list,
            index=default_idx,
            key="selector_alcaldia_ficha",
        )
    with sel_col2:
        # Categorías disponibles para esta alcaldía
        cat_disponibles = [
            z["categoria"] for z in dataset["zonas"] if z["alcaldia"] == alcaldia_seleccionada
        ]
        cat_seleccionada = st.selectbox(
            "Categoría de equipamiento",
            options=cat_disponibles,
            index=0,
        )
    with sel_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        # Sincronizar estado
        st.session_state["selected_alcaldia"] = alcaldia_seleccionada

    # Obtener zona seleccionada
    zona_activa = next(
        (z for z in dataset["zonas"] if z["alcaldia"] == alcaldia_seleccionada and z["categoria"] == cat_seleccionada),
        None
    )

    if zona_activa:
        # Header de la zona con badges
        sem_color = zona_activa["semaforo"]
        badge_class = f"badge-{sem_color}"
        sem_label = {
            "verde": "🟢 Zona de Oportunidad",
            "amarillo": "🟡 Zona en Transición",
            "rojo": "🔴 Zona Saturada",
        }.get(sem_color, sem_color)

        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin: 14px 0 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px;">
                <div>
                    <h2 style="margin: 0; font-size: 1.6rem; color: #0F172A;">{zona_activa['alcaldia']}</h2>
                    <span style="font-size: 0.92rem; color: #64748B;">{zona_activa['categoria']} · Población: {zona_activa['poblacion_2020']:,} habitantes</span>
                </div>
                <div>
                    <span class="badge {badge_class}" style="font-size: 0.92rem; padding: 6px 14px;">
                        {sem_label}
                    </span>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
                <div style="background: #F8FAF9; padding: 12px 14px; border-radius: 8px;">
                    <span style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Oferta Actual (2026)</span>
                    <div style="font-size: 1.35rem; font-weight: 700; color: #0F172A;">{zona_activa['serie_historica'][-1]['conteo']} est.</div>
                    <span style="font-size: 0.8rem; color: #64748B;">{zona_activa['oferta_percapita_100k']:.1f} por 100k hab</span>
                </div>
                <div style="background: #F8FAF9; padding: 12px 14px; border-radius: 8px;">
                    <span style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Tendencia Anual</span>
                    <div style="font-size: 1.35rem; font-weight: 700; color: {'#166534' if zona_activa['tendencia_pendiente_anual'] > 0 else '#991B1B'};">
                        {zona_activa['tendencia_pendiente_anual']:+.2f} / año
                    </div>
                    <span style="font-size: 0.8rem; color: #64748B;">R² = {zona_activa['tendencia_r2']:.2f}</span>
                </div>
                <div style="background: #F8FAF9; padding: 12px 14px; border-radius: 8px;">
                    <span style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Proyección a {horizonte} años</span>
                    <div style="font-size: 1.35rem; font-weight: 700; color: #1F4B44;">
                        {zona_activa['proyeccion'][str(horizonte)]['estimado']:.0f} est.
                    </div>
                    <span style="font-size: 0.8rem; color: #64748B;">Banda ±95%: ±{zona_activa['proyeccion'][str(horizonte)]['banda_95']:.1f}</span>
                </div>
                <div style="background: #F8FAF9; padding: 12px 14px; border-radius: 8px;">
                    <span style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Error Retrospectivo</span>
                    <div style="font-size: 1.35rem; font-weight: 700; color: #0F172A;">
                        {zona_activa['loo_cv']['loo_mape'] if zona_activa['loo_cv']['loo_mape'] is not None else 0:.1f}%
                    </div>
                    <span style="font-size: 0.8rem; color: #64748B;">MAPE Leave-One-Out</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Gráfico interactivo con bandas de proyección insesgada
        st.markdown("#### 📊 Curva de Evolución Histórica y Proyecciones Insesgadas")

        hist_eds = [h["edicion"] for h in zona_activa["serie_historica"]]
        hist_counts = [h["conteo"] for h in zona_activa["serie_historica"]]
        hist_years = [EDITION_YEARS[ed] for ed in hist_eds]

        # Regresión y proyecciones
        x_arr = np.array(hist_years)
        y_arr = np.array(hist_counts, dtype=float)
        fit = ols_fit(x_arr, y_arr)

        fig_proj = go.Figure()

        # 1. Puntos históricos observados
        fig_proj.add_trace(go.Scatter(
            x=hist_eds,
            y=hist_counts,
            mode="lines+markers",
            name="Observado (DENUE)",
            line=dict(color="#0F172A", width=3),
            marker=dict(size=9, color="#0F172A"),
            hovertemplate="<b>%{x}</b><br>Observado: <b>%{y} establecimientos</b><extra></extra>",
        ))

        # 2. Horizonte de proyección a 3, 5 y 7 años
        proj_horizons = [3, 5, 7]
        proj_x_labels = [f"+{h} años ({2026 + h})" for h in proj_horizons]
        proj_years = [hist_years[-1] + h for h in proj_horizons]

        proj_estimates = []
        proj_lowers = []
        proj_uppers = []

        for yr in proj_years:
            y_hat, lo, hi = fit["predict"](yr)
            proj_estimates.append(y_hat)
            proj_lowers.append(lo)
            proj_uppers.append(hi)

        # Unir el último punto observado con las proyecciones
        full_proj_x = [hist_eds[-1]] + proj_x_labels
        full_proj_y = [hist_counts[-1]] + proj_estimates
        full_proj_lo = [hist_counts[-1]] + proj_lowers
        full_proj_hi = [hist_counts[-1]] + proj_uppers

        # Banda superior (oculta para rellenar)
        fig_proj.add_trace(go.Scatter(
            x=full_proj_x,
            y=full_proj_hi,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Banda inferior con relleno de color suave
        fig_proj.add_trace(go.Scatter(
            x=full_proj_x,
            y=full_proj_lo,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(31, 75, 68, 0.12)",
            name="Intervalo 95% (t de Student)",
            hoverinfo="skip",
        ))

        # Línea central proyectada
        fig_proj.add_trace(go.Scatter(
            x=full_proj_x,
            y=full_proj_y,
            mode="lines+markers",
            name="Proyección Central Insesgada",
            line=dict(color="#1F4B44", width=2.5, dash="dash"),
            marker=dict(size=8, symbol="diamond", color="#1F4B44"),
            hovertemplate="<b>%{x}</b><br>Estimado: <b>%{y:.1f} est.</b><extra></extra>",
        ))

        # Destacar el horizonte actualmente seleccionado
        h_idx = proj_horizons.index(horizonte)
        fig_proj.add_trace(go.Scatter(
            x=[proj_x_labels[h_idx]],
            y=[proj_estimates[h_idx]],
            mode="markers",
            name=f"Seleccionado ({horizonte} años)",
            marker=dict(size=14, color="#166534", symbol="star"),
            hovertemplate=f"<b>Horizonte {horizonte} años</b><br>Estimación: <b>{proj_estimates[h_idx]:.1f}</b><br>Rango 95%: [{proj_lowers[h_idx]:.1f} - {proj_uppers[h_idx]:.1f}]<extra></extra>",
        ))

        fig_proj.update_layout(
            template="plotly_white",
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            xaxis=dict(
                title=dict(text="Línea de Tiempo", font=dict(color="#64748B")),
                gridcolor="#F1F5F9",
                tickfont=dict(color="#475569"),
            ),
            yaxis=dict(
                title=dict(text="Conteo de Establecimientos", font=dict(color="#64748B")),
                gridcolor="#F1F5F9",
                tickfont=dict(color="#475569"),
            ),
            hovermode="x unified",
            margin=dict(l=40, r=20, t=30, b=40),
            height=380,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12, color="#0F172A"),
            ),
            transition=dict(duration=500, easing="cubic-in-out"),
        )

        st.plotly_chart(fig_proj, use_container_width=True, config={"displayModeBar": False})

        # Tabla comparativa de horizontes 3, 5 y 7 años
        col_table, col_breakdown = st.columns([1.3, 1.0], gap="large")

        with col_table:
            st.markdown("##### 🔮 Resumen de Proyecciones a 3, 5 y 7 Años")
            horizon_summary = []
            for h in [3, 5, 7]:
                proj = zona_activa["proyeccion"][str(h)]
                diff_act = proj["estimado"] - hist_counts[-1]
                horizon_summary.append({
                    "Horizonte": f"{h} años",
                    "Año": 2026 + h,
                    "Estimación Central": f"{proj['estimado']:.1f}",
                    "Cambio Neto": f"{diff_act:+.1f}",
                    "Rango Insesgado 95%": f"[{proj['lower_95']:.1f} a {proj['upper_95']:.1f}]",
                    "Margen de Error": f"±{proj['banda_95']:.1f}",
                })
            st.dataframe(
                pd.DataFrame(horizon_summary),
                use_container_width=True,
                hide_index=True,
            )

            # Factores determinantes en formato limpio
            st.markdown("##### 💡 Factores Determinantes de la Clasificación")
            for factor in zona_activa["factores_determinantes"]:
                st.markdown(f"""
                <div style="display: flex; align-items: baseline; gap: 8px; font-size: 0.88rem; color: #334155; margin-bottom: 4px;">
                    <span style="color: #1F4B44;">•</span>
                    <span>{factor}</span>
                </div>
                """, unsafe_allow_html=True)

        with col_breakdown:
            st.markdown("##### 🏢 Composición de Oferta por Subcategoría")
            if zona_activa["subcategorias"]:
                sub_df = pd.DataFrame(zona_activa["subcategorias"])
                
                # Gráfico donut elegante
                fig_donut = px.pie(
                    sub_df,
                    names="subcategoria",
                    values="conteo",
                    hole=0.55,
                    color_discrete_sequence=["#1F4B44", "#0D9488", "#14B8A6", "#5EEAD4", "#99F6E4"],
                )
                fig_donut.update_traces(
                    textposition="inside",
                    textinfo="percent+value",
                    hoverinfo="label+value+percent",
                    marker=dict(line=dict(color="#FFFFFF", width=2)),
                )
                fig_donut.update_layout(
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=10)),
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=240,
                )
                st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("No se registran subcategorías desagregadas para esta zona.")

# ===========================================================================
# TAB 3: MATRIZ DE DECISIÓN (SCATTER CUADRANTES)
# ===========================================================================
with tab_matriz:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 600; color: #0F172A;">
            Matriz Estratégica de Decisión: Cobertura vs. Crecimiento
        </h3>
        <p style="margin: 2px 0 0 0; font-size: 0.9rem; color: #64748B;">
            Posicionamiento territorial de todas las alcaldías. Permite clasificar la urgencia de inversión sin sobrecargar con tablas extensas.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not df_filtered.empty:
        # Calcular medianas para las líneas de cuadrante
        med_oferta = df_filtered["Oferta per cápita (100k)"].median()
        med_pendiente = 0.0

        fig_matrix = go.Figure()

        color_map_scatter = {
            "verde": "#166534",
            "amarillo": "#D97706",
            "rojo": "#DC2626",
        }

        for sem, color_code in color_map_scatter.items():
            sub = df_filtered[df_filtered["Semáforo"] == sem]
            if sub.empty:
                continue

            fig_matrix.add_trace(go.Scatter(
                x=sub["Oferta per cápita (100k)"],
                y=sub["Pendiente anual"],
                mode="markers+text",
                name=sem.capitalize(),
                text=sub["Alcaldía"],
                textposition="top center",
                textfont=dict(size=11, color="#1E293B"),
                marker=dict(
                    size=14,
                    color=color_code,
                    opacity=0.9,
                    line=dict(width=1.5, color="#FFFFFF"),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Oferta per cápita: <b>%{x:.1f} por 100k</b><br>"
                    "Crecimiento anual: <b>%{y:+.2f} est./año</b><br>"
                    f"Semáforo: <b>{sem.upper()}</b><extra></extra>"
                ),
            ))

        # Líneas de referencia para cuadrantes
        fig_matrix.add_vline(x=med_oferta, line_dash="dash", line_color="#CBD5E1", line_width=1.5)
        fig_matrix.add_hline(y=med_pendiente, line_dash="dash", line_color="#CBD5E1", line_width=1.5)

        # Anotaciones de cuadrantes
        x_max = df_filtered["Oferta per cápita (100k)"].max() * 1.05
        x_min = df_filtered["Oferta per cápita (100k)"].min() * 0.95
        y_max = df_filtered["Pendiente anual"].max() * 1.15
        y_min = df_filtered["Pendiente anual"].min() * 1.15

        fig_matrix.add_annotation(
            x=x_min + (med_oferta - x_min) * 0.1, y=y_max,
            text="🟢 <b>OPORTUNIDAD ALTA</b><br>Baja oferta / Crecimiento activo",
            showarrow=False, font=dict(size=10, color="#166534"), align="left",
        )
        fig_matrix.add_annotation(
            x=x_min + (med_oferta - x_min) * 0.1, y=y_min,
            text="⚠️ <b>DÉFICIT CRÍTICO</b><br>Baja oferta / Decreciendo",
            showarrow=False, font=dict(size=10, color="#92400E"), align="left",
        )
        fig_matrix.add_annotation(
            x=med_oferta + (x_max - med_oferta) * 0.7, y=y_min,
            text="🔴 <b>ZONA SATURADA</b><br>Alta oferta / Sin crecimiento",
            showarrow=False, font=dict(size=10, color="#991B1B"), align="right",
        )

        fig_matrix.update_layout(
            template="plotly_white",
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            xaxis=dict(
                title="Oferta per cápita (Establecimientos por 100k hab)",
                gridcolor="#F1F5F9",
            ),
            yaxis=dict(
                title="Tendencia anual (Pendiente de aperturas/año)",
                gridcolor="#F1F5F9",
            ),
            margin=dict(l=40, r=40, t=30, b=40),
            height=460,
            showlegend=False,
            transition=dict(duration=400, easing="cubic-in-out"),
        )

        st.plotly_chart(fig_matrix, use_container_width=True, config={"displayModeBar": False})

        # Tabla limpia y ordenable para usuarios que requieran el dato exacto
        with st.expander("📋 Ver Tabla Completa de Indicadores", expanded=False):
            cols_clean = [
                "Alcaldía", "Categoría", "Semáforo", "Conteo actual",
                "Oferta per cápita (100k)", "Pendiente anual", "R²",
                f"Proy. {horizonte}a (est.)", f"Proy. {horizonte}a (±95%)",
            ]
            st.dataframe(
                df_filtered[cols_clean].sort_values("Oferta per cápita (100k)", ascending=True),
                use_container_width=True,
                hide_index=True,
            )

# ===========================================================================
# TAB 4: METODOLOGÍA & RIGOR ESTADÍSTICO
# ===========================================================================
with tab_auditoria:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 600; color: #0F172A;">
            Rigor Estadístico, Insesgadez y Validación del Modelo
        </h3>
        <p style="margin: 2px 0 0 0; font-size: 0.9rem; color: #64748B;">
            Documentación técnica auditable sobre cómo se estiman de forma insesgada las proyecciones y cómo se evalúa su incertidumbre.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_m1, col_m2 = st.columns(2, gap="large")

    with col_m1:
        st.markdown("#### 📐 ¿Por qué la estimación es insesgada?")
        st.markdown("""
        En muestras pequeñas ($n=5$ puntos temporales correspondientes a las ediciones DENUE 2022 a 2026), 
        la aproximación asintótica normal ($z=1.96$) **subestima severamente el error de predicción**, produciendo 
        intervalos excesivamente optimistas y sesgados hacia la sobreconfianza.

        Para garantizar una estimación **estrictamente insesgada**, se aplican dos correcciones fundamentales:

        1. **Distribución t de Student con $n - 2 = 3$ grados de libertad**:
           Se sustituye $z=1.96$ por el valor crítico bilateral exacto:
           $$t_{0.975,\\, 3} = 3.1824$$
           Esto amplía los márgenes de predicción en un **62%**, reflejando la incertidumbre epistémica real.

        2. **Error Estándar de Predicción Completo**:
           El intervalo no solo mide la dispersión del ajuste, sino también la distancia al centro de los datos $(x_0 - \\bar{x})^2$:
           $$SE_{pred}(x_0) = s_e \\sqrt{1 + \\frac{1}{n} + \\frac{(x_0 - \\bar{x})^2}{\\sum (x_i - \\bar{x})^2}}$$
           
           A medida que el horizonte se aleja (de 3 a 5 y 7 años), la banda de incertidumbre se ensancha de manera matemática y honesta.
        """)

    with col_m2:
        st.markdown("#### ✅ Validación Retrospectiva (Backtesting)")
        st.markdown("""
        Siguiendo las directrices del reto (*"entrenamiento con datos históricos para validar el acierto del modelo"*):

        - **Entrenamiento**: Primeras 3 ediciones (Nov-2022, Nov-2023, Nov-2024).
        - **Evaluación a ciegas**: Predicción de las ediciones Mayo-2025 y Mayo-2026.
        - **Diagnóstico Leave-One-Out (LOO-CV)**: Se evalúa la sensibilidad del modelo omitiendo una edición a la vez para calcular el Error Porcentual Absoluto Medio (MAPE).
        """)

        # Métricas de validación global
        val_records = []
        for z in dataset["zonas"]:
            for v in z["validacion_retrospectiva"]:
                val_records.append({
                    "Alcaldía": z["alcaldia"],
                    "Categoría": z["categoria"],
                    "Edición": v["edicion"],
                    "Error %": v["error_pct"],
                    "Dentro del IC 95%": v["dentro_IC"],
                })

        val_df = pd.DataFrame(val_records)
        tasa_cobertura = (val_df["Dentro del IC 95%"].sum() / len(val_df)) * 100
        mape_promedio = val_df["Error %"].dropna().mean()

        v1, v2 = st.columns(2)
        with v1:
            st.metric("Tasa de Cobertura IC 95%", f"{tasa_cobertura:.1f}%", help="Porcentaje de observaciones reales que cayeron dentro del intervalo previsto.")
        with v2:
            st.metric("MAPE Promedio de Validación", f"{mape_promedio:.1f}%", help="Error porcentual absoluto medio en las predicciones retrospectivas.")

    st.markdown("---")
    st.caption("""
    📌 **Fuentes de información utilizadas**: Directorio Estadístico Nacional de Unidades Económicas (DENUE, INEGI 2022-2026), Censo de Población y Vivienda 2020 (INEGI).
    """)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("""
<div style="margin-top: 40px; padding-top: 16px; border-top: 1px solid #E2E8F0; text-align: center; font-size: 0.82rem; color: #94A3B8;">
    Semáforo de Inversión Social · Datatón CDMX 2026 · Construido con Streamlit & Plotly
</div>
""", unsafe_allow_html=True)
