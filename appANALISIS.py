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
MAPA_ACTUALIZAR_CADA = 5 # El mapa se actualiza cada 5 puntos.

st.set_page_config(layout="wide", page_title="🏃 App Fitness - Historial y Récords")
st.markdown("""
<style>
.stDeployButton {display:none;}
.st-emotion-cache-vk3wpw {display:none;}
</style>
""", unsafe_allow_html=True)


# --- 1. Funciones de Simulación y Cálculo (Se mantienen sin cambios) ---

@st.cache_data
def generar_datos_actividad(num_puntos=50):
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
    df_actual = df_parcial.iloc[:punto_actual].copy()
    duracion_seg = df_actual['Tiempo_Segundos'].iloc[-1]
    distancia_km = (duracion_seg / TOTAL_SEGUNDOS) * DISTANCIA_TOTAL_KM
    
    ritmo_promedio_seg_km = 0
    if distancia_km > 0 and tiempo_en_movimiento_seg > 0:
        ritmo_promedio_seg_km = tiempo_en_movimiento_seg / distancia_km

    calorias_quemadas = int(distancia_km * 50)
    
    return {
        "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "Distancia (km)": distancia_km,
        "Duración (seg)": int(duracion_seg),
        "Ritmo Medio (s/km)": ritmo_promedio_seg_km,
        "Calorías (kcal)": calorias_quemadas,
        "Tiempo Movimiento (s)": int(tiempo_en_movimiento_seg)
    }

