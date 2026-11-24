import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Configuración de la página en modo ancho
st.set_page_config(
    page_title="Dashboard Geodésico EGM",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🗺️ Dashboard Geodésico: Comparación EGM2008 vs EGM96")
st.markdown(
    "Herramienta interactiva para el análisis de diferencias altimétricas"
    " y validación de vértices."
)

# --- PANEL LATERAL (SIDEBAR): CARGA DE DATOS Y FILTROS ---
st.sidebar.header("📁 Gestión de Datos")
archivo_subido = st.sidebar.file_uploader(
    "Cargar CSV de vértices personalizado", type=["csv"]
)

# Casillero interactivo de texto opcional para notas o filtrado
filtro_punto = st.sidebar.text_input(
    "🔍 Buscar vértice por nombre (opcional):", ""
)

# --- CARGAR O SIMULAR DATOS DE PUNTOS ---
if archivo_subido is not None:
  df_puntos = pd.read_csv(archivo_subido)
  st.sidebar.success(
      f"¡Archivo cargado con éxito! ({len(df_puntos)} registros)"
  )
else:
  # Datos por defecto si no se sube nada
  df_puntos = pd.DataFrame({
      "Punto": [
          "PR-01 (Temuco)",
          "PR-02 (Padre Las Casas)",
          "PR-03 (Labranza)",
          "PR-04 (Cunco)",
      ],
      "Latitud": [-38.735, -38.765, -38.750, -38.900],
      "Longitud": [-72.590, -72.580, -72.700, -71.920],
      "H_Elipsoidal": [125.40, 115.80, 105.20, 250.60],
      "N_2008": [-18.45, -18.48, -18.52, -19.10],
      "N_96": [-18.25, -18.28, -18.32, -18.90],
  })

# Calcular diferencias si no existen
if "Delta_N_cm" not in df_puntos.columns:
  df_puntos["Delta_N_cm"] = (df_puntos["N_2008"] - df_puntos["N_96"]) * 100

# Aplicar filtro de búsqueda si el usuario escribió algo
if filtro_punto:
  df_puntos = df_puntos[
      df_puntos["Punto"].str.contains(filtro_punto, case=False, na=False)
  ]

# --- SIMULACIÓN DE GRILLAS 3D ---
latitudes = np.linspace(-39.0, -38.5, 50)
longitudes = np.linspace(-73.0, -72.2, 50)
lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
N_2008_m = -18.5 + (lat_grid * 0.1) + (lon_grid * 0.05)
N_96_m = -18.3 + (lat_grid * 0.102) + (lon_grid * 0.049)
delta_N = N_2008_m - N_96_m

# --- CONSTRUCCIÓN DE GRÁFICOS (PLOTLY 2x2) ---
fig = make_subplots(
    rows=2,
    cols=2,
    specs=[[{"type": "scattergeo"}, {"type": "surface"}], [{"type": "xy"}, {"type": "table"}]],
    subplot_titles=(
        "1. Mapa de Distribución de Diferencias (ΔN)",
        "2. Superficie 3D de Residuales",
        "3. Perfil Transversal de Ondulación (cm)",
        "4. Tabla de Vértices y Validación Altimétrica",
    ),
)

# 1. Mapa geoespacial
fig.add_trace(
    go.Scattergeo(
        lat=df_puntos["Latitud"],
        lon=df_puntos["Longitud"],
        text=df_puntos["Punto"]
        + "<br>ΔN: "
        + df_puntos["Delta_N_cm"].round(2).astype(str)
        + " cm",
        marker=dict(
            size=10,
            color=df_puntos["Delta_N_cm"],
            colorscale="Viridis",
            showscale=True,
        ),
        name="Vértices",
    ),
    row=1,
    col=1,
)

# 2. Superficie 3D
fig.add_trace(
    go.Surface(
        z=delta_N * 100, colorscale="Plasma", name="Malla ΔN (cm)"
    ),
    row=1,
    col=2,
)

# 3. Perfil transversal
distancia_perfil = np.linspace(0, 100, 50)
fig.add_trace(
    go.Scatter(
        x=distancia_perfil,
        y=(-18.5 + np.sin(distancia_perfil / 10) * 0.5) * 100,
        name="EGM2008",
        line=dict(color="blue"),
    ),
    row=2,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=distancia_perfil,
        y=(-18.3 + np.sin(distancia_perfil / 10) * 0.48) * 100,
        name="EGM96",
        line=dict(color="orange", dash="dash"),
    ),
    row=2,
    col=1,
)

# 4. Tabla de datos
fig.add_trace(
    go.Table(
        header=dict(
            values=[
                "<b>Punto</b>",
                "<b>Latitud</b>",
                "<b>Longitud</b>",
                "<b>ΔN (cm)</b>",
            ],
            fill_color="#1e293b",
            font=dict(color="white", size=12),
        ),
        cells=dict(
            values=[
                df_puntos["Punto"],
                df_puntos["Latitud"],
                df_puntos["Longitud"],
                df_puntos["Delta_N_cm"].round(2),
            ],
            fill_color="#f8fafc",
            font=dict(color="#334155", size=11),
        ),
    ),
    row=2,
    col=2,
)

fig.update_layout(
    template="plotly_dark", height=850, margin=dict(l=20, r=20, t=40, b=20)
)
fig.update_geos(
    center=dict(lat=-38.75, lon=-72.60),
    projection_scale=15,
    showland=True,
    landcolor="rgb(40, 40, 40)",
)

# --- RENDERIZAR EN STREAMLIT ---
st.plotly_chart(fig, use_container_width=True)