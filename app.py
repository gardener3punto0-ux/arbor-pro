import streamlit as st
import openai
import os
import base64
import sqlite3
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
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

st.set_page_config(page_title="ARBORICULTURA PRO ELITE", layout="wide", initial_sidebar_state="collapsed")

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
    background-color: #1b5e20; position: sticky; top: 0; z-index: 999; width: 100%;
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

# 4. FUNCIONES CORE
def generar_pdf_elite(texto, img_paths, id_inf, gps):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(27, 94, 32)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 20, "CERTIFICADO TECNICO DE ARBORICULTURA PRO", ln=True, align='C')
    pdf.ln(25)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"ID: {id_inf} | COORDENADAS GPS: {gps}", ln=True)
    if img_paths and os.path.exists(img_paths[0]):
        pdf.image(img_paths[0], x=60, w=90)
        pdf.ln(10)
    pdf.set_font("Arial", '', 11)
    pdf_text = texto.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, pdf_text)
    if not os.path.exists("reports"): os.makedirs("reports")
    path = f"reports/Informe_{id_inf}.pdf"
    pdf.output(path)
    return path

def enviar_email_pro(dest, pdf_path, user_mail, pass_app):
    try:
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = user_mail, dest, "Reporte Arboricultura"
        msg.attach(MIMEText("Adjunto reporte pericial de alta precision.", 'plain'))
        with open(pdf_path, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(pdf_path)}")
            msg.attach(part)
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(user_mail, pass_app)
        s.send_message(msg)
        s.quit()
        return True
    except:
        return False

# 5. INTERFAZ
st.title("🌲 ARBORICULTURA PRO ELITE")
t1, t2, t3 = st.tabs(["📸 NUEVA", "🗄️ HISTORIAL", "📚 BIBLIOTECA"])

with t1:
    with st.sidebar:
        st.header("Configuracion")
        mi_correo = st.text_input("Tu Gmail")
        mi_pass = st.text_input("Pass App Google", type="password")
    
    loc = get_geolocation()
    gps_actual = f"{loc['coords']['latitude']}, {loc['coords']['longitude']}" if loc else "0.0, 0.0"
    st.caption(f"📍 GPS ACTIVADO: {gps_actual}")

    fuente = st.radio("Entrada:", ["📷 Cámara", "📂 Galería"], horizontal=True)
    fotos = st.camera_input("Scanner") if fuente == "📷 Cámara" else st.file_uploader("Subir fotos", accept_multiple_files=True)
    
    if fotos:
        if st.button("EJECUTAR ANALISIS TOTAL"):
            with st.spinner("IA analizando biomecánica y salud foliar..."):
                f_list = [fotos] if fuente == "📷 Cámara" else fotos
                saved = []
                contents = [{"type": "text", "text": "Analiza como Ingeniero Agronomo: 1. Biomecanica/VTA. 2. Salud Foliar. 3. CODIT. 4. Riesgo: Bajo, Medio o Alto."}]
                for i, f in enumerate(f_list[:15]):
                    p = f"reports/img_{datetime.now().timestamp()}.jpg"
                    if not os.path.exists("reports"): os.makedirs("reports")
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
    st.subheader("Mapa de Inventario")
    registros = c.execute("SELECT * FROM informes ORDER BY id DESC").fetchall()
    
    if registros:
        df_mapa = pd.DataFrame(registros, columns=['id', 'fecha', 'analisis', 'imagenes', 'gps', 'riesgo'])
        df_mapa[['lat', 'lon']] = df_mapa['gps'].str.split(', ', expand=True).apply(pd.to_numeric, errors='coerce')
        df_mapa = df_mapa.dropna(subset=['lat', 'lon'])
        if not df_mapa.empty:
            m = folium.Map(location=[df_mapa['lat'].iloc[0], df_mapa['lon'].iloc[0]], zoom_start=16)
            colors = {"Bajo": "green", "Medio": "orange", "Alto": "red"}
            for _, r in df_mapa.iterrows():
                folium.Marker([r['lat'], r['lon']], icon=folium.Icon(color=colors.get(r['riesgo'], 'blue'))).add_to(m)
            st_folium(m, width="100%", height=400)
        
        for r in registros:
            with st.expander(f"📌 {r[1]} | Riesgo: {r[5]}"):
                st.write(r[2])
                pdf_p = generar_pdf_elite(r[2], r[3].split(",") if r[3] else [], r[0], r[4])
                c1, c2, c3 = st.columns(3)
                with c1: st.download_button("📥 PDF", open(pdf_p, "rb"), file_name=f"Informe_{r[0]}.pdf", key=f"pdf_{r[0]}")
                with c2:
                    mail_c = st.text_input("Email Cliente", key=f"e_{r[0]}")
                    if st.button("📧 Enviar", key=f"s_{r[0]}"):
                        if enviar_email_pro(mail_c, pdf_p, mi_correo, mi_pass): st.toast("Enviado")
                with c3:
                    wa = f"https://wa.me/?text=Informe%20Riesgo%20{r[5]}"
                    st.markdown(f'<a href="{wa}" target="_blank">📲 WhatsApp</a>', unsafe_allow_html=True)
                if st.button("🗑️ ELIMINAR", key=f"del_{r[0]}"):
                    c.execute(f"DELETE FROM informes WHERE id={r[0]}")
                    conn.commit()
                    st.rerun()

with t3:
    st.header("📖 Academia de Ingenieria")
    st.markdown('<div class="biblio-card"><h3>1. Biomecanica y Viento</h3><p>Estudio de carga dinamica y factor de vela.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="biblio-card"><h3>2. Sistema CODIT</h3><p>Barreras de compartimentacion de la pudricion.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="biblio-card"><h3>3. Analisis Foliar</h3><p>Identificacion de clorosis ferrica y plagas.</p></div>', unsafe_allow_html=True)

    st.subheader("Tratados Técnicos")
    st.write("El árbol no cicatriza, compartimenta (CODIT). Mantén cortes limpios cerca del cuello de la rama.")
    st.write("La estabilidad se calcula mediante el equilibrio entre el momento de vuelco y el anclaje radicular.")
    

### 💎 Nivel Dios: Perfeccionamiento Final
