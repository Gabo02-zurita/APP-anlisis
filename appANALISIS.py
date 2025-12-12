import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import timedelta
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static

# --- Configuración y Datos Estáticos ---
TOTAL_SEGUNDOS = 2560
DISTANCIA_TOTAL_KM = 5.0 

st.set_page_config(layout="wide", page_title="🏃 App Fitness - Historial y Récords")
st.markdown("""
<style>
.stDeployButton {display:none;}
.st-emotion-cache-vk3wpw {display:none;}
</style>
""", unsafe_allow_html=True)


# --- 1. Funciones de Simulación y Cálculo ---

@st.cache_data
def generar_datos_actividad(num_puntos=50):
    """Genera datos estáticos de la actividad (5.0 km en 42:40)."""
    lat_base, lon_base = -1.2683, -78.6186 
    
    data = {
        'Tiempo_Segundos': np.linspace(0, TOTAL_SEGUNDOS, num_puntos), 
        'Latitud': lat_base + np.cumsum(np.random.normal(0, 0.00005, num_puntos)),
        'Longitud': lon_base + np.cumsum(np.random.normal(0, 0.00008, num_puntos)),
        'Ritmo_Inst_Seg_Km': np.random.uniform(270, 420, num_puntos) 
    }
    df = pd.DataFrame(data)
    
    # Simulación de Pausa Automática
    start_pause_index = int(num_puntos * 0.5)
    end_pause_index = int(num_puntos * 0.6)
    df.loc[start_pause_index:end_pause_index, 'Ritmo_Inst_Seg_Km'] = 1000 # Simula pausa
    return df

