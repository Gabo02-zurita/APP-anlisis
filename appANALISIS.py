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
MAPA_ACTUALIZAR_CADA = 5 
NUM_PUNTOS_SIMULACION = 50

st.set_page_config(layout="wide", page_title="🏃 App Fitness - Historial y Récords")
st.markdown("""
<style>
.stDeployButton {display:none;}
.st-emotion-cache-vk3wpw {display:none;}
</style>
""", unsafe_allow_html=True)


# --- 1. Funciones de Simulación y Cálculo ---

@st.cache_data
def generar_datos_actividad(num_puntos=NUM_PUNTOS_SIMULACION):
    """Genera datos estáticos de la actividad. Se ejecuta una sola vez."""
    lat_base, lon_base = -1.2683, -78.6186
    data = {
        'Tiempo_Segundos': np.linspace(0, TOTAL_SEGUNDOS, num_puntos), 
        'Latitud': lat_base + np.cumsum(np.random.normal(0, 0.00005, num_puntos)),
        'Longitud': lon_base + np.cumsum(np.random.normal(0, 0.00008, num_puntos)),
        'Ritmo_Inst_Seg_Km': np.random.uniform(270, 420, num_puntos) 
    }
    df = pd.DataFrame(data)
    start_pause_index = int(num_puntos * 0.5)
    end_pause_index = int(num_puntos * 0.6)
    df.loc[start_pause_index:end_pause_index, 'Ritmo_Inst_Seg_Km'] = 1000 
    return df

def calcular_metricas_acumuladas(df_parcial, punto_actual, tiempo_en_movimiento_seg):
    """Calcula las métricas principales según el índice actual."""
    
    # Manejar el caso donde el punto actual excede los datos disponibles
    if punto_actual >= len(df_parcial):
        punto_actual = len(df_parcial)
        
    df_actual = df_parcial.iloc[:punto_actual].copy()
    
    # Si estamos en el punto 0, inicializamos las métricas
    if punto_actual == 0:
        return {
            "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Distancia (km)": 0.0,
            "Duración (seg)": 0,
            "Ritmo Medio (s/km)": 0,
            "Calorías (kcal)": 0,
            "Tiempo Movimiento (s)": 0
        }

    duracion_seg = df_actual['Tiempo_Segundos'].iloc[-1]
    distancia_km = (duracion_seg / TOTAL_SEGUNDOS) * DISTANCIA_TOTAL_KM
    
    # Calcular el tiempo de movimiento hasta este punto
    tiempo_movimiento_total = 0
    for i in range(1, punto_actual):
        intervalo_tiempo = df_parcial['Tiempo_Segundos'].iloc[i] - df_parcial['Tiempo_Segundos'].iloc[i-1]
        if df_parcial['Ritmo_Inst_Seg_Km'].iloc[i] < 900:
            tiempo_movimiento_total += intervalo_tiempo
            
    ritmo_promedio_seg_km = 0
    if distancia_km > 0 and tiempo_movimiento_total > 0:
        ritmo_promedio_seg_km = tiempo_movimiento_total / distancia_km

    calorias_quemadas = int(distancia_km * 50)
    
    return {
        "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "Distancia (km)": distancia_km,
        "Duración (seg)": int(duracion_seg),
        "Ritmo Medio (s/km)": ritmo_promedio_seg_km,
        "Calorías (kcal)": calorias_quemadas,
        "Tiempo Movimiento (s)": int(tiempo_movimiento_total)
    }

