import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="Admin Pagos V3", page_icon="📊", layout="wide")

# Credenciales
SUPABASE_URL = "https://rjdgwsmrjfedppvevkny.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZGd3c21yamZlZHBwdmV2a255Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyNTkyNTEsImV4cCI6MjA4NDgzNTI1MX0.RUS_ng1rvj1Jz4aVCMhRptUMDKR2hBCY7CUT6wSGKXY"

# Listas de opciones
SERVICIOS = [
    "Netflix", "Disney+", "Amazon Prime", "Spotify", "HBO Max", 
    "YouTube Premium", "Paramount+", "Crunchyroll", "VIKI Rakuten", 
    "AppleTV", "Tidal", "Flujo TV", "Tele Latino", "PLEX", "IPTV", 
    "VIX", "Canva", "Adobe", "ChatGPT", "Duolingo", "Capcut", 
    "Gemini", "PornHub", "AppleMusic", "Telegram Premium", "VPN"
]

TIPOS_CLIENTE = ["Cliente", "Revendedor"]

# Usuarios
USUARIOS = {
    "gabyluces": {"pass": "24012026", "rol": "admin", "nombre": "Gaby"},
    "saritta":   {"pass": "28032006", "rol": "empleado", "nombre": "Saritta"}
}

# ================= CONEXIÓN Y UTILIDADES =================
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def limpiar_monto_venezuela(monto_input):
    """
    Convierte formatos como '2.112,50' o 'Bs. 2.112,50' a float 2112.50
    Asume formato VE: Punto = Miles, Coma = Decimal.
    """
    if pd.isna(monto_input): return 0.0
    
    # Convertir a string y limpiar letras
    texto = str(monto_input).upper().replace('BS', '').replace('USD', '').strip()
    
    # Caso 1: Si ya viene limpio como "2112.5" (Formato inglés/computadora)
    # y no tiene comas, intentamos convertir directo.
    if '.' in texto and ',' not in texto:
        try:
            return float(texto)
        except: pass

    # Caso 2: Formato Venezuela "2.112,50"
    # Eliminar puntos de miles
    texto_sin_miles = texto.replace('.', '')
    # Reemplazar coma decimal por punto
    texto_final = texto_sin_miles.replace(',', '.')
    
    try:
        return float(texto_final)
    except:
        return 0.0

def get_data():
    response = supabase.table("pagos").select("*").order("id", desc=True).limit(80).execute()
    return response.data

def update_full_pago(id_pago, servicio, tipo):
    """Actualiza servicio y tipo de cliente al mismo tiempo"""
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

# ================= INTERFAZ =================

if not st.session_state['logged_in']:
    login()
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.title(f"Hola, {st.session_state['user_name']}")
        st.caption(f"Rol: {st.session_state['user_role'].upper()}")
        
        if st.button("Cerrar Sesión"):
            logout()
            
        st.divider()
        st.info("ℹ️ Para que un pago se sume al total, debe tener asignado un **Servicio** y un **Tipo de Cliente**.")

    st.title("📊 Gestión de Pagos y Suscripciones")

    # --- DATOS ---
    data = get_data()
    
    if data:
        df = pd.DataFrame(data)
        # Limpieza de datos
        df['monto_real'] = df['monto'].apply(limpiar_monto_venezuela)
        df['fecha_fmt'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m %H:%M')

        # --- SECCIÓN DE ADMIN (TOTALES) ---
        if st.session_state['user_role'] == 'admin':
            
            # Filtros para cálculos
            # Solo sumamos si tienen servicio Y tipo asignado
            mask_validos = (df['servicio'].notnull()) & (df['tipo_cliente'].notnull())
            df_validos = df[mask_validos]
            
            # Totales separados
            total_clientes = df_validos[df_validos['tipo_cliente'] == 'Cliente']['monto_real'].sum()
            total_revendedores = df_validos[df_validos['tipo_cliente'] == 'Revendedor']['monto_real'].sum()
            total_general = total_clientes + total_revendedores
            
            # Tarjetas de Métricas
            st.markdown("### 💰 Balance General")
            m1, m2, m3 = st.columns(3)
            
            m1.metric("Clientes Comunes", f"Bs. {total_clientes:,.2f}")
            m2.metric("Revendedores", f"Bs. {total_revendedores:,.2f}")
            m3.metric("⭐ INGRESO TOTAL", f"Bs. {total_general:,.2f}", delta="Confirmado")
            
            st.divider()

        # --- TABLA DE GESTIÓN ---
        st.subheader("📋 Listado de Transacciones")
        
        # Encabezados visuales
        h1, h2, h3, h4, h5 = st.columns([1.5, 1, 1.5, 1.5, 0.5])
        h1.markdown("**Referencia**")
        h2.markdown("**Monto**")
        h3.markdown("**Servicio**")
        h4.markdown("**Tipo Cliente**")
        h5.markdown("**Go**")

        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1.5, 1.5, 0.5])
                
                # 1. Info
                c1.write(f"**{row['referencia']}**")
                c1.caption(row['fecha_fmt'])
                
                # 2. Monto
                # Color verde si ya está "Listo" (tiene servicio y tipo), gris si falta algo
                listo = row['servicio'] and row['tipo_cliente']
                color = "green" if listo else "red"
                c2.markdown(f":{color}[Bs. {row['monto']}]")
                
                # 3. Selector Servicio
                idx_serv = 0
                if row['servicio'] in SERVICIOS:
                    idx_serv = SERVICIOS.index(row['servicio']) + 1
                
                sel_servicio = c3.selectbox(
                    "Serv", 
                    options=["-"] + SERVICIOS, 
                    index=idx_serv, 
                    key=f"srv_{row['id']}", 
                    label_visibility="collapsed"
                )

                # 4. Selector Tipo Cliente
                idx_tipo = 0
                if row['tipo_cliente'] in TIPOS_CLIENTE:
                    idx_tipo = TIPOS_CLIENTE.index(row['tipo_cliente']) + 1
                
                sel_tipo = c4.selectbox(
                    "Tipo", 
                    options=["-"] + TIPOS_CLIENTE, 
                    index=idx_tipo, 
                    key=f"tip_{row['id']}", 
                    label_visibility="collapsed"
                )

                # 5. Botón Guardar (Solo aparece si hay cambios pendientes por guardar)
                # O si falta asignar algo para completarlo
                
                # Detectar cambios
                cambio_serv = sel_servicio != "-" and sel_servicio != row['servicio']
                cambio_tipo = sel_tipo != "-" and sel_tipo != row['tipo_cliente']
                
                if cambio_serv or cambio_tipo:
                    if c5.button("💾", key=f"save_{row['id']}"):
                        val_serv = sel_servicio if sel_servicio != "-" else None
                        val_tipo = sel_tipo if sel_tipo != "-" else None
                        
                        update_full_pago(row['id'], val_serv, val_tipo)
                        st.toast("¡Actualizado!")
                        time.sleep(0.5)
                        st.rerun()
                
                # Botón Borrar (Solo Admin)
                elif st.session_state['user_role'] == 'admin':
                     if c5.button("🗑️", key=f"del_{row['id']}"):
                        delete_payment(row['id'])
                        st.rerun()
                
                st.divider()

    else:
        st.info("No hay pagos registrados.")
        
    if st.button("🔄 Refrescar"):
        st.rerun()
