import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import folium
from folium.plugins import HeatMap # Importamos la función de Mapa de Calor
from streamlit_folium import folium_static

# --- 1. Funciones de Simulación y Cálculo de Métricas ---

def simular_datos_actividad(num_puntos=100):
    """
    Simula datos de actividad (similar a un archivo GPX/TCX) y genera datos para el mapa de calor.
    """
    lat_base, lon_base = -1.2683, -78.6186 

    data = {
        'Tiempo_Segundos': np.linspace(0, 2560, num_puntos), 
        'Latitud': lat_base + np.cumsum(np.random.normal(0, 0.00005, num_puntos)),
        'Longitud': lon_base + np.cumsum(np.random.normal(0, 0.00008, num_puntos)),
        'Ritmo_Min_Km': np.random.uniform(5.0, 7.5, num_puntos), 
        'FC_BPM': np.random.normal(135, 10, num_puntos).clip(100, 160).astype(int),
        'Cadencia_Pasos_Min': np.random.normal(155, 10, num_puntos).clip(130, 175).astype(int)
    }
    df = pd.DataFrame(data)
    
    # Simulación de Pausa Automática
    start_pause_index = int(num_puntos * 0.5)
    end_pause_index = int(num_puntos * 0.6)
    df.loc[start_pause_index:end_pause_index, 'Ritmo_Min_Km'] = np.nan
    
    # Generación de datos de "Intensidad" para el Mapa de Calor
    # Simulamos que la intensidad es inversamente proporcional al Ritmo (Ritmo más rápido = Mayor Intensidad)
    df['Intensidad'] = 1 / df['Ritmo_Min_Km'].fillna(9.0) * 10 
    df['Intensidad'] = df['Intensidad'].clip(0.5, 3.0) # Normalizar la intensidad
    
    return df

def calcular_metricas_clave(df_actividad):
    """
    Calcula las métricas principales basadas en la simulación.
    """
    distancia_km = 0.68
    duracion_seg = df_actividad['Tiempo_Segundos'].max()
    duracion_str = str(timedelta(seconds=int(duracion_seg)))
    ritmo_min_seg = "62:46"
    calorias = 91
    
    return {
        "Distancia (km)": f"{distancia_km:.2f}",
        "Ritmo medio (min/km)": ritmo_min_seg,
        "Duración": duracion_str,
        "Calorías [kcal]": str(calorias),
        "FC Promedio": f"{int(df_actividad['FC_BPM'].mean())} BPM",
        "Cadencia Promedio": f"{int(df_actividad['Cadencia_Pasos_Min'].mean())} spm"
    }

# --- 2. Lógica de Inicio de Sesión y Configuración ---

st.set_page_config(layout="wide", page_title="🏃 Seguimiento de Actividad")
st.markdown("""
<style>
.stDeployButton {display:none;}
.st-emotion-cache-vk3wpw {display:none;}
</style>
""", unsafe_allow_html=True)

# Inicializar el estado de la sesión si no existe
if 'actividad_iniciada' not in st.session_state:
    st.session_state['actividad_iniciada'] = False

# Función para iniciar la actividad
def iniciar_actividad():
    st.session_state['actividad_iniciada'] = True

# --- Interfaz Inicial ---
if not st.session_state['actividad_iniciada']:
    st.title("🏃 Aplicación de Seguimiento Deportivo")
    st.markdown("### ¡Tu entrenador personal y comunidad de running te esperan!")
    st.markdown("""
    Esta aplicación simula el seguimiento GPS en tiempo real, planes de entrenamiento y análisis detallado,
    incluyendo funcionalidades Premium como **Pausa Automática** y **Entrenamiento por Intervalos**.
    """)
    st.image("https://images.unsplash.com/photo-1571026079085-306915f0134f?fit=crop&w=800&q=80") 
    st.write(" ")
    if st.button("▶️ INICIAR ACTIVIDAD", type="primary", use_container_width=True):
        iniciar_actividad()
    st.markdown("---")
    st.info("Haz clic en 'INICIAR ACTIVIDAD' para simular el seguimiento en tiempo real.")
