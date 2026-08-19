import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime, timedelta
from supabase import create_client, Client

# Configuración de la página
st.set_config = st.set_page_config(page_title="Gestor Financiero Pro", page_icon="🏦", layout="wide")

# --- CONEXIÓN SUPABASE ---
SUPABASE_URL = "https://frnvacgjgiofqmhchypf.supabase.co"
SUPABASE_KEY = "sb_publishable_DZ4PGeLx2rLuiXF5yAveaQ_kuW6SugO"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GESTIÓN DE USUARIOS ---
ARCHIVO_USUARIOS = 'usuarios.json'

def cargar_usuarios():
    if os.path.exists(ARCHIVO_USUARIOS):
        try:
            with open(ARCHIVO_USUARIOS, 'r') as f:
                return json.load(f)
        except:
            pass
    usuarios_por_defecto = {
        "admin": {"password": "admin", "rol": "Administrador"},
        "invitado": {"password": "1234", "rol": "Lector"}
    }
    with open(ARCHIVO_USUARIOS, 'w') as f:
        json.dump(usuarios_por_defecto, f)
    return usuarios_por_defecto

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario = None

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("🏦 Sistema Financiero")
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar")
            
            if submit:
                db_actual = cargar_usuarios()
                if user in db_actual and db_actual[user]["password"] == password:
                    st.session_state.autenticado = True
                    st.session_state.rol = db_actual[user]["rol"]
                    st.session_state.usuario = user
                    st.success("¡Ingreso exitoso!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

# ==========================================
# CÓDIGO PRINCIPAL (AUTENTICADO)
# ==========================================

# Estado de Tarjeta de Crédito (Banco Lafise - Visa Gold)
if 'tc_dop' not in st.session_state:
    archivo_tc = 'tarjeta_lafise.json'
    if os.path.exists(archivo_tc):
        with open(archivo_tc, 'r') as f:
            data_tc = json.load(f)
            st.session_state.tc_dop = data_tc.get('dop', 81060.38)
            st.session_state.tc_usd = data_tc.get('usd', -2.41)
            st.session_state.tc_movs = pd.DataFrame(data_tc.get('movs', []))
    else:
        st.session_state.tc_dop = 81060.38
        st.session_state.tc_usd = -2.41
        st.session_state.tc_movs = pd.DataFrame(columns=['Fecha', 'Moneda', 'Tipo', 'Monto', 'Descripcion'])

def guardar_estado_tc():
    data_tc = {
        'dop': st.session_state.tc_dop,
        'usd': st.session_state.tc_usd,
        'movs': st.session_state.tc_movs.to_dict('records')
    }
    with open('tarjeta_lafise.json', 'w') as f:
        json.dump(data_tc, f)

if 'presupuesto' not in st.session_state: 
    st.session_state.presupuesto = 39348.77

# --- VENTANAS MODALES (DIÁLOGOS) ---

@st.dialog("➕ Registrar Movimiento")
def dialog_agregar():
    with st.form("form_registro"):
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        cat_lista = ["Alimentación", "Combustible", "Supermercado", "Tiendas", "Deudas", "Impuesto", "Transporte", "Vivienda", "Servicios", "Entretenimiento", "Otros"] if tipo == "Gasto" else ["Salario", "Ventas", "Negocio", "Inversiones", "Regalos", "Otros"]
        cat = st.selectbox("Categoría", cat_lista)
        fecha = st.date_input("Fecha")
        metodo_pago = "Cuenta propia"
        if tipo == "Gasto":
            metodo_pago = st.selectbox("Método de Pago", ["Cuenta propia", "Efectivo", "Transferencia a tercero"], index=0)
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto (RD$)", min_value=0.01)
        
        if st.form_submit_button("Guardar Movimiento"):
            data = {
                'Fecha': str(fecha), 
                'Tipo': tipo, 
                'Categoría': cat, 
                'Descripción': desc, 
                'Monto': float(monto), 
                'Recibo_Adjunto': 'Sin recibo'
            }
            supabase.table("movimientos").insert(data).execute()
            
            if tipo == "Gasto" and metodo_pago == "Transferencia a tercero":
                monto_impuesto = float(monto) * 0.0020
                supabase.table("movimientos").insert({
                    'Fecha': str(fecha),
                    'Tipo': 'Gasto',
                    'Categoría': 'Impuesto',
                    'Descripción': 'Impuesto bancario (0.20% por transferencia a tercero)',
                    'Monto': monto_impuesto,
                    'Recibo_Adjunto': 'Sin recibo'
                }).execute()
                
            st.success("¡Guardado exitosamente!")
            st.rerun()

@st.dialog("🔍 Detalle del Movimiento")
def mostrar_detalle_modal(row):
    st.write(f"**Fecha:** {row['Fecha']}")
    st.write(f"**Tipo:** {row['Tipo']}")
    st.write(f"**Categoría:** {row['Categoría']}")
    st.write(f"**Descripción:** {row['Descripción']}")
    st.write(f"**Monto:** RD${float(row['Monto']):,.2f}")
    st.write(f"**Recibo Adjunto:** {row.get('Recibo_Adjunto', 'N/A')}")
    if st.button("Cerrar"):
        st.rerun()

@st.dialog("⚠️ Confirmar Eliminación")
def confirmar_eliminar(row):
    st.warning(f"¿Eliminará el registro: '{row['Descripción']}' por RD${float(row['Monto']):,.2f}? ¿Está seguro?")
    if st.button("Sí, eliminar permanentemente"):
        supabase.table("movimientos").delete().eq("id", int(row['id'])).execute()
        st.success("Registro eliminado.")
        st.rerun()

# --- CARGAR MOVIMIENTOS DESDE SUPABASE ---
response = supabase.table("movimientos").select("*").execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=['id', 'Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto', 'Recibo_Adjunto'])
if not df.empty and 'Monto' in df.columns:
    df['Monto'] = df['Monto'].astype(float)

