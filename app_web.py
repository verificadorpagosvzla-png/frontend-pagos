import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

# ================= CONFIGURACIÓN INICIAL =================
st.set_page_config(page_title="Admin Pagos", page_icon="🔐", layout="wide")

# Credenciales
SUPABASE_URL = "https://rjdgwsmrjfedppvevkny.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZGd3c21yamZlZHBwdmV2a255Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyNTkyNTEsImV4cCI6MjA4NDgzNTI1MX0.RUS_ng1rvj1Jz4aVCMhRptUMDKR2hBCY7CUT6wSGKXY"

# Lista de Servicios
SERVICIOS = [
    "Netflix", "Disney+", "Amazon Prime", "Spotify", "HBO Max", 
    "YouTube Premium", "Paramount+", "Crunchyroll", "VIKI Rakuten", 
    "AppleTV", "Tidal", "Flujo TV", "Tele Latino", "PLEX", "IPTV", 
    "VIX", "Canva", "Adobe", "ChatGPT", "Duolingo", "Capcut", 
    "Gemini", "PornHub", "AppleMusic", "Telegram Premium", "VPN"
]

# Usuarios y Roles
USUARIOS = {
    "gabyluces": {"pass": "24012026", "rol": "admin", "nombre": "Gaby"},
    "saritta":   {"pass": "28032006", "rol": "empleado", "nombre": "Saritta"}
}

# ================= CONEXIÓN Y FUNCIONES =================
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def limpiar_monto_venezuela(monto_str):
    """
    Convierte '2.112,50' -> 2112.50 (Float)
    Lógica: Elimina puntos de miles, cambia coma decimal por punto.
    """
    if not isinstance(monto_str, str):
        return float(monto_str)
    
    # 1. Eliminar puntos (separador de miles en VE)
    limpio = monto_str.replace('.', '')
    # 2. Reemplazar coma por punto (separador decimal en Python)
    limpio = limpio.replace(',', '.')
    
    try:
        return float(limpio)
    except:
        return 0.0

def get_data():
    # Traemos los últimos 70 pagos
    response = supabase.table("pagos").select("*").order("id", desc=True).limit(70).execute()
    return response.data

def update_servicio(id_pago, servicio_nombre):
    supabase.table("pagos").update({"servicio": servicio_nombre}).eq("id", id_pago).execute()

def delete_payment(id_pago):
    supabase.table("pagos").delete().eq("id", id_pago).execute()

# ================= SISTEMA DE LOGIN =================

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['user_name'] = None

def login():
    st.markdown("## 🔐 Iniciar Sesión")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar"):
        if user in USUARIOS and USUARIOS[user]["pass"] == password:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = USUARIOS[user]["rol"]
            st.session_state['user_name'] = USUARIOS[user]["nombre"]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

def logout():
    st.session_state['logged_in'] = False
    st.rerun()

# ================= INTERFAZ PRINCIPAL =================

if not st.session_state['logged_in']:
    login()
else:
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.write(f"Hola, **{st.session_state['user_name']}** ({st.session_state['user_role'].upper()})")
        if st.button("Cerrar Sesión"):
            logout()
        st.divider()
        st.info("💡 Solo los pagos asignados a un servicio suman al total.")

    st.title("💸 Gestión de Suscripciones")

    # --- OBTENCIÓN Y PROCESAMIENTO DE DATOS ---
    data = get_data()
    
    if data:
        df = pd.DataFrame(data)
        
        # Procesar columna monto (Corrección numérica)
        df['monto_real'] = df['monto'].apply(limpiar_monto_venezuela)
        
        # Procesar fechas
        df['fecha_fmt'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m %I:%M %p')

        # --- LÓGICA DE TOTALES (Solo para Admin) ---
        if st.session_state['user_role'] == 'admin':
            # Filtrar solo los que tienen servicio asignado (no nulos)
            pagos_asignados = df[df['servicio'].notnull()]
            total_recaudado = pagos_asignados['monto_real'].sum()
            
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Total Confirmado", f"Bs. {total_recaudado:,.2f}", help="Suma solo de pagos enlazados")
            c2.metric("📋 Transacciones Totales", len(df))
            c3.metric("✅ Enlazados", len(pagos_asignados))
            st.divider()
        
        elif st.session_state['user_role'] == 'empleado':
            st.warning("⚠️ Modo Empleado: Visualización de totales restringida.")
            st.divider()

        # --- TABLA DE GESTIÓN ---
        col_ref, col_monto, col_serv, col_accion = st.columns([2, 1.5, 2, 1])
        
        # Encabezados
        col_ref.markdown("**Referencia / Fecha**")
        col_monto.markdown("**Monto**")
        col_serv.markdown("**Asignar Servicio**")
        col_accion.markdown("**Acción**")

        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 1.5, 2, 1])
                
                # 1. Referencia
                c1.write(f"**{row['referencia']}**")
                c1.caption(row['fecha_fmt'])
                
                # 2. Monto (Verde si está asignado, Gris si no)
                color_monto = "green" if row['servicio'] else "gray"
                c2.markdown(f":{color_monto}[Bs. {row['monto']}]")
                
                # 3. Selector de Servicio
                # Detectar índice actual para mostrar el valor guardado
                idx_actual = 0
                if row['servicio'] in SERVICIOS:
                    idx_actual = SERVICIOS.index(row['servicio'])
                
                # El selectbox permite cambiar el servicio
                nuevo_servicio = c3.selectbox(
                    "Servicio", 
                    options=["Sin asignar"] + SERVICIOS, 
                    index=idx_actual + 1 if row['servicio'] else 0,
                    key=f"sel_{row['id']}",
                    label_visibility="collapsed"
                )

                # 4. Botones de Acción
                # Botón Guardar (Solo aparece si cambias el valor o si no está guardado)
                if nuevo_servicio != "Sin asignar" and nuevo_servicio != row['servicio']:
                    if c4.button("💾", key=f"save_{row['id']}", help="Guardar cambio"):
                        update_servicio(row['id'], nuevo_servicio)
                        st.toast(f"Asignado a {nuevo_servicio}")
                        time.sleep(0.5)
                        st.rerun()
                
                # Botón Borrar (Solo Admin)
                if st.session_state['user_role'] == 'admin':
                    if c4.button("🗑️", key=f"del_{row['id']}"):
                        delete_payment(row['id'])
                        st.rerun()
                
                st.divider()

    else:
        st.info("No hay pagos registrados esperando gestión.")

    # Botón manual de recarga
    if st.button("🔄 Refrescar Lista"):
        st.rerun()