def formatear_metricas_visual(metricas_dict):
    ritmo_min = int(metricas_dict["Ritmo Medio (s/km)"] // 60)
    ritmo_seg = int(metricas_dict["Ritmo Medio (s/km)"] % 60)
    
    return {
        "Distancia (km)": f"{metricas_dict['Distancia (km)']:.2f}",
        "Duración": str(timedelta(seconds=metricas_dict['Duración (seg)'])),
        "Ritmo medio (min/km)": f"{ritmo_min:02d}:{ritmo_seg:02d}",
        "Calorías [kcal]": str(metricas_dict['Calorías (kcal)'])
    }

# --- 2. Funciones de Gestión de Historial y Récords (Se mantienen sin cambios) ---

def inicializar_estado():
    if 'actividad_iniciada' not in st.session_state:
        st.session_state['actividad_iniciada'] = False
        st.session_state['actividad_finalizada'] = False
    
    if 'historial_actividades' not in st.session_state:
        st.session_state['historial_actividades'] = pd.DataFrame(columns=["Fecha", "Distancia (km)", "Duración (seg)", "Ritmo Medio (s/km)", "Calorías (kcal)", "Tiempo Movimiento (s)"])
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

def calcular_records():
    historial = st.session_state['historial_actividades'].copy()
    if historial.empty:
        return []
    
    rp_logrados = []
    ultima_actividad = st.session_state['ultimas_metricas']
    
    # Récord: Distancia más larga
    max_distancia_historica = historial['Distancia (km)'].max()
    if ultima_actividad['Distancia (km)'] >= max_distancia_historica and ultima_actividad['Distancia (km)'] > historial.iloc[-2]['Distancia (km)']:
         rp_logrados.append(f"Distancia más larga: {ultima_actividad['Distancia (km)']:.2f} km")
         
    # Récord: Ritmo más rápido (Simulado para 5K)
    candidatos_5k = historial[(historial['Distancia (km)'] >= 4.5) & (historial['Distancia (km)'] <= 5.5)]
    if not candidatos_5k.empty:
        mejor_ritmo_seg = candidatos_5k['Ritmo Medio (s/km)'].min()
        
        if ultima_actividad['Ritmo Medio (s/km)'] < mejor_ritmo_seg:
             min_r = int(ultima_actividad['Ritmo Medio (s/km)'] // 60)
             sec_r = int(ultima_actividad['Ritmo Medio (s/km)'] % 60)
             rp_logrados.append(f"Mejor Ritmo en 5K: {min_r:02d}:{sec_r:02d} /km")

    return rp_logrados

# --- 3. Renderizado de Interfaz ---

def renderizar_interfaz_seguimiento():
    """
    Bucle principal para la simulación en tiempo real.
    Estructura optimizada para evitar el error 'removeChild'.
    """
    st.title("🟢 ACTIVIDAD EN CURSO (Tiempo Real)")
    
    df_actividad = generar_datos_actividad(num_puntos=50) 
    num_puntos = len(df_actividad)
    
    # 🛑 CAMBIO CLAVE: Usamos st.empty() para los placehoders sin anidamiento de st.container()
    metricas_placeholder = st.empty()
    mapa_placeholder = st.empty()
    controles_placeholder = st.empty() # Placeholder para los botones
    
    tiempo_en_movimiento = 0.0

    # Bucle de simulación
    for i in range(1, num_puntos):
        
        intervalo_tiempo = df_actividad['Tiempo_Segundos'].iloc[i] - df_actividad['Tiempo_Segundos'].iloc[i-1]
        
        # Pausa Automática Lógica
        if df_actividad['Ritmo_Inst_Seg_Km'].iloc[i] < 900:
            tiempo_en_movimiento += intervalo_tiempo
            estado_pausa = "RUNNING"
        else:
            estado_pausa = "PAUSA AUTOMÁTICA"
        
        # Calcular Métricas Acumuladas
        metricas_crudo = calcular_metricas_acumuladas(df_actividad, i + 1, tiempo_en_movimiento)
        metricas_visual = formatear_metricas_visual(metricas_crudo)
        
        # --- Dibujar Métricas Dinámicamente (Actualización rápida) ---
        with metricas_placeholder:
            st.markdown(f"**Estado:** {estado_pausa} | Tiempo Total: {metricas_visual['Duración']}")
            
            # Diseño de la imagen proporcionada (Distancia grande, el resto abajo)
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


        # --- Dibujar el Mapa Dinámicamente (Corrección clave: solo actualizar de vez en cuando) ---
        if i % MAPA_ACTUALIZAR_CADA == 0 or i == num_puntos - 1:
            with mapa_placeholder:
                st.subheader("Ruta en Tiempo Real con Intensidad")
                df_ruta_parcial = df_actividad.iloc[:i+1]
                coords_actuales = [df_ruta_parcial['Latitud'].iloc[-1], df_ruta_parcial['Longitud'].iloc[-1]]
                
                m = folium.Map(location=coords_actuales, zoom_start=15, tiles="cartodbpositron", height=400)

                # Mapa de Calor (Intensidad simulada)
                df_heatmap_parcial = df_ruta_parcial[['Latitud', 'Longitud']]
                data_heatmap = [[row['Latitud'], row['Longitud'], 1] for index, row in df_heatmap_parcial.iterrows()]
                HeatMap(data_heatmap, radius=15).add_to(m)
                
                folium.PolyLine(df_ruta_parcial[['Latitud', 'Longitud']].values, color="blue", weight=3, opacity=0.8).add_to(m)
                
                folium.Marker(coords_actuales, tooltip="Tú aquí", icon=folium.Icon(color="red", icon="circle", prefix='fa')).add_to(m)

                folium_static(m, width=700, height=400)
                


        # Controles (Actualización rápida)
        with controles_placeholder:
            col_pausa, col_finalizar = st.columns(2)
            # 🛑 CLAVE: Para evitar el error de los botones, deben tener un 'key' único 
            # y se deben envolver en el placeholder para su redibujado
            if col_pausa.button("🔴 PAUSA", key=f"pausa_loop_{i}"):
                st.warning("Pausa manual activada.")
                guardar_actividad(metricas_crudo) # Guardamos el progreso antes de salir
                st.rerun()
            
            if col_finalizar.button("✅ FINALIZAR", key=f"finalizar_loop_{i}"):
                guardar_actividad(metricas_crudo)
                st.rerun()

        time.sleep(0.2)
        
    # Si el bucle termina normalmente
    if i == num_puntos - 1 and st.session_state['actividad_iniciada']:
        guardar_actividad(metricas_crudo)
        st.rerun()
        

def renderizar_pantalla_analisis():
    """Muestra el resumen, el historial y los récords al finalizar la actividad."""
    
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
    st.markdown("Esta simulación incluye: **Seguimiento GPS, Historial de Actividad, Récords Personales** y funciones **Premium**.")
    st.image("https://images.unsplash.com/photo-1571026079085-306915f0134f?fit=crop&w=800&q=80") 
    st.write(" ")
    if st.button("▶️ INICIAR ACTIVIDAD", type="primary", use_container_width=True):
        st.session_state['actividad_iniciada'] = True
        st.rerun()
    st.write(" ")
    if st.button("▶️ INICIAR ACTIVIDAD", type="primary", use_container_width=True):
        st.session_state['actividad_iniciada'] = True
        st.rerun()
