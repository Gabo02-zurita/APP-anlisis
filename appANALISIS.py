import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import timedelta
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static

# --- 1. Funciones de Simulación y Cálculo Progresivo ---

# Datos base para la actividad (Simularemos una actividad de 2560 segundos, aprox. 42:40 minutos)
TOTAL_SEGUNDOS = 2560
DISTANCIA_TOTAL_KM = 5.0 # Usaremos una distancia más realista de 5.0 km para el tiempo dado.

@st.cache_data
def generar_datos_actividad(num_puntos=100):
    """Genera datos estáticos de la actividad para asegurar consistencia en la simulación."""
    lat_base, lon_base = -1.2683, -78.6186 
    
    data = {
        'Tiempo_Segundos': np.linspace(0, TOTAL_SEGUNDOS, num_puntos), 
        'Latitud': lat_base + np.cumsum(np.random.normal(0, 0.00005, num_puntos)),
        'Longitud': lon_base + np.cumsum(np.random.normal(0, 0.00008, num_puntos)),
        # Ritmo instantáneo simulado (en segundos/km).
        'Ritmo_Inst_Seg_Km': np.random.uniform(270, 420, num_puntos) 
    }
    df = pd.DataFrame(data)
    
    # 2. Simulación de Pausa Automática (Autopausa)
    start_pause_index = int(num_puntos * 0.5)
    end_pause_index = int(num_puntos * 0.6)
    # Un ritmo muy alto (ej. 1000 segundos/km) simula una pausa / movimiento muy lento
    df.loc[start_pause_index:end_pause_index, 'Ritmo_Inst_Seg_Km'] = 1000
    
    return df

