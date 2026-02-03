import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import requests
from datetime import datetime
import base64

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="Admin Pagos", page_icon="🔐", layout="wide")

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

# ================= CONEXIONES Y UTILIDADES =================
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

@st.cache_data(ttl=60)
def get_tasa_binance(estrategia="LOW"):
    """
    Consulta API P2P de Binance.
    estrategia="LOW" -> Trae el precio más bajo de venta (Lo estándar para comprar barato).
    estrategia="HIGH" -> Intenta traer un precio más alto (usando ofertas de compra).
    """
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    # Si queremos PRECIO ALTO, buscamos a los que QUIEREN COMPRAR (TradeType SELL),
    # ya que sus ofertas suelen ser las más altas del listado visible 'Venta'.
    # Si queremos PRECIO BAJO, buscamos a los que QUIEREN VENDER (TradeType BUY).
    tipo_trade = "SELL" if estrategia == "HIGH" else "BUY"
    
    data = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": ["PagoMovil"], 
        "publisherType": None,
        "rows": 1, 
        "tradeType": tipo_trade 
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result["data"]:
                precio = float(result["data"][0]["adv"]["price"])
                return precio
    except Exception as e:
        pass
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
    supabase.table("pagos").update({
        "servicio": servicio,
        "tipo_cliente": tipo
    }).eq("id", id_pago).execute()

def delete_payment(id_pago):
    supabase.table("pagos").delete().eq("id", id_pago).execute()

# ================= LOGIN CON PERSISTENCIA =================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

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
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("## 🔐 Control de Acceso")
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            if user in USUARIOS and USUARIOS[user]["pass"] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = USUARIOS[user]["rol"]
                st.session_state['user_name'] = USUARIOS[user]["nombre"]
                token_str = f"{user}:{password}"
                token_b64 = base64.b64encode(token_str.encode()).decode()
                st.query_params["auth"] = token_b64
                st.rerun()
            else:
                st.error("Datos incorrectos")

def logout():
    st.session_state['logged_in'] = False
    st.query_params.clear()
    st.rerun()

# ================= INTERFAZ PRINCIPAL =================
if not st.session_state['logged_in']:
    login()
