import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

st.set_page_config(page_title="Mi Billetera", page_icon="🌎", layout="centered")

# TUS CREDENCIALES EXACTAS
SUPABASE_URL = "https://rjdgwsmrjfedppvevkny.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZGd3c21yamZlZHBwdmV2a255Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyNTkyNTEsImV4cCI6MjA4NDgzNTI1MX0.RUS_ng1rvj1Jz4aVCMhRptUMDKR2hBCY7CUT6wSGKXY"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def get_data():
    response = supabase.table("pagos").select("*").order("id", desc=True).limit(50).execute()
    return response.data

def delete_payment(pid):
    supabase.table("pagos").delete().eq("id", pid).execute()

st.title("🌎 Monitor de Pagos")

# Métricas
data = get_data()
if data:
    df = pd.DataFrame(data)
    try:
        df['monto_num'] = pd.to_numeric(df['monto'].astype(str).str.replace(r'[^\d\.]', '', regex=True), errors='coerce')
        st.metric("Total Recibido", f"Bs. {df['monto_num'].sum():,.2f}")
    except: pass

    st.divider()
    
    if st.button("🔄 Actualizar"):
        st.rerun()

    for i, row in df.iterrows():
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"Ref: **{row['referencia']}**")
        c2.write(f"Bs. {row['monto']}")
        if c3.button("🗑️", key=row['id']):
            delete_payment(row['id'])
            time.sleep(0.5)
            st.rerun()
        st.divider()
else:
    st.info("Sin pagos registrados.")