# Encabezado con información de usuario, botón de agregar y cierre de sesión
col_t1, col_t2, col_t3, col_t4 = st.columns([2.5, 1, 1, 1])
with col_t1:
    st.title(f"📊 Dashboard — {st.session_state.rol}")
with col_t2:
    st.write(f"👤 {st.session_state.usuario}")
with col_t3:
    if st.button("➕ Agregar"):
        dialog_agregar()
with col_t4:
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.rol = None
        st.session_state.usuario = None
        st.rerun()

# Pestañas principales
tabs = st.tabs(["📊 Quincena Actual", "📋 Estado de Situación", "💳 Tarjeta Lafise", "📈 Tendencias", "📜 Movimientos"])

# PESTAÑA 1: QUINCENA ACTUAL
with tabs[0]:
    st.subheader("Resumen - Quincena Actual")
    
    ing = df[df['Tipo'] == 'Ingreso']['Monto'].sum() if not df.empty else 0
    gas = df[df['Tipo'] == 'Gasto']['Monto'].sum() if not df.empty else 0
    restante = st.session_state.presupuesto + ing - gas

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos Totales", f"RD${ing:,.2f}")
    col2.metric("Gastos Totales", f"RD${gas:,.2f}")
    col3.metric("Presupuesto Restante", f"RD${restante:,.2f}", f"Base: RD${st.session_state.presupuesto:,.2f}")

    if restante <= 1000:
        st.warning("⚠️ ¡Atención! Tu presupuesto restante está por debajo de RD$ 1,000.00")

    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Distribución de Gastos")
            df_gasto = df[df['Tipo'] == 'Gasto'].copy()
            if not df_gasto.empty:
                fig_pie = px.pie(df_gasto, values='Monto', names='Categoría', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            st.subheader("Ingresos vs Gastos")
            df_resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
            fig_bar = px.bar(df_resumen, x='Tipo', y='Monto', color='Tipo', text_auto='.2s')
            st.plotly_chart(fig_bar, use_container_width=True)

# PESTAÑA 2: ESTADO DE SITUACIÓN FORMAL (PREVISUALIZACIÓN)
with tabs[1]:
    st.subheader("📋 Previsualización del Estado de Situación Financiera")
    st.markdown("---")
    
    total_ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum() if not df.empty else 0
    total_gastos = df[df['Tipo'] == 'Gasto']['Monto'].sum() if not df.empty else 0
    balance_neto = total_ingresos - total_gastos

    col_es1, col_es2 = st.columns(2)
    with col_es1:
        st.markdown("### 🟢 ACTIVOS / ENTRADAS")
        st.metric("Total Ingresos Registrados", f"RD${total_ingresos:,.2f}")
        if not df[df['Tipo'] == 'Ingreso'].empty:
            st.dataframe(df[df['Tipo'] == 'Ingreso'][['Fecha', 'Categoría', 'Descripción', 'Monto']], use_container_width=True)
        else:
            st.info("No hay ingresos registrados.")

    with col_es2:
        st.markdown("### 🔴 PASIVOS / SALIDAS (GASTOS)")
        st.metric("Total Gastos Registrados", f"RD${total_gastos:,.2f}")
        if not df[df['Tipo'] == 'Gasto'].empty:
            st.dataframe(df[df['Tipo'] == 'Gasto'][['Fecha', 'Categoría', 'Descripción', 'Monto']], use_container_width=True)
        else:
            st.info("No hay gastos registrados.")

    st.markdown("---")
    st.metric("💎 BALANCE NETO GENERAL", f"RD${balance_neto:,.2f}", 
              delta="Saludable" if balance_neto >= 0 else "Déficit", delta_color="normal" if balance_neto >= 0 else "inverse")

# PESTAÑA 3: TARJETA LAFISE (VISA GOLD)
with tabs[2]:
    st.header("💳 Tarjeta de Crédito - Banco Lafise (Visa Gold)")
    st.write("**Terminal:** 5453")
    
    hoy = datetime.now()
    corte_actual = datetime(hoy.year, hoy.month, 15) if hoy.day <= 15 else (datetime(hoy.year + 1, 1, 15) if hoy.month == 12 else datetime(hoy.year, hoy.month + 1, 15))
    vencimiento = corte_actual + timedelta(days=26)
    limite_usd = 1735.00
    tasa_fija = 49.00
    limite_dop = limite_usd * tasa_fija
    
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Balance Actual DOP", f"RD$ {st.session_state.tc_dop:,.2f}", f"Límite: RD$ {limite_dop:,.2f}")
    tc2.metric("Balance Actual USD", f"US$ {st.session_state.tc_usd:,.2f}", f"Límite: US$ {limite_usd:,.2f}")
    tc3.metric("Fecha de Corte", corte_actual.strftime("%d/%m/%Y"), f"Vencimiento: {vencimiento.strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    if st.session_state.rol == "Administrador":
        st.subheader("Registrar Movimiento de Tarjeta")
        with st.form("form_tc"):
            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
            tc_moneda = c_m1.selectbox("Moneda", ["DOP", "USD"])
            tc_tipo = c_m2.selectbox("Acción", ["Consumo (Sube Balance)", "Abono / Pago (Baja Balance)"])
            tc_monto = c_m3.number_input("Monto", min_value=0.01, step=100.0)
            tc_desc = c_m4.text_input("Descripción")
            
            if st.form_submit_button("Aplicar a Tarjeta"):
                if tc_moneda == "DOP":
                    st.session_state.tc_dop += tc_monto if "Consumo" in tc_tipo else -tc_monto
                else:
                    st.session_state.tc_usd += tc_monto if "Consumo" in tc_tipo else -tc_monto
                
                nuevo_mov_tc = pd.DataFrame([{
                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                    'Moneda': tc_moneda, 'Tipo': tc_tipo, 'Monto': tc_monto, 'Descripcion': tc_desc
                }])
                st.session_state.tc_movs = pd.concat([st.session_state.tc_movs, nuevo_mov_tc], ignore_index=True)
                guardar_estado_tc()
                st.success("¡Movimiento de tarjeta registrado!")
                st.rerun()
                
    st.subheader("Historial de Tarjeta")
    if not st.session_state.tc_movs.empty:
        st.dataframe(st.session_state.tc_movs, use_container_width=True)
    else:
        st.info("No hay movimientos registrados en la tarjeta.")

# PESTAÑA 4: TENDENCIAS
with tabs[3]:
    st.subheader("📈 Gráfico de Tendencia Temporal")
    if not df.empty:
        df_tendencia = df.groupby(['Fecha', 'Tipo'])['Monto'].sum().reset_index()
        fig = px.line(df_tendencia, x='Fecha', y='Monto', color='Tipo', markers=True, title="Evolución de Ingresos y Gastos")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar tendencias.")

# PESTAÑA 5: MOVIMIENTOS Y ACCIONES (DETALLE Y ELIMINAR)
with tabs[4]:
    st.subheader("📜 Listado Completo de Movimientos")
    if not df.empty:
        for _, row in df.iterrows():
            cols = st.columns([1.5, 1, 1.5, 2.5, 1, 0.6, 0.6])
            cols[0].write(str(row['Fecha']))
            cols[1].write(str(row['Tipo']))
            cols[2].write(str(row['Categoría']))
            cols[3].write(str(row['Descripción']))
            cols[4].write(f"RD${float(row['Monto']):,.2f}")
            
            if cols[5].button("🔍", key=f"ver_{row['id']}"):
                mostrar_detalle_modal(row)
            if cols[6].button("🗑️", key=f"del_{row['id']}"):
                confirmar_eliminar(row)
    else:
        st.info("No hay movimientos registrados.")