def calcular_metricas_acumuladas(df_parcial, punto_actual, tiempo_en_movimiento_seg):
    """Calcula las métricas principales al finalizar la actividad."""
    
    df_actual = df_parcial.iloc[:punto_actual].copy()
    duracion_seg = df_actual['Tiempo_Segundos'].iloc[-1]
    distancia_km = (duracion_seg / TOTAL_SEGUNDOS) * DISTANCIA_TOTAL_KM
    
    ritmo_promedio_str = "--:--"
    if distancia_km > 0 and tiempo_en_movimiento_seg > 0:
        ritmo_promedio_seg_km = tiempo_en_movimiento_seg / distancia_km
        minutos = int(ritmo_promedio_seg_km // 60)
        segundos = int(ritmo_promedio_seg_km % 60)
        ritmo_promedio_str = f"{minutos:02d}:{segundos:02d}"

    calorias_quemadas = int(distancia_km * 50) 
    
    return {
        "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "Distancia (km)": distancia_km,
        "Duración (seg)": int(duracion_seg),
        "Ritmo Medio (s/km)": ritmo_promedio_seg_km if distancia_km > 0 else 0,
        "Calorías (kcal)": calorias_quemadas,
        "Tiempo Movimiento (s)": int(tiempo_en_movimiento_seg)
    }

def formatear_metricas_visual(metricas_dict):
    """Formatea los valores para la visualización en la interfaz."""
    ritmo_min = int(metricas_dict["Ritmo Medio (s/km)"] // 60)
    ritmo_seg = int(metricas_dict["Ritmo Medio (s/km)"] % 60)
    
    return {
        "Distancia (km)": f"{metricas_dict['Distancia (km)']:.2f}",
        "Duración": str(timedelta(seconds=metricas_dict['Duración (seg)'])),
        "Ritmo medio (min/km)": f"{ritmo_min:02d}:{ritmo_seg:02d}",
        "Calorías [kcal]": str(metricas_dict['Calorías (kcal)'])
    }

# --- 2. Funciones de Gestión de Historial y Récords ---

def inicializar_estado():
    """Inicializa variables de estado, historial y récords."""
    if 'actividad_iniciada' not in st.session_state:
        st.session_state['actividad_iniciada'] = False
        st.session_state['actividad_finalizada'] = False
    
    if 'historial_actividades' not in st.session_state:
        # Crea un DataFrame vacío para el historial
        st.session_state['historial_actividades'] = pd.DataFrame(columns=[
            "Fecha", "Distancia (km)", "Duración (seg)", "Ritmo Medio (s/km)", "Calorías (kcal)", "Tiempo Movimiento (s)"
        ])
        
    if 'ultimas_metricas' not in st.session_state:
        st.session_state['ultimas_metricas'] = {}

def guardar_actividad(metricas_finales):
    """Guarda la actividad actual en el historial y resetea el estado."""
    
    # Crea un DataFrame de una sola fila con los resultados
    nueva_actividad_df = pd.DataFrame([metricas_finales])
    
    # Concatena al historial existente
    st.session_state['historial_actividades'] = pd.concat([st.session_state['historial_actividades'], nueva_actividad_df], ignore_index=True)
    
    # Guarda las métricas para mostrarlas en la pantalla de análisis
    st.session_state['ultimas_metricas'] = metricas_finales
    
    # Marca como finalizada y resetea 'iniciada' para volver a la pantalla de análisis
    st.session_state['actividad_finalizada'] = True
    st.session_state['actividad_iniciada'] = False

def calcular_records():
    """Calcula si la última actividad logró algún Récord Personal (RP)."""
    historial = st.session_state['historial_actividades']
    if historial.empty:
        return []
    
    rp_logrados = []
    ultima_actividad = st.session_state['ultimas_metricas']
    
    # Récord 1: Distancia más larga
    max_distancia = historial['Distancia (km)'].max()
    if ultima_actividad['Distancia (km)'] >= max_distancia:
         # Usamos > estricto o >= para incluir la actividad actual
         rp_logrados.append(f"Distancia más larga: {max_distancia:.2f} km")
         
    # Récord 2: Ritmo más rápido (semanal, simulado en 5K)
    # Buscamos la actividad más cercana a 5K para simular el RP en 5K
    distancia_ideal = 5.0
    # Encuentra la actividad en el historial con la distancia más cercana a 5.0 km
    historial['Diferencia_5K'] = abs(historial['Distancia (km)'] - distancia_ideal)
    # Filtra solo las actividades que están "cerca" (ej. 4.5km - 5.5km)
    candidatos_5k = historial[historial['Diferencia_5K'] <= 0.5]

    if not candidatos_5k.empty:
        # El mejor ritmo es el Ritmo Medio MÁS BAJO (menor tiempo/km)
        mejor_ritmo_seg = candidatos_5k['Ritmo Medio (s/km)'].min()
        
        # Comparamos el ritmo de la actividad actual con el mejor ritmo histórico
        if ultima_actividad['Ritmo Medio (s/km)'] <= mejor_ritmo_seg:
             min_r = int(mejor_ritmo_seg // 60)
             sec_r = int(mejor_ritmo_seg % 60)
             rp_logrados.append(f"Mejor Ritmo en 5K: {min_r:02d}:{sec_r:02d} /km")

    return rp_logrados

# --- 3. Renderizado de Interfaz ---

def renderizar_interfaz_seguimiento():
    """Bucle principal para la simulación en tiempo real."""
    st.title("🟢 ACTIVIDAD EN CURSO (Tiempo Real)")
    
    df_actividad = generar_datos_actividad(num_puntos=50) 
    num_puntos = len(df_actividad)
    
    metricas_placeholder = st.empty()
    mapa_placeholder = st.empty()
    
    tiempo_en_movimiento = 0.0

    # Bucle de simulación
    for i in range(1, num_puntos):
        
        intervalo_tiempo = df_actividad['Tiempo_Segundos'].iloc[i] - df_actividad['Tiempo_Segundos'].iloc[i-1]
        
        # Pausa Automática
        if df_actividad['Ritmo_Inst_Seg_Km'].iloc[i] < 900:
            tiempo_en_movimiento += intervalo_tiempo
            estado_pausa = "RUNNING"
        else:
            estado_pausa = "PAUSA AUTOMÁTICA"
        
        # Calcular Métricas Acumuladas
        metricas_crudo = calcular_metricas_acumuladas(df_actividad, i + 1, tiempo_en_movimiento)
        metricas_visual = formatear_metricas_visual(metricas_crudo)
        
        # --- Dibujar Métricas Dinámicamente ---
        with metricas_placeholder.container():
            st.markdown(f"**Estado:** {estado_pausa}")
            
            col_distancia, _, _, _ = st.columns([1, 1, 1, 1])
            col_distancia.markdown(
                f"<p style='font-size: 4em; font-weight: bold; text-align: center; line-height: 0.9;'>{metricas_visual['Distancia (km)']}</p>", unsafe_allow_html=True
            )
            col_distancia.markdown(
                f"<p style='font-size: 1em; text-align: center; margin-top: -10px;'>Distancia [km]</p>", unsafe_allow_html=True
            )

            cols_inferiores = st.columns([1, 1, 1])
            cols_inferiores[0].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas_visual['Ritmo medio (min/km)']}</p>", unsafe_allow_html=True)
            cols_inferiores[0].markdown("<p style='font-size: 0.9em; text-align: center;'>Ritmo medio (min/km)</p>", unsafe_allow_html=True)
            
            cols_inferiores[1].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas_visual['Calorías [kcal]']}</p>", unsafe_allow_html=True)
            cols_inferiores[1].markdown("<p style='font-size: 0.9em; text-align: center;'>Calorías [kcal]</p>", unsafe_allow_html=True)
            
            cols_inferiores[2].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas_visual['Duración']}</p>", unsafe_allow_html=True)
            cols_inferiores[2].markdown("<p style='font-size: 0.9em; text-align: center;'>Duración</p>", unsafe_allow_html=True)
            st.markdown("---")

        # --- Dibujar el Mapa Dinámicamente ---
        with mapa_placeholder.container():
            st.subheader("Ruta en Tiempo Real con Intensidad")
            df_ruta_parcial = df_actividad.iloc[:i+1]
            coords_actuales = [df_ruta_parcial['Latitud'].iloc[-1], df_ruta_parcial['Longitud'].iloc[-1]]
            
            m = folium.Map(location=coords_actuales, zoom_start=15, tiles="cartodbpositron", height=400)

            # Mapa de Calor (Simulación)
            df_heatmap_parcial = df_ruta_parcial[['Latitud', 'Longitud']]
            data_heatmap = [[row['Latitud'], row['Longitud'], 1] for index, row in df_heatmap_parcial.iterrows()]
            HeatMap(data_heatmap, radius=15).add_to(m)
            
            folium.PolyLine(df_ruta_parcial[['Latitud', 'Longitud']].values, color="blue", weight=3, opacity=0.8).add_to(m)
            
            folium.Marker(coords_actuales, tooltip="Tú aquí", icon=folium.Icon(color="red", icon="circle", prefix='fa')).add_to(m)

            folium_static(m, width=700, height=400)

        # Controles
        col_pausa, col_finalizar = st.columns(2)
        if col_pausa.button("🔴 PAUSA", key="pausa_loop"):
            st.warning("Pausa manual activada. La simulación continuará cuando la desactives.")
            # Si el usuario hace clic en PAUSA, salimos del bucle para esperar la acción siguiente (simplificado)
            break 
            
        if col_finalizar.button("✅ FINALIZAR", key="finalizar_loop"):
            # Si el usuario hace clic en FINALIZAR, guardamos el estado actual y salimos
            guardar_actividad(metricas_crudo)
            break
        
        time.sleep(0.2)
        
    # Si el bucle termina normalmente (la actividad se completa)
    if i == num_puntos - 1 and st.session_state['actividad_iniciada']:
        guardar_actividad(metricas_crudo)
        

