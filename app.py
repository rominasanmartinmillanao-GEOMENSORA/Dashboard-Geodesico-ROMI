import base64
import io
import os
import dash
from dash import Input, Output, State, dcc, html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import rasterio

app = dash.Dash(__name__)

# --- FUNCIÓN PARA GENERAR EL DASHBOARD (Gráficos 2x2) ---


def generar_dashboard(df_puntos=None):
  ruta_egm2008 = "datos/egm2008.tif"
  ruta_egm96 = "datos/egm96.tif"

  # Carga de grillas geoidales o simulación por defecto
  if os.path.exists(ruta_egm2008) and os.path.exists(ruta_egm96):
    with rasterio.open(ruta_egm2008) as src2008:
      egm2008_data = src2008.read(1)
    with rasterio.open(ruta_egm96) as src96:
      egm96_data = src96.read(1)
    latitudes = np.linspace(-39.0, -38.5, 50)
    longitudes = np.linspace(-73.0, -72.2, 50)
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    delta_N = egm2008_data[:50, :50] - egm96_data[:50, :50]
  else:
    latitudes = np.linspace(-39.0, -38.5, 50)
    longitudes = np.linspace(-73.0, -72.2, 50)
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    N_2008 = -18.5 + (lat_grid * 0.1) + (lon_grid * 0.05)
    N_96 = -18.3 + (lat_grid * 0.102) + (lon_grid * 0.049)
    delta_N = N_2008 - N_96

  # Si no se pasó un DataFrame por carga web, usa los datos por defecto
  if df_puntos is None:
    ruta_puntos = "datos/puntos_terreno.csv"
    if os.path.exists(ruta_puntos):
      df_puntos = pd.read_csv(ruta_puntos)
    else:
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

  # Calcular ΔN en centímetros si no existe la columna
  if "Delta_N_cm" not in df_puntos.columns:
    if "N_2008" in df_puntos.columns and "N_96" in df_puntos.columns:
      df_puntos["Delta_N_cm"] = (
          df_puntos["N_2008"] - df_puntos["N_96"]
      ) * 100
    else:
      df_puntos["Delta_N_cm"] = 0.0

  # Construcción de Subplots (2x2)
  fig = make_subplots(
      rows=2,
      cols=2,
      specs=[[{"type": "scattergeo"}, {"type": "surface"}], [{"type": "xy"}, {"type": "table"}]],
      subplot_titles=(
          "1. Mapa de Distribución de Diferencias (ΔN)",
          "2. Superficie 3D de Residuales (EGM2008 vs EGM96)",
          "3. Perfil Transversal de Ondulación (cm)",
          "4. Tabla de Vértices y Validación Altimétrica",
      ),
  )

  # Gráfico 1: Mapa geoespacial de puntos
  fig.add_trace(
      go.Scattergeo(
          lat=df_puntos["Latitud"],
          lon=df_puntos["Longitud"],
          text=df_puntos.get(
              "Punto", [f"Pto {i}" for i in range(len(df_puntos))]
          )
          + "<br>ΔN: "
          + df_puntos["Delta_N_cm"].round(2).astype(str)
          + " cm",
          marker=dict(
              size=10,
              color=df_puntos["Delta_N_cm"],
              colorscale="Viridis",
              colorbar=dict(title="ΔN (cm)", x=0.46, y=0.8),
              showscale=True,
          ),
          name="Vértices",
      ),
      row=1,
      col=1,
  )

  # Gráfico 2: Superficie 3D de residuales
  fig.add_trace(
      go.Surface(
          z=delta_N * 100, colorscale="Plasma", name="Malla ΔN (cm)"
      ),
      row=1,
      col=2,
  )

  # Gráfico 3: Perfil transversal comparativo
  distancia_perfil = np.linspace(0, 100, 50)
  perfil_2008 = -18.5 + np.sin(distancia_perfil / 10) * 0.5
  perfil_96 = -18.3 + np.sin(distancia_perfil / 10) * 0.48
  fig.add_trace(
      go.Scatter(
          x=distancia_perfil,
          y=perfil_2008 * 100,
          name="EGM2008 (cm)",
          line=dict(color="blue"),
      ),
      row=2,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=distancia_perfil,
          y=perfil_96 * 100,
          name="EGM96 (cm)",
          line=dict(color="orange", dash="dash"),
      ),
      row=2,
      col=1,
  )

  # Gráfico 4: Tabla de vértices
  puntos_col = (
      df_puntos["Punto"]
      if "Punto" in df_puntos.columns
      else [f"P-{i}" for i in range(len(df_puntos))]
  )
  fig.add_trace(
      go.Table(
          header=dict(
              values=[
                  "<b>Punto</b>",
                  "<b>Latitud</b>",
                  "<b>Longitud</b>",
                  "<b>ΔN (cm)</b>",
              ],
              fill_color="paleturquoise",
              align="left",
          ),
          cells=dict(
              values=[
                  puntos_col,
                  df_puntos["Latitud"],
                  df_puntos["Longitud"],
                  df_puntos["Delta_N_cm"].round(2),
              ],
              fill_color="lavender",
              align="left",
          ),
      ),
      row=2,
      col=2,
  )

  # Configuración del diseño general
  fig.update_layout(
      title_text="<b>DASHBOARD GEODÉSICO: COMPARACIÓN EGM2008 vs EGM96</b>",
      template="plotly_dark",
      height=900,
      showlegend=False,
  )

  fig.update_geos(
      center=dict(lat=-38.75, lon=-72.60),
      projection_scale=15,
      showland=True,
      landcolor="rgb(40, 40, 40)",
      countrycolor="white",
      coastlinecolor="white",
  )

  return fig