def calcular_metricas_acumuladas(df_parcial, punto_actual, tiempo_en_movimiento_seg):
    """Calcula las métricas usando solo los datos acumulados hasta el punto actual."""
    
    df_actual = df_parcial.iloc[:punto_actual].copy()
    
    # 1. Duración Total
    duracion_seg = df_actual['Tiempo_Segundos'].iloc[-1]
    duracion_str = str(timedelta(seconds=int(duracion_seg)))

    # 2. Distancia (Calculo simplificado basado en el tiempo y ritmo)
    # La distancia se calcula inversamente a partir del Ritmo y el tiempo entre puntos.
    # Para la simulación, usaremos una aproximación proporcional al tiempo.
    distancia_km = (duracion_seg / TOTAL_SEGUNDOS) * DISTANCIA_TOTAL_KM
    
    # 3. Ritmo Medio (Tiempo total en movimiento / Distancia total)
    if distancia_km > 0:
        ritmo_promedio_seg_km = tiempo_en_movimiento_seg / distancia_km
        minutos = int(ritmo_promedio_seg_km // 60)
        segundos = int(ritmo_promedio_seg_km % 60)
        ritmo_promedio_str = f"{minutos:02d}:{segundos:02d}"
    else:
        ritmo_promedio_str = "--:--"

    # 4. Calorías (Estimación: 50 kcal/km, ajustable)
    calorias_quemadas = int(distancia_km * 50) 
    
    return {
        "Distancia (km)": f"{distancia_km:.2f}",
        "Duración": duracion_str,
        "Ritmo medio (min/km)": ritmo_promedio_str,
        "Calorías [kcal]": str(calorias_quemadas)
    }

# --- 2. Lógica de Streamlit y Bucle de Tiempo Real ---

st.set_page_config(layout="wide", page_title="🏃 Seguimiento de Actividad T. Real")
st.markdown("""
<style>
.stDeployButton {display:none;}
.st-emotion-cache-vk3wpw {display:none;}
</style>
""", unsafe_allow_html=True)

# Inicializar estado de la sesión
if 'actividad_iniciada' not in st.session_state:
    st.session_state['actividad_iniciada'] = False

def iniciar_actividad():
    st.session_state['actividad_iniciada'] = True

# --- Interfaz Inicial ---
if not st.session_state['actividad_iniciada']:
    st.title("🏃 Aplicación de Seguimiento Deportivo")
    st.markdown("### Simulación de Seguimiento en Tiempo Real")
    st.markdown("El sistema calculará y actualizará dinámicamente las métricas y la ruta en el mapa.")
    st.image("https://images.unsplash.com/photo-1571026079085-306915f0134f?fit=crop&w=800&q=80") 
    st.write(" ")
    if st.button("▶️ INICIAR ACTIVIDAD", type="primary", use_container_width=True):
        iniciar_actividad()
else:
    st.title("🟢 ACTIVIDAD EN CURSO (Tiempo Real)")
    
    # Generar los datos base
    df_actividad = generar_datos_actividad(num_puntos=50) # Menos puntos para que la simulación sea más rápida
    num_puntos = len(df_actividad)
    
    # Contenedores para actualizar dinámicamente las métricas y el mapa
    metricas_placeholder = st.empty()
    mapa_placeholder = st.empty()
    controles_placeholder = st.empty()
    
    tiempo_en_movimiento = 0.0

    # --- BUCLE DE SIMULACIÓN DE TIEMPO REAL ---
    for i in range(1, num_puntos):
        
        # 1. Control de Simulación (Pausa Automática)
        # Asumimos que si el ritmo instantáneo es > 900 (simulando 15 min/km), está en pausa
        intervalo_tiempo = df_actividad['Tiempo_Segundos'].iloc[i] - df_actividad['Tiempo_Segundos'].iloc[i-1]
        
        # Solo acumular tiempo si no es una pausa simulada
        if df_actividad['Ritmo_Inst_Seg_Km'].iloc[i] < 900:
            tiempo_en_movimiento += intervalo_tiempo
            estado_pausa = "RUNNING"
        else:
            estado_pausa = "PAUSA AUTOMÁTICA"
        
        # 2. Calcular Métricas Acumuladas
        metricas = calcular_metricas_acumuladas(df_actividad, i + 1, tiempo_en_movimiento)
        
        # 3. Dibujar las Métricas Dinámicamente (Replicando el formato de la imagen)
        with metricas_placeholder.container():
            st.markdown(f"**Estado:** {estado_pausa}")
            
            # Fila superior y diseño de la imagen
            col_distancia, _, _, _ = st.columns([1, 1, 1, 1])

            col_distancia.markdown(
                f"<p style='font-size: 4em; font-weight: bold; text-align: center; line-height: 0.9;'>{metricas['Distancia (km)']}</p>", 
                unsafe_allow_html=True
            )
            col_distancia.markdown(
                f"<p style='font-size: 1em; text-align: center; margin-top: -10px;'>Distancia [km]</p>", 
                unsafe_allow_html=True
            )

            cols_inferiores = st.columns([1, 1, 1])
            
            cols_inferiores[0].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Ritmo medio (min/km)']}</p>", unsafe_allow_html=True)
            cols_inferiores[0].markdown("<p style='font-size: 0.9em; text-align: center;'>Ritmo medio (min/km)</p>", unsafe_allow_html=True)
            
            cols_inferiores[1].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Calorías [kcal]']}</p>", unsafe_allow_html=True)
            cols_inferiores[1].markdown("<p style='font-size: 0.9em; text-align: center;'>Calorías [kcal]</p>", unsafe_allow_html=True)
            
            cols_inferiores[2].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas['Duración']}</p>", unsafe_allow_html=True)
            cols_inferiores[2].markdown("<p style='font-size: 0.9em; text-align: center;'>Duración</p>", unsafe_allow_html=True)
            st.markdown("---")

        # 4. Dibujar el Mapa Dinámicamente
        with mapa_placeholder.container():
            st.subheader("Ruta en Tiempo Real (Simulada)")
            df_ruta_parcial = df_actividad.iloc[:i+1]
            coords_actuales = [df_ruta_parcial['Latitud'].iloc[-1], df_ruta_parcial['Longitud'].iloc[-1]]
            
            m = folium.Map(location=coords_actuales, 
                        zoom_start=15, 
                        tiles="cartodbpositron",
                        height=400)

            # Mapa de Calor (Simulación)
            df_heatmap_parcial = df_ruta_parcial[['Latitud', 'Longitud']]
            # Usar una intensidad fija solo para mostrar la densidad de la ruta
            data_heatmap = [[row['Latitud'], row['Longitud'], 1] for index, row in df_heatmap_parcial.iterrows()]
            HeatMap(data_heatmap, radius=15).add_to(m)
            
            # Línea de la ruta recorrida
            folium.PolyLine(df_ruta_parcial[['Latitud', 'Longitud']].values, color="blue", weight=3, opacity=0.8).add_to(m)
            
            # Marcador de Posición Actual
            folium.Marker(
                coords_actuales,
                tooltip="Tú aquí",
                icon=folium.Icon(color="red", icon="circle", prefix='fa')
            ).add_to(m)

            folium_static(m, width=700, height=400)
            


        # 5. Dibujar Controles
        with controles_placeholder.container():
            col_pausa, col_bloqueo, col_finalizar = st.columns(3)
            col_pausa.button("🔴 PAUSA", key="pausa_loop")
            col_bloqueo.button("🔒 BLOQUEAR Pantalla", key="bloqueo_loop")
            col_finalizar.button("✅ FINALIZAR", key="finalizar_loop")


        # Simular el paso del tiempo (Actualización cada 0.2 segundos)
        time.sleep(0.2)
        
    # --- FIN DEL BUCLE DE SIMULACIÓN ---
    st.success("Actividad Finalizada. ¡Revisa el Análisis y Estadísticas!")
    st.balloons()
