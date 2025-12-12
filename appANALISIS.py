import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import folium
from streamlit_folium import folium_static

# --- Configuración Inicial y Título ---
st.set_page_config(layout="wide", page_title="🏃 Panel de Análisis de Actividad")

st.title("🏃‍♀️ Running App Analytics (Panel Streamlit)")
st.caption("Visualización de métricas y rutas de actividades deportivas.")

# --- Funciones de Cálculo de Métricas ---

def simular_datos_actividad(num_puntos=50):
    """
    Simula datos de una actividad de running (similar a un archivo GPX/TCX).
    """
    # Coordenadas base (ej. cerca de un parque)
    lat_base, lon_base = 40.7128, -74.0060  # Nueva York (ejemplo)

    data = {
        'Tiempo_Segundos': np.linspace(0, 3600, num_puntos), # 1 hora de actividad
        'Latitud': lat_base + np.cumsum(np.random.normal(0, 0.001, num_puntos)),
        'Longitud': lon_base + np.cumsum(np.random.normal(0, 0.0015, num_puntos)),
        'Ritmo_Min_Km': np.random.uniform(4.0, 6.5, num_puntos),
        'FC_BPM': np.random.normal(140, 15, num_puntos).clip(100, 180).astype(int),
        'Cadencia_Pasos_Min': np.random.normal(165, 5, num_puntos).clip(140, 180).astype(int)
    }
    df = pd.DataFrame(data)
    # Simulación de Pausa Automática (si el Ritmo es muy lento, se asume pausa)
    df.loc[df['Ritmo_Min_Km'] > 6.0, 'Ritmo_Min_Km'] = np.nan
    return df