else:
    # --- Interfaz de Seguimiento (Una vez iniciada la actividad) ---

    # 3. Cargar y Calcular Datos (Simulación en "Tiempo Real")
    df_actividad = simular_datos_actividad()
    metricas = calcular_metricas_clave(df_actividad)

    # ----------------------------------------------------
    # 🌐 1. Seguimiento y Monitoreo de Actividades (GPS)
    # ----------------------------------------------------

    # --- 3.1. Diseño de Métricas (Replicando la imagen) ---
    col_distancia, col_ritmo, col_calorias, col_duracion = st.columns([1, 1, 1, 1])
    
    col_distancia.markdown(
        f"<p style='font-size: 4em; font-weight: bold; text-align: center; line-height: 0.9;'>{metricas['Distancia (km)']}</p>", 
        unsafe_allow_html=True
    )
    col_distancia.markdown(
        f"<p style='font-size: 1em; text-align: center; margin-top: -10px;'>Distancia [km]</p>", 
        unsafe_allow_html=True
    )

    with st.container():
        cols_inferiores = st.columns([1, 1, 1])
        
        cols_inferiores[0].markdown(
            f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Ritmo medio (min/km)']}</p>", 
            unsafe_allow_html=True
        )
        cols_inferiores[0].markdown(
            f"<p style='font-size: 0.9em; text-align: center;'>Ritmo medio (min/km)</p>", 
            unsafe_allow_html=True
        )

        cols_inferiores[1].markdown(
            f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Calorías [kcal]']}</p>", 
            unsafe_allow_html=True
        )
        cols_inferiores[1].markdown(
            f"<p style='font-size: 0.9em; text-align: center;'>Calorías [kcal]</p>", 
            unsafe_allow_html=True
        )
        
        cols_inferiores[2].markdown(
            f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Duración']}</p>", 
            unsafe_allow_html=True
        )
        cols_inferiores[2].markdown(
            f"<p style='font-size: 0.9em; text-align: center;'>Duración</p>", 
            unsafe_allow_html=True
        )

    st.markdown("---") # Separador visual

    # --- 3.2. Mapeo de la Ruta (Ruta y Mapa de Calor) ---
    st.subheader("Ruta y Mapa de Calor (Intensidad Simulada)")
    
    # Coordenadas iniciales para centrar el mapa
    coords_centrales = [df_actividad['Latitud'].mean(), df_actividad['Longitud'].mean()]

    m = folium.Map(location=coords_centrales, 
                   zoom_start=15, 
                   tiles="cartodbpositron",
                   height=450)

    # 1. Agregar el Mapa de Calor
    # Creamos una lista de [Latitud, Longitud, Intensidad]
    data_heatmap = df_actividad[['Latitud', 'Longitud', 'Intensidad']].values.tolist()
    HeatMap(data_heatmap, radius=15).add_to(m)
    
    # 2. Agregar la ruta (Línea de la actividad)
    ruta_activa = df_actividad[['Latitud', 'Longitud']].dropna()
    if not ruta_activa.empty:
        folium.PolyLine(ruta_activa.values, color="#F00000", weight=3, opacity=0.6).add_to(m)
        
        # Marcador de posición actual (simulado)
        folium.Marker(
            [ruta_activa.iloc[-1]['Latitud'], ruta_activa.iloc[-1]['Longitud']],
            tooltip="Posición Actual",
            icon=folium.Icon(color="black", icon="circle", prefix='fa')
        ).add_to(m)

    folium_static(m, width=700, height=450)
    

    # --- 3.3. Controles Inferiores ---
    st.markdown("---")
    col_pausa, col_bloqueo, col_finalizar = st.columns(3)

    if col_pausa.button("🔴 PAUSA"):
        st.info("Actividad en Pausa Automática o Manual. El seguimiento se ha detenido.")

    if col_bloqueo.button("🔒 BLOQUEAR Pantalla"):
        st.warning("Pantalla bloqueada para evitar toques accidentales.")

    if col_finalizar.button("✅ FINALIZAR"):
        st.success("Actividad finalizada. Pasando al **Análisis y Estadísticas**.")

    st.markdown("---")

    # [Otras Secciones (Análisis, Intervalos, Récords) seguirían aquí...]
    st.subheader("📈 Análisis de Pausa Automática")
    tiempo_total = metricas['Duración']
    tiempo_movimiento_seg = df_actividad['Ritmo_Min_Km'].dropna().shape[0] / df_actividad.shape[0] * df_actividad['Tiempo_Segundos'].max()
    tiempo_pausa_seg = df_actividad['Tiempo_Segundos'].max() - tiempo_movimiento_seg
    tiempo_pausa_str = str(timedelta(seconds=int(tiempo_pausa_seg)))
    st.metric("Tiempo en Pausa (Autopausa)", tiempo_pausa_str)