def formatear_metricas_visual(metricas_dict):
    """Formatea los valores para la visualización en la interfaz."""
    ritmo_s_km = metricas_dict.get("Ritmo Medio (s/km)", 0)
    
    ritmo_min = int(ritmo_s_km // 60)
    ritmo_seg = int(ritmo_s_km % 60)
    
    return {
        "Distancia (km)": f"{metricas_dict['Distancia (km)']:.2f}",
        "Duración": str(timedelta(seconds=metricas_dict['Duración (seg)'])),
        "Ritmo medio (min/km)": f"{ritmo_min:02d}:{ritmo_seg:02d}",
        "Calorías [kcal]": str(metricas_dict['Calorías (kcal)'])
    }

# --- 2. Funciones de Gestión de Estado (Historial y Récords) ---

def inicializar_estado():
    if 'actividad_iniciada' not in st.session_state:
        st.session_state['actividad_iniciada'] = False
        st.session_state['actividad_finalizada'] = False
    
    if 'indice_simulacion' not in st.session_state:
        st.session_state['indice_simulacion'] = 0 # Nuevo contador para el avance

    if 'historial_actividades' not in st.session_state:
        st.session_state['historial_actividades'] = pd.DataFrame(columns=[
            "Fecha", "Distancia (km)", "Duración (seg)", "Ritmo Medio (s/km)", "Calorías (kcal)", "Tiempo Movimiento (s)"
        ])
        if st.session_state['historial_actividades'].empty:
             st.session_state['historial_actividades'] = pd.DataFrame([{
                 "Fecha": "2025-12-01 10:00", "Distancia (km)": 4.0, "Duración (seg)": 1500, "Ritmo Medio (s/km)": 375, "Calorías (kcal)": 200, "Tiempo Movimiento (s)": 1500
             },
             {
                 "Fecha": "2025-12-08 18:30", "Distancia (km)": 5.5, "Duración (seg)": 2000, "Ritmo Medio (s/km)": 363.6, "Calorías (kcal)": 275, "Tiempo Movimiento (s)": 2000
             }])

    if 'ultimas_metricas' not in st.session_state:
        st.session_state['ultimas_metricas'] = {}

def guardar_actividad(metricas_finales):
    nueva_actividad_df = pd.DataFrame([metricas_finales])
    st.session_state['historial_actividades'] = pd.concat([st.session_state['historial_actividades'], nueva_actividad_df], ignore_index=True)
    st.session_state['ultimas_metricas'] = metricas_finales
    st.session_state['actividad_finalizada'] = True
    st.session_state['actividad_iniciada'] = False
    st.session_state['indice_simulacion'] = 0 # Reiniciar contador al finalizar

def avanzar_simulacion():
    """Incrementa el índice y fuerza el redibujado."""
    if st.session_state['indice_simulacion'] < NUM_PUNTOS_SIMULACION:
        st.session_state['indice_simulacion'] += 1
        st.rerun()

def finalizar_actividad_manual(df_actividad):
    """Calcula y guarda el estado actual al finalizar manualmente."""
    indice_actual = st.session_state['indice_simulacion']
    
    # Recalculamos el tiempo de movimiento hasta el punto actual
    tiempo_movimiento_final = 0
    for i in range(1, indice_actual + 1):
        intervalo_tiempo = df_actividad['Tiempo_Segundos'].iloc[i] - df_actividad['Tiempo_Segundos'].iloc[i-1]
        if df_actividad['Ritmo_Inst_Seg_Km'].iloc[i] < 900:
            tiempo_movimiento_final += intervalo_tiempo
            
    metricas_finales = calcular_metricas_acumuladas(df_actividad, indice_actual, tiempo_movimiento_final)
    guardar_actividad(metricas_finales)
    st.rerun()

def calcular_records():
    # Lógica de cálculo de récords (se mantiene igual)
    historial = st.session_state['historial_actividades'].copy()
    if historial.empty:
        return []
    
    rp_logrados = []
    ultima_actividad = st.session_state['ultimas_metricas']
    
    max_distancia_historica = historial['Distancia (km)'].max()
    if ultima_actividad['Distancia (km)'] >= max_distancia_historica and ultima_actividad['Distancia (km)'] > historial.iloc[-2]['Distancia (km)']:
         rp_logrados.append(f"Distancia más larga: {ultima_actividad['Distancia (km)']:.2f} km")
         
    candidatos_5k = historial[(historial['Distancia (km)'] >= 4.5) & (historial['Distancia (km)'] <= 5.5)]
    if not candidatos_5k.empty:
        mejor_ritmo_seg = candidatos_5k['Ritmo Medio (s/km)'].min()
        
        if ultima_actividad['Ritmo Medio (s/km)'] < mejor_ritmo_seg and ultima_actividad['Ritmo Medio (s/km)'] > 0:
             min_r = int(ultima_actividad['Ritmo Medio (s/km)'] // 60)
             sec_r = int(ultima_actividad['Ritmo Medio (s/km)'] % 60)
             rp_logrados.append(f"Mejor Ritmo en 5K: {min_r:02d}:{sec_r:02d} /km")

    return rp_logrados

# --- 3. Renderizado de Interfaz (Optimizado para Estabilidad) ---

def renderizar_interfaz_seguimiento():
    """Interfaz de seguimiento reactiva, sin bucle 'for'."""
    st.title("🟢 ACTIVIDAD EN CURSO (Simulación Estática)")
    
    df_actividad = generar_datos_actividad(num_puntos=NUM_PUNTOS_SIMULACION) 
    i = st.session_state['indice_simulacion'] # Usamos el índice de la sesión

    # Calcular el tiempo de movimiento hasta el punto actual (necesario fuera del bucle)
    tiempo_en_movimiento = 0
    if i > 0:
        for k in range(1, i + 1):
            intervalo_tiempo = df_actividad['Tiempo_Segundos'].iloc[k] - df_actividad['Tiempo_Segundos'].iloc[k-1]
            if df_actividad['Ritmo_Inst_Seg_Km'].iloc[k] < 900:
                tiempo_en_movimiento += intervalo_tiempo
    
    metricas_crudo = calcular_metricas_acumuladas(df_actividad, i, tiempo_en_movimiento)
    metricas_visual = formatear_metricas_visual(metricas_crudo)
    
    # Determinar el estado para la visualización
    if i == 0:
        estado_pausa = "ESPERANDO INICIO"
    elif df_actividad['Ritmo_Inst_Seg_Km'].iloc[i-1] < 900:
        estado_pausa = "RUNNING"
    else:
        estado_pausa = "PAUSA AUTOMÁTICA"

    # --- 3.1. Dibujar Métricas (Estructura más simple) ---
    st.markdown(f"**Estado:** {estado_pausa} | Tiempo Total: {metricas_visual['Duración']}")
    
    # Contenedor para Distancia (Formato Grande)
    col_distancia, _, _, _ = st.columns([1, 1, 1, 1])
    col_distancia.markdown(
        f"<p style='font-size: 4em; font-weight: bold; text-align: center; line-height: 0.9;'>{metricas_visual['Distancia (km)']}</p>", unsafe_allow_html=True
    )
    col_distancia.markdown(
        f"<p style='font-size: 1em; text-align: center; margin-top: -10px;'>Distancia [km]</p>", unsafe_allow_html=True
    )

    # Contenedor para el resto de métricas (Fila inferior)
    cols_inferiores = st.columns([1, 1, 1])
    cols_inferiores[0].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas_visual['Ritmo medio (min/km)']}</p>", unsafe_allow_html=True)
    cols_inferiores[0].markdown("<p style='font-size: 0.9em; text-align: center;'>Ritmo medio (min/km)</p>", unsafe_allow_html=True)
    
    cols_inferiores[1].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas_visual['Calorías [kcal]']}</p>", unsafe_allow_html=True)
    cols_inferiores[1].markdown("<p style='font-size: 0.9em; text-align: center;'>Calorías [kcal]</p>", unsafe_allow_html=True)
    
    cols_inferiores[2].markdown(f"<p style='font-size: 2.5em; font-weight: bold; text-align: center; line-height: 1.0;'>{metricas_visual['Duración']}</p>", unsafe_allow_html=True)
    cols_inferiores[2].markdown("<p style='font-size: 0.9em; text-align: center;'>Duración</p>", unsafe_allow_html=True)
    st.markdown("---")


    # --- 3.2. Dibujar Mapa (Solo en ciertas condiciones) ---
    st.subheader("Ruta en Tiempo Real con Intensidad")
    
    if i % MAPA_ACTUALIZAR_CADA == 0 and i > 0: # Solo actualizamos si el índice lo permite y no es el inicio
        df_ruta_parcial = df_actividad.iloc[:i]
        coords_actuales = [df_ruta_parcial['Latitud'].iloc[-1], df_ruta_parcial['Longitud'].iloc[-1]]
        
        m = folium.Map(location=coords_actuales, zoom_start=15, tiles="cartodbpositron", height=400)
        
        # Mapa de Calor y Polilínea
        df_heatmap_parcial = df_ruta_parcial[['Latitud', 'Longitud']]
        data_heatmap = [[row['Latitud'], row['Longitud'], 1] for index, row in df_heatmap_parcial.iterrows()]
        HeatMap(data_heatmap, radius=15).add_to(m)
        folium.PolyLine(df_ruta_parcial[['Latitud', 'Longitud']].values, color="blue", weight=3, opacity=0.8).add_to(m)
        folium.Marker(coords_actuales, tooltip="Tú aquí", icon=folium.Icon(color="red", icon="circle", prefix='fa')).add_to(m)

        folium_static(m, width=700, height=400)
        
    else:
        st.info(f"Mapa estático. Se actualizará en el punto de datos {i + 1} de {NUM_PUNTOS_SIMULACION}.")
    
    st.markdown("---")

    # --- 3.3. Controles de Avance y Finalización ---
    
    if i < NUM_PUNTOS_SIMULACION:
        col_pausa, col_finalizar, col_avance = st.columns([1, 1, 1])
        
        if col_pausa.button("🔴 PAUSA", key="pausa_manual"):
             st.warning("Pausa manual activada. Avanza la simulación para continuar.")
             # No forzamos rerun, simplemente esperamos el siguiente evento.
        
        if col_finalizar.button("✅ FINALIZAR Y GUARDAR", type="primary"):
            finalizar_actividad_manual(df_actividad)
        
        # Este botón reemplaza el bucle time.sleep
        if col_avance.button(f"▶️ AVANZAR SIMULACIÓN ({i+1}/{NUM_PUNTOS_SIMULACION})"):
            avanzar_simulacion()
            
    else:
        # Si la simulación ha llegado al final, guardamos y vamos a análisis
        if not st.session_state['actividad_finalizada']:
            finalizar_actividad_manual(df_actividad)
            
        st.success("Actividad Finalizada. ¡Revisa el Análisis y Estadísticas!")


