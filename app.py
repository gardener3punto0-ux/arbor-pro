import streamlit as st
import openai
import os
import base64
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from dotenv import load_dotenv
from streamlit_js_eval import get_geolocation
import folium
from streamlit_folium import st_folium

# 1. NÚCLEO Y SEGURIDAD
load_dotenv()
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=api_key)

st.set_page_config(page_title="ARBORICULTURA", layout="wide", initial_sidebar_state="collapsed")

# 2. ESTILO UI ANDROID NATIVA
st.markdown("""
<style>
.main { background-color: #f1f3f2; padding: 0px; }
.stButton>button {
    width: 100%; border-radius: 20px; height: 4.2em;
    background: linear-gradient(135deg, #1b5e20 0%, #388e3c 100%);
    color: white; font-weight: bold; border: none;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.stTabs [data-baseweb="tab-list"] {
    background-color: #1b5e20; position: sticky; top: 0; z-index: 999;
}
.stTabs [data-baseweb="tab"] { color: #c8e6c9 !important; font-size: 14px; }
.stTabs [aria-selected="true"] { border-bottom: 4px solid #ffffff !important; color: white !important; }
.biblio-card {
    background: white; border-radius: 15px; padding: 25px; margin-bottom: 20px;
    border-left: 10px solid #1b5e20; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
h3 { color: #1b5e20; border-bottom: 2px solid #81c784; padding-bottom: 8px; margin-top: 0px; }
</style>
""", unsafe_allow_html=True)

# 3. BASE DE DATOS
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS informes 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, analisis TEXT, imagenes TEXT, gps TEXT, riesgo TEXT)''')
conn.commit()

# 4. INTERFAZ
st.title("🌲 ARBORICULTURA PRO ELITE")
t1, t2, t3 = st.tabs(["📸 INSPECCIÓN", "🗄️ HISTORIAL", "📚 BIBLIOTECA"])

with t1:
    # GPS BLINDADO (Sin errores de carga)
    loc = get_geolocation()
    if loc and 'coords' in loc:
        lat = loc['coords'].get('latitude', 0)
        lon = loc['coords'].get('longitude', 0)
        gps_actual = f"{lat}, {lon}"
    else:
        gps_actual = "Localizando..."
    
    st.caption(f"📍 GPS: {gps_actual}")

    fuente = st.radio("Entrada:", ["📷 Cámara", "📂 Galería"], horizontal=True)
    fotos = st.camera_input("Scanner") if fuente == "📷 Cámara" else st.file_uploader("Subir fotos", accept_multiple_files=True)
    
    if fotos:
        if st.button("EJECUTAR ANALISIS TOTAL"):
            with st.spinner("IA analizando biomecánica y salud foliar..."):
                f_list = [fotos] if fuente == "📷 Cámara" else fotos
                saved = []
                contents = [{"type": "text", "text": "Analiza como Ingeniero Agronomo: 1. Biomecanica/VTA. 2. Salud Foliar. 3. CODIT. 4. Riesgo: Bajo, Medio o Alto."}]
                for i, f in enumerate(f_list[:15]):
                    p = f"img_{datetime.now().timestamp()}.jpg"
                    with open(p, "wb") as tmp: tmp.write(f.getbuffer())
                    saved.append(p)
                    f.seek(0)
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    contents.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
                
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": contents}])
                txt = res.choices[0].message.content
                
                riesgo = "Bajo"
                if "Alto" in txt: riesgo = "Alto"
                elif "Medio" in txt: riesgo = "Medio"
                
                c.execute("INSERT INTO informes (fecha, analisis, imagenes, gps, riesgo) VALUES (?, ?, ?, ?, ?)", 
                          (datetime.now().strftime("%d/%m/%Y %H:%M"), txt, ",".join(saved), gps_actual, riesgo))
                conn.commit()
                st.markdown(txt)

with t2:
    st.subheader("Gestión de Inventario")
    registros = c.execute("SELECT * FROM informes ORDER BY id DESC").fetchall()
    
    if registros:
        # BOTÓN DE EXPORTACIÓN EXCEL (CSV)
        df_export = pd.DataFrame(registros, columns=['ID', 'Fecha', 'Análisis', 'Imágenes', 'GPS', 'Riesgo'])
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 DESCARGAR INVENTARIO (EXCEL/CSV)",
            data=csv,
            file_name=f'Inventario_Arboricultura_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )
        
        # MAPA INTERACTIVO
        df_mapa = df_export.copy()
        df_mapa[['lat', 'lon']] = df_mapa['GPS'].str.split(', ', expand=True).apply(pd.to_numeric, errors='coerce')
        df_mapa = df_mapa.dropna(subset=['lat', 'lon'])
        
        if not df_mapa.empty:
            m = folium.Map(location=[df_mapa['lat'].iloc[0], df_mapa['lon'].iloc[0]], zoom_start=16)
            colors = {"Bajo": "green", "Medio": "orange", "Alto": "red"}
            for _, r in df_mapa.iterrows():
                folium.Marker([r['lat'], r['lon']], icon=folium.Icon(color=colors.get(r['Riesgo'], 'blue'))).add_to(m)
            st_folium(m, width="100%", height=400)
        
        for r in registros:
            with st.expander(f"📌 {r[1]} | ID {r[0]} | Riesgo: {r[5]}"):
                st.write(r[2])
                if st.button("🗑️ ELIMINAR", key=f"del_{r[0]}"):
                    c.execute(f"DELETE FROM informes WHERE id={r[0]}")
                    conn.commit()
                    st.rerun()

with t3:
    st.header("📖 Academia de Ingenieria")
    st.markdown('<div class="biblio-card"><h3>1. Biomecanica y Viento</h3><p>Estudio de carga dinamica de viento y anclaje radicular.</p></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="biblio-card"><h3>2. Sistema CODIT</h3><p>Barreras de compartimentacion de la pudricion de Shigo.</p></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="biblio-card"><h3>3. Analisis Foliar</h3><p>Identificacion visual de clorosis y deficiencias nutricionales.</p></div>', unsafe_allow_html=True)