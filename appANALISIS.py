import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import folium
from streamlit_folium import folium_static

# --- 1. Funciones de Simulación y Cálculo de Métricas ---

def simular_datos_actividad(num_puntos=100):
    """
    Simula datos de actividad (similar a un archivo GPX/TCX) para el panel de Streamlit.
    """
    # Usaremos coordenadas simuladas cerca de Ambato (Ecuador), inspiradas en la imagen
    lat_base, lon_base = -1.2683, -78.6186 

    data = {
        'Tiempo_Segundos': np.linspace(0, 2560, num_puntos), # 42:40 minutos totales (2560 segundos)
        'Latitud': lat_base + np.cumsum(np.random.normal(0, 0.00005, num_puntos)),
        'Longitud': lon_base + np.cumsum(np.random.normal(0, 0.00008, num_puntos)),
        'Ritmo_Min_Km': np.random.uniform(5.0, 7.5, num_puntos), # Ritmo más lento para simular el 62:46 /km
        'FC_BPM': np.random.normal(135, 10, num_puntos).clip(100, 160).astype(int),
        'Cadencia_Pasos_Min': np.random.normal(155, 10, num_puntos).clip(130, 175).astype(int)
    }
    df = pd.DataFrame(data)
    
    # 2. Simulación de Pausa Automática (Autopausa - Premium)
    # Simulamos que los puntos del 50% al 60% del tiempo fueron una pausa (ritmo NaN)
    start_pause_index = int(num_puntos * 0.5)
    end_pause_index = int(num_puntos * 0.6)
    df.loc[start_pause_index:end_pause_index, 'Ritmo_Min_Km'] = np.nan
    
    return df

def calcular_metricas_clave(df_actividad):
    """
    Calcula las métricas basándose en los valores de la imagen proporcionada (Distancia: 0.68, Duración: 42:40, Ritmo: 62:46).
    """
    # Métrica 1: Distancia (Directa de la imagen)
    distancia_km = 0.68

    # Métrica 2: Duración Total (Directa de la imagen, 42 minutos y 40 segundos)
    duracion_seg = df_actividad['Tiempo_Segundos'].max()
    duracion_str = str(timedelta(seconds=int(duracion_seg)))

    # Métrica 3: Ritmo Promedio (Directo de la imagen, pero formateado)
    ritmo_min_seg = "62:46" # Se asume 62 minutos y 46 segundos por km (Muy lento, puede ser error de la imagen o ritmo de caminata muy lenta)

    # Métrica 4: Calorías (Directa de la imagen)
    calorias = 91
    
    return {
        "Distancia (km)": f"{distancia_km:.2f}",
        "Ritmo medio (min/km)": ritmo_min_seg,
        "Duración": duracion_str,
        "Calorías [kcal]": str(calorias),
        "FC Promedio": f"{int(df_actividad['FC_BPM'].mean())} BPM",
        "Cadencia Promedio": f"{int(df_actividad['Cadencia_Pasos_Min'].mean())} spm"
    }

# --- 2. Cargar y Calcular Datos ---
df_actividad = simular_datos_actividad()
metricas = calcular_metricas_clave(df_actividad)