def calcular_metricas_totales(df_actividad):
    """
    Calcula las métricas principales de la actividad.
    """
    # 1. Distancia (Simulada, asumiendo una ruta de 10km)
    distancia_km = 10.0

    # 2. Duración
    duracion_seg = df_actividad['Tiempo_Segundos'].max()
    duracion_str = str(timedelta(seconds=int(duracion_seg)))

    # 3. Tiempo en Movimiento (Excluyendo Pausas)
    puntos_movimiento = df_actividad['Ritmo_Min_Km'].dropna().shape[0]
    tiempo_movimiento_seg = (puntos_movimiento / df_actividad.shape[0]) * duracion_seg
    tiempo_movimiento_str = str(timedelta(seconds=int(tiempo_movimiento_seg)))

    # 4. Ritmo Promedio (Tiempo en Movimiento / Distancia)
    ritmo_promedio_seg_km = tiempo_movimiento_seg / distancia_km
    minutos = int(ritmo_promedio_seg_km // 60)
    segundos = int(ritmo_promedio_seg_km % 60)
    ritmo_promedio_str = f"{minutos:02d}:{segundos:02d} /km"

    # 5. Calorías (Estimación simple)
    peso_kg = 70  # Asunción: se usaría el peso real del usuario
    calorias_quemadas = int(distancia_km * peso_kg * 1.05 / 5) # Estimación MUY simplificada
    
    # 6. FC y Cadencia Promedio (En Movimiento)
    fc_promedio = int(df_actividad['FC_BPM'].mean())
    cadencia_promedio = int(df_actividad['Cadencia_Pasos_Min'].mean())
    
    return {
        "Distancia (km)": f"{distancia_km:.2f}",
        "Duración Total": duracion_str,
        "Tiempo en Movimiento": tiempo_movimiento_str,
        "Ritmo Promedio": ritmo_promedio_str,
        "Calorías Quemadas": f"{calorias_quemadas} kcal",
        "FC Promedio": f"{fc_promedio} BPM",
        "Cadencia Promedio": f"{cadencia_promedio} spm"
    }

# --- Cargar y Simular Datos ---
df_actividad = simular_datos_actividad(num_puntos=200)
metricas = calcular_metricas_totales(df_actividad)

# ----------------------------------------------------
# 1. 🌐 Seguimiento y Monitoreo de Actividades (GPS)
# ----------------------------------------------------

st.header("1. Seguimiento y Monitoreo de Actividades")
st.subheader("Ruta Mapeada")

# Crear el mapa de Folium
m = folium.Map(location=[df_actividad['Latitud'].mean(), df_actividad['Longitud'].mean()], 
               zoom_start=14, 
               tiles="cartodbpositron")

# Agregar la ruta (solo los puntos que no están en pausa)
ruta = df_actividad[['Latitud', 'Longitud']].dropna()
if not ruta.empty:
    folium.PolyLine(ruta.values, color="red", weight=4.5, opacity=0.8).add_to(m)
    # Marcador de inicio
    folium.Marker(
        [ruta.iloc[0]['Latitud'], ruta.iloc[0]['Longitud']],
        popup="Inicio",
        icon=folium.Icon(color="green", icon="play", prefix='fa')
    ).add_to(m)
    # Marcador de fin
    folium.Marker(
        [ruta.iloc[-1]['Latitud'], ruta.iloc[-1]['Longitud']],
        popup="Fin",
        icon=folium.Icon(color="darkred", icon="flag", prefix='fa')
    ).add_to(m)

# Mostrar el mapa usando Streamlit
folium_static(m, width=700, height=450)


# Mostrar las métricas clave en columnas (Registro de Datos)
st.subheader("Métricas Vitales de la Sesión")
cols = st.columns(7)

metricas_claves = ["Distancia (km)", "Duración Total", "Ritmo Promedio", "Calorías Quemadas", "FC Promedio", "Cadencia Promedio", "Tiempo en Movimiento"]
for i, key in enumerate(metricas_claves):
    cols[i].metric(label=key, value=metricas[key])

st.markdown("---")

# ----------------------------------------------------
# 3. 📈 Análisis y Estadísticas
# ----------------------------------------------------

st.header("3. Análisis y Estadísticas")
st.subheader("Evolución de las Métricas de Rendimiento")

# Preparar datos para gráficos (reemplazar NaN en el ritmo para la visualización)
df_chart = df_actividad.copy()
df_chart['Ritmo_Min_Km_Interp'] = df_chart['Ritmo_Min_Km'].interpolate(method='linear')

# Gráfico de Ritmo Instantáneo
st.line_chart(df_chart[['Tiempo_Segundos', 'Ritmo_Min_Km_Interp']].set_index('Tiempo_Segundos'), 
              use_container_width=True)
st.markdown("> **Ritmo Instantáneo:** Muestra el cambio de ritmo a lo largo del tiempo. Las secciones más bajas son las más rápidas. Se han interpolado los datos faltantes (pausas) para una mejor visualización de la línea.")

# Gráfico de Frecuencia Cardíaca y Cadencia
st.line_chart(df_chart[['Tiempo_Segundos', 'FC_BPM', 'Cadencia_Pasos_Min']].set_index('Tiempo_Segundos'),
              use_container_width=True)
st.markdown("> **Frecuencia Cardíaca y Cadencia:** Seguimiento de la respuesta fisiológica y la eficiencia de la zancada (spm = pasos por minuto).")



st.markdown("---")

# ----------------------------------------------------
# 4. 🧑‍🤝‍🧑 Comunidad y Motivación (Simulación de Récords)
# ----------------------------------------------------

st.header("4. Récords Personales y Etiquetado")
st.success("🎉 ¡Nuevo Récord Personal! ¡Mejor tiempo en 10K!")

st.markdown("""
- **Mejor 5K:** 25:30 (Anterior: 26:15)
- **Mejor 10K:** 52:45 **(¡Nuevo Récord!)**
- **Distancia Más Larga:** 15.0 km
""")

st.subheader("👟 Etiquetado de Calzado")
# Simulación de un selector y registro de uso de zapatillas
zapatillas = st.selectbox(
    "Selecciona el par de zapatillas usado:",
    ("Nike Pegasus 39 (Uso: 350 km)", "Adidas Ultraboost (Uso: 150 km)", "Nuevo Par")
)

if st.button("Registrar actividad a estas zapatillas"):
    st.info(f"Actividad de **10.0 km** registrada al calzado: **{zapatillas}**.")
    st.warning("Recomendación: ¡Las Nike Pegasus 39 están cerca de su vida útil (aprox. 500-800 km)!.")

# ----------------------------------------------------
# 2. 🎯 Planes de Entrenamiento (Simulación de Interfaz)
# ----------------------------------------------------

st.markdown("---")
st.header("2. Planes de Entrenamiento y Coaching (Simulación)")
st.info("Esta sección simula la interfaz para seleccionar un plan.")

plan_seleccionado = st.radio(
    "Elige tu meta de entrenamiento:",
    ('Preparación para Maratón (42K)', 'Mejorar Velocidad (Intervalos)', 'Entrenamiento Básico 5K'),
    index=0
)

if plan_seleccionado == 'Preparación para Maratón (42K)':
    st.success("Plan adaptativo activo. Tu entrenamiento de hoy: **Rodaje Largo de 22 km (Zona 2)**.")
    st.audio("audio_entrenador_simulado.mp3", format="audio/mp3", start_time=0) # Simulación de Entrenador por Voz
    st.markdown("*(Simulación de audio: 'Muy bien, mantén el ritmo constante. Estás en la Zona 2. Llevas 15 minutos.')*")