def renderizar_pantalla_analisis():
    # Lógica de renderizado del análisis (se mantiene igual)
    
    st.title("✅ Análisis y Estadísticas de la Sesión")
    
    tab_resumen, tab_historial, tab_entrenamiento = st.tabs(["Resumen y Récords", "Historial Completo", "Planes y Coaching"])
    
    with tab_resumen:
        st.subheader("Resumen de la Actividad Reciente")
        
        metricas_crudo = st.session_state['ultimas_metricas']
        metricas_visual = formatear_metricas_visual(metricas_crudo)
        
        cols = st.columns(4)
        cols[0].metric("Distancia", metricas_visual['Distancia (km)'] + " km")
        cols[1].metric("Duración", metricas_visual['Duración'])
        cols[2].metric("Ritmo Medio", metricas_visual['Ritmo medio (min/km)'] + " /km")
        cols[3].metric("Calorías", metricas_visual['Calorías [kcal]'] + " kcal")

        st.markdown("---")

        st.subheader("🏆 Récords Personales (RP)")
        records = calcular_records()
        
        if records:
            st.balloons()
            st.success("¡Felicidades! Lograste nuevos Récords Personales:")
            for record in records:
                st.markdown(f"* **{record}**")
        else:
            st.info("No se lograron nuevos Récords Personales en esta sesión. ¡Sigue entrenando!")

    with tab_historial:
        st.subheader("Historial Completo de Actividades")
        historial_df = st.session_state['historial_actividades'].copy()
        
        if not historial_df.empty:
            historial_df['Duración Total'] = historial_df['Duración (seg)'].apply(lambda x: str(timedelta(seconds=int(x))))
            historial_df['Ritmo Promedio (min/km)'] = historial_df['Ritmo Medio (s/km)'].apply(lambda x: f"{int(x // 60):02d}:{int(x % 60):02d}")
            
            historial_mostrar = historial_df[['Fecha', 'Distancia (km)', 'Duración Total', 'Ritmo Promedio (min/km)', 'Calorías (kcal)']]
            historial_mostrar.columns = ['Fecha', 'Distancia (km)', 'Duración Total', 'Ritmo Promedio', 'Calorías']
            
            st.dataframe(historial_mostrar.sort_values(by='Fecha', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.warning("Aún no tienes actividades registradas en tu historial.")
            
    with tab_entrenamiento:
        st.subheader("🎯 Planes de Entrenamiento y Coaching (Simulación)")
        st.markdown("---")
        
        st.info("Esta sección simula la interfaz para crear y seguir un **Entrenamiento por Intervalos (Premium)**.")

        with st.expander("➕ Crear Sesión de Intervalos (Premium)"):
            num_repeticiones = st.slider("Número de Repeticiones", 1, 20, 8)
            tiempo_rapido = st.number_input("Tiempo de Tramos Rápidos (segundos)", 30, 300, 60)
            tiempo_recuperacion = st.number_input("Tiempo de Recuperación (segundos)", 30, 300, 90)

            if st.button("Guardar Entrenamiento de Intervalos"):
                st.success(f"Sesión guardada: {num_repeticiones} repeticiones de {tiempo_rapido}s (rápido) / {tiempo_recuperacion}s (recuperación).")
        
        st.markdown("---")
        st.subheader("🏅 adiClub y Recompensas (Simulación)")
        st.metric("Puntos adiClub Ganados en esta actividad", "25 Puntos")
        st.progress(0.75, "75% para el Nivel Gold (500 Puntos restantes)")
        st.info("¡Gana puntos al registrar actividades para canjear por productos o experiencias!")

    st.markdown("---")
    if st.button("⬅️ VOLVER A INICIO"):
        st.session_state['actividad_finalizada'] = False
        st.rerun()

# --- Lógica Principal de Control de Flujo ---

inicializar_estado()

if st.session_state['actividad_finalizada']:
    renderizar_pantalla_analisis()
elif st.session_state['actividad_iniciada']:
    renderizar_interfaz_seguimiento()
else:
    # Pantalla de Inicio
    st.title("🏃 Aplicación de Seguimiento Deportivo")
    st.markdown("### ¡Tu entrenador personal y comunidad de running te esperan!")
    st.markdown("Esta simulación es **extremadamente estable** y evita errores de *redibujado* al basarse en clicks para avanzar la actividad.")
    st.image("https://images.unsplash.com/photo-1571026079085-306915f0134f?fit=crop&w=800&q=80") 
    st.write(" ")
    if st.button("▶️ INICIAR ACTIVIDAD", type="primary", use_container_width=True):
        st.session_state['actividad_iniciada'] = True
        st.session_state['indice_simulacion'] = 0 # Asegurar inicio en 0
        st.rerun()