else:
    # Variables globales de configuración (con valores por defecto por seguridad)
    tasa_calculo = 60.00
    modo_vivo = True # Por defecto activado para empleados también

    # --- SIDEBAR (SOLO ADMIN GABY VE LA CONFIGURACIÓN) ---
    with st.sidebar:
        st.title(f"Hola, {st.session_state['user_name']}")
        
        # Bloque de Configuración (Solo Admin)
        if st.session_state['user_role'] == 'admin':
            st.divider()
            st.subheader("⚙️ Configuración Admin")
            
            # Selector de Tasa
            modo_tasa = st.radio(
                "Tasa de Referencia:",
                ["Binance (Mercado Alto/Venta)", "Binance (Mercado Bajo/Compra)", "Manual"],
                index=0,
                help="Alto: Mejor para vendedores. Bajo: Mejor para compradores."
            )

            if modo_tasa == "Manual":
                tasa_calculo = st.number_input("Tasa Manual (Bs/USDT)", min_value=1.0, value=60.0, step=0.1, format="%.2f")
            else:
                # Estrategia HIGH busca en SELL (Ofertas de Compra más altas)
                # Estrategia LOW busca en BUY (Ofertas de Venta más bajas)
                estrategia = "HIGH" if "Alto" in modo_tasa else "LOW"
                tasa_api = get_tasa_binance(estrategia)
                
                if tasa_api:
                    tasa_calculo = tasa_api
                    st.success(f"Tasa API: {tasa_calculo:,.2f}")
                else:
                    st.error("API Error.")
                    tasa_calculo = 60.0
            
            st.divider()
            # Selector En Vivo
            modo_vivo = st.checkbox("🔴 En Vivo (Auto-refresh)", value=True)
        
        else:
            # Para el empleado Saritta, calculamos la tasa por defecto (Alta) sin mostrar controles
            # Ocultamente usamos la tasa alta de Binance para que los cálculos sean consistentes
            tasa_api_default = get_tasa_binance("HIGH")
            if tasa_api_default: tasa_calculo = tasa_api_default
            st.info(f"Tasa del día: {tasa_calculo:,.2f}")

        st.divider()
        if st.button("Cerrar Sesión"):
            logout()

    # --- CONTENIDO PRINCIPAL ---
    st.title("📊 Gestión de Pagos")

    data = get_data()
    
    if data:
        df = pd.DataFrame(data)
        df['monto_real'] = df['monto'].apply(limpiar_monto_venezuela)
        
        # Fechas
        df['fecha_dt'] = pd.to_datetime(df['fecha'])
        if df['fecha_dt'].dt.tz is None: df['fecha_dt'] = df['fecha_dt'].dt.tz_localize('UTC')
        df['fecha_ve'] = df['fecha_dt'].dt.tz_convert('America/Caracas')
        df['fecha_fmt'] = df['fecha_ve'].dt.strftime('%d/%m %I:%M %p')

        # --- PANEL DE ADMIN (TOTALES) ---
        if st.session_state['user_role'] == 'admin':
            mask_validos = (df['servicio'].notnull()) & (df['tipo_cliente'].notnull())
            df_validos = df[mask_validos]
            
            t_cli = df_validos[df_validos['tipo_cliente'] == 'Cliente']['monto_real'].sum()
            t_rev = df_validos[df_validos['tipo_cliente'] == 'Revendedor']['monto_real'].sum()
            t_gen = t_cli + t_rev
            
            u_cli = t_cli / tasa_calculo if tasa_calculo else 0
            u_rev = t_rev / tasa_calculo if tasa_calculo else 0
            u_gen = t_gen / tasa_calculo if tasa_calculo else 0

            st.markdown(f"### 💰 Balance General (Tasa: {tasa_calculo:,.2f})")
            m1, m2, m3 = st.columns(3)
            m1.metric("Clientes", f"Bs. {t_cli:,.2f}", f"${u_cli:,.2f}")
            m2.metric("Revendedores", f"Bs. {t_rev:,.2f}", f"${u_rev:,.2f}")
            m3.metric("⭐ TOTAL", f"Bs. {t_gen:,.2f}", f"${u_gen:,.2f}")
            st.divider()

        # --- TABLA ---
        st.subheader("📋 Transacciones")
        cols = st.columns([1.5, 1, 1.5, 1.5, 0.5])
        headers = ["Ref / Hora", "Monto", "Servicio", "Tipo", "Ok"]
        for c, h in zip(cols, headers): c.markdown(f"**{h}**")

        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1.5, 1.5, 0.5])
                
                c1.write(f"**{row['referencia']}**")
                c1.caption(row['fecha_fmt'])
                
                listo = row['servicio'] and row['tipo_cliente']
                color = "green" if listo else "red"
                c2.markdown(f":{color}[Bs. {row['monto']}]")
                
                # Selectores
                ix_s = SERVICIOS.index(row['servicio']) + 1 if row['servicio'] in SERVICIOS else 0
                s_sel = c3.selectbox("S", ["-"] + SERVICIOS, index=ix_s, key=f"s_{row['id']}", label_visibility="collapsed")

                ix_t = TIPOS_CLIENTE.index(row['tipo_cliente']) + 1 if row['tipo_cliente'] in TIPOS_CLIENTE else 0
                t_sel = c4.selectbox("T", ["-"] + TIPOS_CLIENTE, index=ix_t, key=f"t_{row['id']}", label_visibility="collapsed")

                # Botones Acción
                if (s_sel != "-" and s_sel != row['servicio']) or (t_sel != "-" and t_sel != row['tipo_cliente']):
                    if c5.button("💾", key=f"sv_{row['id']}"):
                        v_s = s_sel if s_sel != "-" else None
                        v_t = t_sel if t_sel != "-" else None
                        update_full_pago(row['id'], v_s, v_t)
                        st.toast("Guardado")
                        time.sleep(0.5)
                        st.rerun()
                elif st.session_state['user_role'] == 'admin':
                     if c5.button("🗑️", key=f"dl_{row['id']}"):
                        delete_payment(row['id'])
                        st.rerun()
                st.divider()
    else:
        st.info("Sin registros.")
        
    # Auto-refresh (Activo por defecto para todos, solo Admin puede desactivarlo)
    if modo_vivo:
        time.sleep(5)
        st.rerun()