def renderizar_pantalla_analisis():
    """Muestra el resumen, el historial y los récords al finalizar la actividad."""
    
    st.title("✅ Análisis y Estadísticas de la Sesión")
    st.subheader("Resumen de la Actividad Reciente")
    
    metricas_crudo = st.session_state['ultimas_metricas']
    metricas_visual = formatear_metricas_visual(metricas_crudo)
    
    cols = st.columns(4)
    cols[0].metric("Distancia", metricas_visual['Distancia (km)'] + " km")
    cols[1].metric("Duración", metricas_visual['Duración'])
    cols[2].metric("Ritmo Medio", metricas_visual['Ritmo medio (min/km)'] + " /km")
    cols[3].metric("Calorías", metricas_visual['Calorías [kcal]'] + " kcal")

    st.markdown("---")

    # --- Cálculo y Visualización de Récords Personales ---
    st.subheader("🏆 Récords Personales (RP)")
    records = calcular_records()
    
    if records:
        st.balloons()
        st.success("¡Felicidades! Lograste nuevos Récords Personales:")
        for record in records:
            st.markdown(f"* **{record}**")
    else:
        st.info("No se lograron nuevos Récords Personales en esta sesión. ¡Sigue entrenando!")

    st.markdown("---")
    
    # --- Historial Completo ---
    st.subheader("Historial Completo de Actividades")
    historial_df = st.session_state['historial_actividades'].copy()
    
    if not historial_df.empty:
        # Formatear el DataFrame para una mejor visualización
        historial_df['Duración'] = historial_df['Duración (seg)'].apply(lambda x: str(timedelta(seconds=x)))
        historial_df['Ritmo Medio'] = historial_df['Ritmo Medio (s/km)'].apply(lambda x: f"{int(x // 60):02d}:{int(x % 60):02d}")
        
        # Seleccionar y renombrar las columnas a mostrar
        historial_mostrar = historial_df[['Fecha', 'Distancia (km)', 'Duración', 'Ritmo Medio', 'Calorías (kcal)']]
        historial_mostrar.columns = ['Fecha', 'Distancia (km)', 'Duración Total', 'Ritmo Promedio (min/km)', 'Calorías']
        
        st.dataframe(historial_mostrar.sort_values(by='Fecha', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.warning("Aún no tienes actividades registradas en tu historial.")
        
    st.markdown("---")
    if st.button("⬅️ VOLVER A INICIO"):
        st.session_state['actividad_finalizada'] = False
        st.rerun() # Reinicia la aplicación para mostrar la pantalla de inicio

# --- Lógica Principal de Control de Flujo ---

inicializar_estado()

if st.session_state['actividad_finalizada']:
    renderizar_pantalla_analisis()
elif st.session_state['actividad_iniciada']:
    renderizar_interfaz_seguimiento()
else:
    st.title("🏃 Aplicación de Seguimiento Deportivo")
    st.markdown("### ¡Tu entrenador personal y comunidad de running te esperan!")
    st.markdown("Haz clic para comenzar la simulación de seguimiento en tiempo real. Los resultados se guardarán en tu historial.")
    st.image("https://images.unsplash.com/photo-1571026079085-306915f0134f?fit=crop&w=800&q=80") 
    st.write(" ")
    if st.button("▶️ INICIAR ACTIVIDAD", type="primary", use_container_width=True):
        st.session_state['actividad_iniciada'] = True
        st.rerun() # Reinicia la aplicación para entrar en el bucle de seguimiento
        # Simular el paso del tiempo (Actualización cada 0.2 segundos)
        time.sleep(0.2)
        
    # --- FIN DEL BUCLE DE SIMULACIÓN ---
    st.success("Actividad Finalizada. ¡Revisa el Análisis y Estadísticas!")
    st.balloons()
