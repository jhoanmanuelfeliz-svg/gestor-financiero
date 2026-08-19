import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime
from supabase import create_client, Client

# Configuración de página
st.set_config = st.set_page_config(page_title="Gestor Financiero Pro", page_icon="🏦", layout="wide")

# --- CONEXIÓN SUPABASE ---
SUPABASE_URL = "https://frnvacgjgiofqmhchypf.supabase.co"
SUPABASE_KEY = "sb_publishable_DZ4PGeLx2rLuiXF5yAveaQ_kuW6SugO"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GESTIÓN DE USUARIOS ---
def cargar_usuarios():
    if os.path.exists('usuarios.json'):
        with open('usuarios.json', 'r') as f: return json.load(f)
    return {"admin": {"password": "admin", "rol": "Administrador"}}

if "autenticado" not in st.session_state:
    st.session_state.update({"autenticado": False, "rol": None, "usuario": None})

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("🏦 Sistema Financiero")
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                db = cargar_usuarios()
                if user in db and db[user]["password"] == password:
                    st.session_state.update({"autenticado": True, "rol": db[user]["rol"], "usuario": user})
                    st.rerun()
                else: st.error("Usuario o contraseña incorrectos.")
    st.stop()

# --- FUNCIONES DE INTERFAZ (DIÁLOGOS) ---

@st.dialog("➕ Registrar Movimiento")
def dialog_agregar():
    with st.form("form_registro"):
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        cat_lista = ["Alimentación", "Combustible", "Supermercado", "Tiendas", "Deudas", "Impuesto", "Transporte", "Vivienda", "Servicios", "Entretenimiento", "Otros"] if tipo == "Gasto" else ["Salario", "Ventas", "Negocio", "Inversiones", "Regalos", "Otros"]
        cat = st.selectbox("Categoría", cat_lista)
        fecha = st.date_input("Fecha")
        metodo = st.selectbox("Método de Pago", ["Cuenta propia", "Efectivo", "Transferencia a tercero"]) if tipo == "Gasto" else "N/A"
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto (RD$)", min_value=0.01)
        
        if st.form_submit_button("Guardar Movimiento"):
            data = {'Fecha': str(fecha), 'Tipo': tipo, 'Categoría': cat, 'Descripción': desc, 'Monto': float(monto), 'Recibo_Adjunto': 'Sin recibo'}
            supabase.table("movimientos").insert(data).execute()
            if tipo == "Gasto" and metodo == "Transferencia a tercero":
                supabase.table("movimientos").insert({
                    'Fecha': str(fecha),
                    'Tipo': 'Gasto',
                    'Categoría': 'Impuesto',
                    'Descripción': 'Impuesto bancario (0.20% por transferencia a tercero)',
                    'Monto': float(monto) * 0.0020,
                    'Recibo_Adjunto': 'Sin recibo'
                }).execute()
            st.success("Guardado exitosamente")
            st.rerun()

@st.dialog("⚠️ Confirmar Eliminación")
def confirmar_eliminar(row):
    st.warning(f"¿Eliminar: {row['Descripción']} por RD${float(row['Monto']):,.2f}?")
    if st.button("Sí, borrar"):
        supabase.table("movimientos").delete().eq("id", int(row['id'])).execute()
        st.success("Registro eliminado")
        st.rerun()

# --- LÓGICA PRINCIPAL ---
# Cargar datos desde Supabase
response = supabase.table("movimientos").select("*").execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
if not df.empty: df['Monto'] = df['Monto'].astype(float)

# Encabezado
st.title("📊 Dashboard Financiero")
col_header1, col_header2 = st.columns([4, 1])
with col_header2:
    if st.button("➕ Agregar Movimiento"): dialog_agregar()

tabs = st.tabs(["📋 Estado de Situación", "📈 Tendencias", "📜 Movimientos"])

with tabs[0]: # ESTADO DE SITUACIÓN
    st.subheader("Estado de Situación Actual")
    col1, col2, col3 = st.columns(3)
    ing = df[df['Tipo'] == 'Ingreso']['Monto'].sum() if not df.empty else 0
    gas = df[df['Tipo'] == 'Gasto']['Monto'].sum() if not df.empty else 0
    col1.metric("Total Ingresos", f"RD${ing:,.2f}")
    col2.metric("Total Gastos", f"RD${gas:,.2f}")
    col3.metric("Balance Neto", f"RD${ing-gas:,.2f}")

with tabs[1]: # TENDENCIAS
    st.subheader("Tendencia Temporal")
    if not df.empty:
        df_tendencia = df.groupby(['Fecha', 'Tipo'])['Monto'].sum().reset_index()
        fig = px.line(df_tendencia, x='Fecha', y='Monto', color='Tipo', markers=True)
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]: # MOVIMIENTOS
    if not df.empty:
        # Mostramos la tabla con posibilidad de borrar
        for _, row in df.iterrows():
            cols = st.columns([2, 1, 1.5, 2.5, 1, 0.5])
            cols[0].write(row['Fecha'])
            cols[1].write(row['Tipo'])
            cols[2].write(row['Categoría'])
            cols[3].write(row['Descripción'])
            cols[4].write(f"RD${float(row['Monto']):,.2f}")
            if cols[5].button("🗑️", key=f"del_{row['id']}"):
                confirmar_eliminar(row)
    else:
        st.info("No hay movimientos registrados.")