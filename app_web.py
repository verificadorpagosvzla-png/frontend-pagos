import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import requests

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="Admin Pagos V4", page_icon="🇻🇪", layout="wide")

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

# --- NUEVA FUNCIÓN: API BINANCE ---
@st.cache_data(ttl=60) # Guarda el precio en memoria por 60 segundos para no saturar
def get_tasa_binance():
    """
    Consulta la API P2P de Binance para obtener la tasa de COMPRA (Buy) de USDT con VES.
    Filtra por 'PagoMovil' para obtener una tasa realista del mercado venezolano.
    """
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0" # Simulamos ser un navegador
    }
    # Payload para buscar anuncios de VENTA (TradeType BUY para nosotros)
    data = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": ["PagoMovil"], # Filtro clave para Venezuela
        "publisherType": None,
        "rows": 1, # Solo necesitamos el primero (el mejor precio)
        "tradeType": "BUY" 
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result["data"]:
                precio = float(result["data"][0]["adv"]["price"])
                return precio
    except Exception as e:
        print(f"Error Binance: {e}")
    
    return None # Retorna None si falla

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

# ================= LOGIN =================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

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
                st.rerun()
            else:
                st.error("Datos incorrectos")

def logout():
    st.session_state['logged_in'] = False
    st.rerun()

# ================= INTERFAZ PRINCIPAL =================
if not st.session_state['logged_in']:
    login()
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.title(f"Hola, {st.session_state['user_name']}")
        
        # Mostrar Tasa Binance en el menú lateral
        tasa_actual = get_tasa_binance()
        if tasa_actual:
            st.metric("Tasa Binance (P2P)", f"Bs. {tasa_actual:,.2f}")
        else:
            st.warning("Binance Offline")

        if st.button("Cerrar Sesión"):
            logout()
        st.divider()

    st.title("📊 Gestión de Pagos")

    data = get_data()
    
    if data:
        df = pd.DataFrame(data)
        df['monto_real'] = df['monto'].apply(limpiar_monto_venezuela)
        
        # --- CORRECCIÓN DE FECHA Y HORA (Venezuela) ---
        # 1. Convertir a datetime (Supabase da UTC)
        df['fecha_dt'] = pd.to_datetime(df['fecha'])
        
        # 2. Si la fecha no tiene zona horaria (naive), le asignamos UTC
        if df['fecha_dt'].dt.tz is None:
            df['fecha_dt'] = df['fecha_dt'].dt.tz_localize('UTC')
            
        # 3. Convertir a Hora Venezuela (America/Caracas)
        df['fecha_ve'] = df['fecha_dt'].dt.tz_convert('America/Caracas')
        
        # 4. Formatear para mostrar
        df['fecha_fmt'] = df['fecha_ve'].dt.strftime('%d/%m %I:%M %p')

        # --- SECCIÓN DE ADMIN (TOTALES CON USDT) ---
        if st.session_state['user_role'] == 'admin':
            
            mask_validos = (df['servicio'].notnull()) & (df['tipo_cliente'].notnull())
            df_validos = df[mask_validos]
            
            total_clientes = df_validos[df_validos['tipo_cliente'] == 'Cliente']['monto_real'].sum()
            total_revendedores = df_validos[df_validos['tipo_cliente'] == 'Revendedor']['monto_real'].sum()
            total_general = total_clientes + total_revendedores
            
            # Cálculo USDT
            usdt_clientes = total_clientes / tasa_actual if tasa_actual else 0
            usdt_revendedores = total_revendedores / tasa_actual if tasa_actual else 0
            usdt_general = total_general / tasa_actual if tasa_actual else 0

            st.markdown("### 💰 Balance General (Bs. / USDT)")
            
            # Usamos columnas para mostrar Bs arriba y USDT abajo
            m1, m2, m3 = st.columns(3)
            
            m1.metric("Clientes", f"Bs. {total_clientes:,.2f}", f"${usdt_clientes:,.2f} USDT")
            m2.metric("Revendedores", f"Bs. {total_revendedores:,.2f}", f"${usdt_revendedores:,.2f} USDT")
            m3.metric("⭐ TOTAL", f"Bs. {total_general:,.2f}", f"${usdt_general:,.2f} USDT")
            
            st.caption(f"*Cálculo basado en tasa P2P Compra: {tasa_actual:,.2f} Bs/USDT*")
            st.divider()

        # --- TABLA DE GESTIÓN ---
        st.subheader("📋 Transacciones Recientes")
        
        h1, h2, h3, h4, h5 = st.columns([1.5, 1, 1.5, 1.5, 0.5])
        h1.markdown("**Ref / Hora**")
        h2.markdown("**Monto**")
        h3.markdown("**Servicio**")
        h4.markdown("**Tipo**")
        h5.markdown("**Ok**")

        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1.5, 1.5, 0.5])
                
                c1.write(f"**{row['referencia']}**")
                c1.caption(row['fecha_fmt']) # Ahora muestra hora correcta de Vzla
                
                listo = row['servicio'] and row['tipo_cliente']
                color = "green" if listo else "red"
                c2.markdown(f":{color}[Bs. {row['monto']}]")
                
                idx_serv = SERVICIOS.index(row['servicio']) + 1 if row['servicio'] in SERVICIOS else 0
                sel_servicio = c3.selectbox("S", ["-"] + SERVICIOS, index=idx_serv, key=f"s_{row['id']}", label_visibility="collapsed")

                idx_tipo = TIPOS_CLIENTE.index(row['tipo_cliente']) + 1 if row['tipo_cliente'] in TIPOS_CLIENTE else 0
                sel_tipo = c4.selectbox("T", ["-"] + TIPOS_CLIENTE, index=idx_tipo, key=f"t_{row['id']}", label_visibility="collapsed")

                cambio = (sel_servicio != "-" and sel_servicio != row['servicio']) or \
                         (sel_tipo != "-" and sel_tipo != row['tipo_cliente'])
                
                if cambio:
                    if c5.button("💾", key=f"sv_{row['id']}"):
                        v_serv = sel_servicio if sel_servicio != "-" else None
                        v_tipo = sel_tipo if sel_tipo != "-" else None
                        update_full_pago(row['id'], v_serv, v_tipo)
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
        
    if st.button("🔄 Refrescar"):
        st.rerun()