# --- 3. Configuración Inicial y Título ---
st.set_page_config(layout="wide", page_title="🏃 Seguimiento de Actividad")
# Ocultar el menú de Streamlit para un aspecto más limpio
st.markdown("""
<style>
.stDeployButton {display:none;}
.st-emotion-cache-vk3wpw {display:none;}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------
# 🌐 1. Seguimiento y Monitoreo de Actividades (GPS)
# ----------------------------------------------------

# --- 3.1. Diseño de Métricas (Replicando la imagen) ---
col_distancia, col_ritmo, col_calorias, col_duracion = st.columns([1, 1, 1, 1])

# Fila superior (Métrica de Distancia grande)
col_distancia.markdown(
    f"<p style='font-size: 4em; font-weight: bold; text-align: center; line-height: 0.9;'>{metricas['Distancia (km)']}</p>", 
    unsafe_allow_html=True
)
col_distancia.markdown(
    f"<p style='font-size: 1em; text-align: center; margin-top: -10px;'>Distancia [km]</p>", 
    unsafe_allow_html=True
)


# Fila inferior (Ritmo, Calorías, Duración)
# Usamos un contenedor principal para el resto del contenido
with st.container():
    cols_inferiores = st.columns([1, 1, 1])
    
    # Ritmo
    cols_inferiores[0].markdown(
        f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Ritmo medio (min/km)']}</p>", 
        unsafe_allow_html=True
    )
    cols_inferiores[0].markdown(
        f"<p style='font-size: 0.9em; text-align: center;'>Ritmo medio (min/km)</p>", 
        unsafe_allow_html=True
    )

    # Calorías
    cols_inferiores[1].markdown(
        f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Calorías [kcal]']}</p>", 
        unsafe_allow_html=True
    )
    cols_inferiores[1].markdown(
        f"<p style='font-size: 0.9em; text-align: center;'>Calorías [kcal]</p>", 
        unsafe_allow_html=True
    )
    
    # Duración
    cols_inferiores[2].markdown(
        f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Duración']}</p>", 
        unsafe_allow_html=True
    )
    cols_inferiores[2].markdown(
        f"<p style='font-size: 0.9em; text-align: center;'>Duración</p>", 
        unsafe_allow_html=True
    )

st.markdown("---") # Separador visual

# --- 3.2. Mapeo de la Ruta (Ruta) ---
# Coordenadas iniciales para centrar el mapa
coords_centrales = [df_actividad['Latitud'].mean(), df_actividad['Longitud'].mean()]

m = folium.Map(location=coords_centrales, 
               zoom_start=15, 
               tiles="cartodbpositron",
               height=450)

# Agregar la ruta
ruta_activa = df_actividad[['Latitud', 'Longitud']].dropna()
if not ruta_activa.empty:
    folium.PolyLine(ruta_activa.values, color="#F00000", weight=5, opacity=0.8).add_to(m)
    # Marcador de inicio
    folium.Marker(
        [ruta_activa.iloc[0]['Latitud'], ruta_activa.iloc[0]['Longitud']],
        tooltip="Inicio",
        icon=folium.Icon(color="green", icon="play", prefix='fa')
    ).add_to(m)
    # Marcador de posición actual (simulado al final de la ruta)
    folium.Marker(
        [ruta_activa.iloc[-1]['Latitud'], ruta_activa.iloc[-1]['Longitud']],
        tooltip="Posición Actual",
        icon=folium.Icon(color="black", icon="circle", prefix='fa')
    ).add_to(m)

st.subheader("Ruta en Tiempo Real (Simulada)")
folium_static(m, width=700, height=450)

# --- 3.3. Controles Inferiores (Pausa/Finalizar Simulación) ---
st.markdown("---")
col_pausa, col_bloqueo, col_finalizar = st.columns(3)

if col_pausa.button("🔴 PAUSA"):
    st.info("Actividad en Pausa Automática o Manual. El seguimiento se ha detenido.")

if col_bloqueo.button("🔒 BLOQUEAR Pantalla"):
    st.warning("Pantalla bloqueada para evitar toques accidentales.")

if col_finalizar.button("✅ FINALIZAR"):
    st.success("Actividad finalizada. Pasando al **Análisis y Estadísticas**.")

st.markdown("---")

# ----------------------------------------------------
# 📈 3. Análisis y Estadísticas (Métricas Adicionales)
# ----------------------------------------------------

st.subheader("Análisis Detallado de la Sesión")
cols_analisis = st.columns(3)
cols_analisis[0].metric("Frecuencia Cardíaca (BPM)", metricas['FC Promedio'])
cols_analisis[1].metric("Cadencia (Pasos/min)", metricas['Cadencia Promedio'])

# Mostrar la simulación de Pausa Automática
tiempo_total = metricas['Duración']
tiempo_movimiento_seg = df_actividad['Ritmo_Min_Km'].dropna().shape[0] / df_actividad.shape[0] * df_actividad['Tiempo_Segundos'].max()
tiempo_pausa_seg = df_actividad['Tiempo_Segundos'].max() - tiempo_movimiento_seg
tiempo_pausa_str = str(timedelta(seconds=int(tiempo_pausa_seg)))

cols_analisis[2].metric("Tiempo en Pausa (Autopausa)", tiempo_pausa_str)
st.info("La **Pausa Automática (Autopausa - Premium)** se activó durante 05:08, excluyendo este tiempo del cálculo de Ritmo en Movimiento.")

# ----------------------------------------------------
# 🎯 2. Planes de Entrenamiento y Coaching
# ----------------------------------------------------

st.markdown("---")
st.header("🎯 Planes de Entrenamiento y Coaching")

st.markdown("""
Esta sección simula la interfaz para crear y seguir un **Entrenamiento por Intervalos (Premium)**.
""")

with st.expander("➕ Crear Sesión de Intervalos (Premium)"):
    st.markdown("Define tus segmentos de entrenamiento de alta y baja intensidad.")
    
    # Simulación de la interfaz de creación de intervalos
    num_repeticiones = st.slider("Número de Repeticiones", 1, 20, 8)
    tiempo_rapido = st.number_input("Tiempo de Tramos Rápidos (segundos)", 30, 300, 60)
    tiempo_recuperacion = st.number_input("Tiempo de Recuperación (segundos)", 30, 300, 90)

    if st.button("Guardar Entrenamiento de Intervalos"):
        st.success(f"Sesión guardada: {num_repeticiones} repeticiones de {tiempo_rapido}s (rápido) / {tiempo_recuperacion}s (recuperación).")

st.info("El **Entrenador por Voz** te guiaría en tiempo real a través de estos cambios de ritmo.")

# ----------------------------------------------------
# 3. 📈 Récords Personales
# ----------------------------------------------------

st.markdown("---")
st.subheader("Récords Personales")
st.warning("Estás a **0.32 km** de tu distancia más corta registrada de 1 km.")

st.markdown("""
* **Mejor 5K:** 25:30
* **Distancia Más Larga:** 15.0 km
* **Nuevo Logro:** Primera actividad en el sector **"Río Payamino"**.
""")
