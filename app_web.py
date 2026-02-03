import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import requests
import base64
import os
from datetime import datetime

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="Admin Pagos", page_icon="📱", layout="wide")

# Cálculo de ruta absoluta para encontrar el logo siempre
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

# ESTILOS CSS
st.markdown("""
    <style>
    [data-testid="stSidebar"] img {
        margin-top: 20px;
        margin-bottom: 20px;
        max-width: 80%;
        margin-left: 10%;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Centrar logo en login */
    .login-logo {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Credenciales
SUPABASE_URL = "https://rjdgwsmrjfedppvevkny.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZGd3c21yamZlZHBwdmV2a255Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyNTkyNTEsImV4cCI6MjA4NDgzNTI1MX0.RUS_ng1rvj1Jz4aVCMhRptUMDKR2hBCY7CUT6wSGKXY"

SERVICIOS = [
    "Netflix", "Disney+", "Amazon Prime", "Spotify", "HBO Max", 
    "YouTube Premium", "Paramount+", "Crunchyroll", "VIKI Rakuten", 
    "AppleTV", "Tidal", "Flujo TV", "Tele Latino", "PLEX", "IPTV", 
    "VIX", "Canva", "Adobe", "ChatGPT", "Duolingo", "Capcut", 
    "Gemini", "PornHub", "AppleMusic", "Telegram Premium", "VPN"
]

TIPOS_CLIENTE = ["Cliente", "Revendedor"]

USUARIOS = {
    "gabyluces": {"pass": "24012026", "rol": "admin", "nombre": "Gaby"},
    "saritta":   {"pass": "28032006", "rol": "empleado", "nombre": "Saritta"}
}

# ================= CONEXIONES =================
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

@st.cache_data(ttl=60)
def get_tasa_binance(modo="LOW"):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    trade_type = "BUY"
    page = 1
    
    if modo == "HIGH":
        trade_type = "BUY"
        page = 3 
    elif modo == "SELL":
        trade_type = "SELL"
        page = 1
        
    data = {
        "asset": "USDT", "fiat": "VES", "merchantCheck": False,
        "page": page, "payTypes": ["PagoMovil"], 
        "rows": 10, "tradeType": trade_type 
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result["data"]:
                idx = -1 if modo == "HIGH" else 0
                return float(result["data"][idx]["adv"]["price"])
            elif modo == "HIGH":
                return get_tasa_binance_fallback_high()
    except: pass
    return None

def get_tasa_binance_fallback_high():
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        data = {"asset": "USDT", "fiat": "VES", "page": 1, "rows": 20, "tradeType": "BUY", "payTypes": ["PagoMovil"]}
        res = requests.post(url, json=data, headers={"Content-Type": "application/json"}).json()
        if res["data"]: return float(res["data"][-1]["adv"]["price"])
    except: pass
    return None

def limpiar_monto_venezuela(monto_input):
    if pd.isna(monto_input): return 0.0
    texto = str(monto_input).upper().replace('BS', '').replace('USD', '').strip()
    if '.' in texto and ',' not in texto:
        try: return float(texto)
        except: pass
    texto_sin_miles = texto.replace('.', '')
    texto_final = texto_sin_miles.replace(',', '.')
    try: return float(texto_final)
    except: return 0.0

def get_data():
    response = supabase.table("pagos").select("*").order("id", desc=True).limit(80).execute()
    return response.data

def update_full_pago(id_pago, servicio, tipo):
    supabase.table("pagos").update({"servicio": servicio, "tipo_cliente": tipo}).eq("id", id_pago).execute()

def delete_payment(id_pago):
    supabase.table("pagos").delete().eq("id", id_pago).execute()

# ================= LÓGICA DE SESIÓN =================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Auto-login por URL
params = st.query_params
if not st.session_state['logged_in'] and "auth" in params:
    try:
        token_decoded = base64.b64decode(params["auth"]).decode().split(":")
        user_url, pass_url = token_decoded[0], token_decoded[1]
        if user_url in USUARIOS and USUARIOS[user_url]["pass"] == pass_url:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = USUARIOS[user_url]["rol"]
            st.session_state['user_name'] = USUARIOS[user_url]["nombre"]
    except: pass

def login():
    st.write("") 
    st.write("") 
    
    # Columnas para centrar el formulario
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Mostrar logo usando ruta absoluta y try/except por seguridad
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso Seguro</h2>", unsafe_allow_html=True)
        
        # Keys únicos para evitar conflictos
        user = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        
        if st.button("Iniciar Sesión", type="primary"):
            if user in USUARIOS and USUARIOS[user]["pass"] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = USUARIOS[user]["rol"]
                st.session_state['user_name'] = USUARIOS[user]["nombre"]
                
                # Token persistente
                token_str = f"{user}:{password}"
                token_b64 = base64.b64encode(token_str.encode()).decode()
                st.query_params["auth"] = token_b64
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

def logout():
    st.session_state['logged_in'] = False
    st.query_params.clear()
    st.rerun()

# ================= CONTROL DE FLUJO =================
# Usamos un placeholder vacío para el login.
# Si estamos logueados, lo limpiamos para asegurar que no se vea nada.
login_placeholder = st.empty()

if not st.session_state['logged_in']:
    with login_placeholder.container():
        login()
else:
    login_placeholder.empty() # Borra forzosamente el login si quedó 'pegado'
    
    # --- APLICACIÓN PRINCIPAL ---
    # Variables default
    tasa_calculo = 60.00
    modo_vivo = True 

    # --- SIDEBAR ---
    with st.sidebar:
        # LOGO SIDEBAR
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        
        st.title(f"Hola, {st.session_state['user_name']}")
        
        if st.session_state['user_role'] == 'admin':
            st.divider()
            st.subheader("⚙️ Configuración")
            opcion_tasa = st.radio("Tasa:", ["Binance (ALTA)", "Binance (BAJA)", "Manual"], index=0)
            
            if opcion_tasa == "Manual":
                tasa_calculo = st.number_input("Bs/USDT", min_value=1.0, value=65.0, format="%.2f")
            else:
                modo_api = "HIGH" if "ALTA" in opcion_tasa else "LOW"
                tasa_api = get_tasa_binance(modo_api)
                if tasa_api:
                    tasa_calculo = tasa_api
                    st.success(f"API: {tasa_calculo:,.2f}")
                else: tasa_calculo = 65.0
            
            st.divider()
            modo_vivo = st.checkbox("🔴 En Vivo", value=True)
        else:
            tasa_emp = get_tasa_binance("HIGH")
            if tasa_emp: tasa_calculo = tasa_emp

        st.divider()
        if st.button("Salir"): logout()

    # --- CONTENIDO ---
    st.title("📊 Control de Pagos")

    data = get_data()
    
    if data:
        df = pd.DataFrame(data)
        df['monto_real'] = df['monto'].apply(limpiar_monto_venezuela)
        
        df['fecha_dt'] = pd.to_datetime(df['fecha'])
        if df['fecha_dt'].dt.tz is None: df['fecha_dt'] = df['fecha_dt'].dt.tz_localize('UTC')
        df['fecha_ve'] = df['fecha_dt'].dt.tz_convert('America/Caracas')
        df['fecha_fmt'] = df['fecha_ve'].dt.strftime('%d/%m %I:%M %p')

        # --- ADMIN TOTALES ---
        if st.session_state['user_role'] == 'admin':
            mask = (df['servicio'].notnull()) & (df['tipo_cliente'].notnull())
            df_val = df[mask]
            
            t_cli = df_val[df_val['tipo_cliente'] == 'Cliente']['monto_real'].sum()
            t_rev = df_val[df_val['tipo_cliente'] == 'Revendedor']['monto_real'].sum()
            t_gen = t_cli + t_rev
            
            u_cli = t_cli / tasa_calculo if tasa_calculo else 0
            u_rev = t_rev / tasa_calculo if tasa_calculo else 0
            u_gen = t_gen / tasa_calculo if tasa_calculo else 0

            st.markdown(f"### 💰 Balance (Tasa: {tasa_calculo:,.2f})")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                with st.container(border=True):
                    st.metric("Clientes", f"Bs. {t_cli:,.0f}", f"${u_cli:,.1f}")
            with c2:
                with st.container(border=True):
                    st.metric("Revendedores", f"Bs. {t_rev:,.0f}", f"${u_rev:,.1f}")
            with c3:
                with st.container(border=True):
                    st.metric("TOTAL", f"Bs. {t_gen:,.0f}", f"${u_gen:,.1f}")
            st.divider()

        # --- LISTA MÓVIL OPTIMIZADA ---
        st.subheader("📋 Transacciones")
        
        for i, row in df.iterrows():
            with st.container(border=True):
                top1, top2 = st.columns([2, 1])
                
                with top1:
                    st.markdown(f"**Ref: {row['referencia']}**")
                    st.caption(f"📅 {row['fecha_fmt']}")
                
                with top2:
                    ok = row['servicio'] and row['tipo_cliente']
                    color = "green" if ok else "red"
                    st.markdown(f"<div style='text-align: right; color: {color}; font-weight: bold;'>Bs. {row['monto']}</div>", unsafe_allow_html=True)
                
                expanded_state = not ok 
                with st.expander("📝 Clasificar / Editar", expanded=expanded_state):
                    
                    c_serv, c_tipo, c_save = st.columns([2, 2, 1])
                    
                    ix_s = SERVICIOS.index(row['servicio']) + 1 if row['servicio'] in SERVICIOS else 0
                    s_sel = c_serv.selectbox("Servicio", ["-"] + SERVICIOS, index=ix_s, key=f"s_{row['id']}")

                    ix_t = TIPOS_CLIENTE.index(row['tipo_cliente']) + 1 if row['tipo_cliente'] in TIPOS_CLIENTE else 0
                    t_sel = c_tipo.selectbox("Cliente", ["-"] + TIPOS_CLIENTE, index=ix_t, key=f"t_{row['id']}")

                    if (s_sel != "-" and s_sel != row['servicio']) or (t_sel != "-" and t_sel != row['tipo_cliente']):
                        if c_save.button("💾", key=f"sv_{row['id']}"):
                            v_s = s_sel if s_sel != "-" else None
                            v_t = t_sel if t_sel != "-" else None
                            update_full_pago(row['id'], v_s, v_t)
                            st.toast("Guardado")
                            time.sleep(0.5)
                            st.rerun()
                    elif st.session_state['user_role'] == 'admin':
                         if c_save.button("🗑️", key=f"dl_{row['id']}"):
                            delete_payment(row['id'])
                            st.rerun()

    else:
        st.info("Sin registros.")
        
    if modo_vivo:
        time.sleep(5)
        st.rerun()