# --- DISEÑO DE LA INTERFAZ WEB (LAYOUT) ---
app.layout = html.Div(
    [
        html.H1(
            "Dashboard Geodésico Interactivo",
            style={"textAlign": "center", "color": "white", "margin": "10px"},
        ),
        # Botón / Zona interactiva para cargar CSV
        dcc.Upload(
            id="upload-data",
            children=html.Div([
                "📁 Arrastra y suelta o ",
                html.A(
                    "selecciona tu archivo CSV de vértices",
                    style={"color": "#1df", "fontWeight": "bold"},
                ),
            ]),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "2px",
                "borderStyle": "dashed",
                "borderRadius": "8px",
                "textAlign": "center",
                "margin": "10px 0 15px 0",
                "backgroundColor": "#1e1e1e",
                "color": "white",
            },
            multiple=False,
        ),
        # Mensaje de estado de la carga
        html.Div(
            id="upload-status",
            style={"textAlign": "center", "marginBottom": "15px"},
        ),
        # Contenedor del Dashboard completo
        dcc.Graph(id="live-dashboard", figure=generar_dashboard()),
    ],
    style={"backgroundColor": "#111111", "color": "white", "padding": "20px"},
)


# --- CALLBACK PARA PROCESAR EL CSV Y ACTUALIZAR EL DASHBOARD ---
@app.callback(
    [Output("live-dashboard", "figure"), Output("upload-status", "children")],
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_dashboard(contents, filename):
  if contents is not None:
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
      df_user = pd.read_csv(io.BytesIO(decoded))
      # Verificar que contenga las columnas mínimas requeridas
      if "Latitud" in df_user.columns and "Longitud" in df_user.columns:
        fig_updated = generar_dashboard(df_user)
        status_msg = html.Span(
            f"✅ Archivo '{filename}' cargado con éxito ({len(df_user)} puntos procesados). El mapa y la tabla se han actualizado.",
            style={"color": "#00ff99", "fontWeight": "bold"},
        )
        return fig_updated, status_msg
      else:
        status_msg = html.Span(
            "⚠️ Error: El archivo CSV debe incluir al menos las columnas 'Latitud' y 'Longitud'.",
            style={"color": "#ffcc00"},
        )
        return dash.no_update, status_msg
    except Exception as e:
      status_msg = html.Span(
          f"❌ Error al leer el archivo: {str(e)}",
          style={"color": "#ff4d4d"},
      )
      return dash.no_update, status_msg

  return dash.no_update, ""


# --- EJECUCIÓN DEL SERVIDOR WEB LOCAL ---
if __name__ == '__main__':
  app.run(debug=True)