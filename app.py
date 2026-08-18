import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
import json
from datetime import datetime, timedelta
from fpdf import FPDF

# Configuración de la página
st.set_page_config(page_title="Gestor Financiero Pro", page_icon="🏦", layout="wide")

# --- GESTIÓN DE USUARIOS (JSON) ---
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

usuarios_db = cargar_usuarios()

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
if not os.path.exists("recibos"): 
    os.makedirs("recibos")

def generar_pdf(df_mov, resumen, fecha_cierre):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="ESTADO DE SITUACION - CORTE QUINCENAL", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Fecha de Cierre: {fecha_cierre}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Resumen Financiero", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 8, txt=f"Ingresos Totales: RD$ {resumen['ingresos']:,.2f}", ln=True)
    pdf.cell(200, 8, txt=f"Gastos Totales: RD$ {resumen['gastos']:,.2f}", ln=True)
    pdf.cell(200, 8, txt=f"Presupuesto Final Restante: RD$ {resumen['presupuesto']:,.2f}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Registro de Movimientos", ln=True)
    pdf.set_font("Arial", '', 10)
    for _, row in df_mov.iterrows():
        texto = f"{row['Fecha']} | {row['Tipo']}: {row['Categoría']} | RD${row['Monto']} | {row['Descripción']}"
        texto_limpio = texto.replace('ó','o').replace('í','i').replace('á','a').replace('é','e').replace('ú','u').replace('ñ','n')
        pdf.cell(200, 6, txt=texto_limpio, ln=True)
    return pdf.output(dest='S').encode('latin-1')

def cargar_csv(nombre, cols):
    return pd.read_csv(nombre) if os.path.exists(nombre) else pd.DataFrame(columns=cols)

if 'movimientos' not in st.session_state: 
    st.session_state.movimientos = cargar_csv('movimientos.csv', ['Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto', 'Recibo_Adjunto'])
    if st.session_state.movimientos.empty:
        hoy = datetime.now().strftime("%Y-%m-%d")
        gastos_fijos_iniciales = pd.DataFrame([
            {'Fecha': hoy, 'Tipo': 'Gasto', 'Categoría': 'Combustible', 'Descripción': 'Combustible Quincenal Fijo', 'Monto': 5000.0, 'Recibo_Adjunto': 'Sin recibo'},
            {'Fecha': hoy, 'Tipo': 'Gasto', 'Categoría': 'Deudas', 'Descripción': 'Cuota Alimentaria Hijo', 'Monto': 2500.0, 'Recibo_Adjunto': 'Sin recibo'}
        ])
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, gastos_fijos_iniciales], ignore_index=True)
        st.session_state.movimientos.to_csv('movimientos.csv', index=False)

if 'historico_cierres' not in st.session_state: 
    st.session_state.historico_cierres = cargar_csv('historico_cierres.csv', ['Fecha_Cierre', 'Ingresos', 'Gastos', 'Presupuesto_Restante'])
if 'historico_movimientos' not in st.session_state: 
    st.session_state.historico_movimientos = cargar_csv('historico_movimientos.csv', ['Cierre_ID', 'Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto', 'Recibo_Adjunto'])

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

# --- VENTANA MODAL (DIÁLOGO) PARA DETALLES ---
@st.dialog("📋 Detalle del Movimiento y Recibo")
def mostrar_detalle_modal(row):
    st.markdown(f"### {row['Tipo']}: {row['Categoría']}")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown(f"**Fecha:** {row['Fecha']}")
        st.markdown(f"**Monto:** RD$ {row['Monto']:,.2f}")
    with col_m2:
        st.markdown(f"**Descripción:** {row['Descripción']}")
    
    st.markdown("---")
    st.markdown("**Archivo Adjunto / Recibo:**")
    if row['Recibo_Adjunto'] != "Sin recibo" and os.path.exists(str(row['Recibo_Adjunto'])):
        ruta_archivo = row['Recibo_Adjunto']
        extension = ruta_archivo.lower().split('.')[-1]
        if extension in ['png', 'jpg', 'jpeg']:
            st.image(ruta_archivo, caption="Vista previa del recibo", width=400)
        with open(ruta_archivo, "rb") as archivo_adjunto:
            st.download_button(
                label="👁️ Visualizar / Descargar Recibo Adjunto",
                data=archivo_adjunto,
                file_name=os.path.basename(ruta_archivo),
                key=f"modal_btn_{row.name}"
            )
    else:
        st.info("Este movimiento no tiene ningún recibo o archivo adjunto.")

# Encabezado del Dashboard y Botón de Salida
col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.title(f"📊 Dashboard Financiero — Rol: {st.session_state.rol}")
with col_t2:
    st.write(f"👤 {st.session_state.usuario}")
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.rol = None
        st.session_state.usuario = None
        st.rerun()

# --- BARRA LATERAL ( SOLO ADMIN ) ---
if st.session_state.rol == "Administrador":
    st.sidebar.header("1. Ajustar Base")
    nuevo_presupuesto = st.sidebar.number_input("Presupuesto Base (RD$)", min_value=0.0, value=float(st.session_state.presupuesto), step=1000.0)
    if st.sidebar.button("Actualizar Base"):
        st.session_state.presupuesto = nuevo_presupuesto
        st.sidebar.success("¡Base actualizada!")

    st.sidebar.markdown("---")
    st.sidebar.header("2. Registrar Movimiento")
    tipo = st.sidebar.radio("Tipo", ["Gasto", "Ingreso"])
    
    cat_lista = ["Alimentación", "Combustible", "Supermercado", "Tiendas", "Deudas", "Impuesto", "Transporte", "Vivienda", "Servicios", "Entretenimiento", "Otros"] if tipo == "Gasto" else ["Salario", "Ventas", "Negocio", "Inversiones", "Regalos", "Otros"]
    
    fecha = st.sidebar.date_input("Fecha")
    cat = st.sidebar.selectbox("Categoría", cat_lista)
    
    # NUEVA OPCIÓN: Método de pago (Cuenta propia por defecto)
    metodo_pago = "Cuenta propia"
    if tipo == "Gasto":
        metodo_pago = st.sidebar.selectbox("Método de Pago", ["Cuenta propia", "Efectivo", "Transferencia a tercero"], index=0)

    desc = st.sidebar.text_input("Descripción")
    monto = st.sidebar.number_input("Monto (RD$)", min_value=0.01)
    recibo = st.sidebar.file_uploader("Recibo", type=["png", "jpg", "jpeg", "pdf"])

    if st.sidebar.button("Guardar"):
        ruta_recibo = "Sin recibo"
        if recibo:
            ruta_recibo = os.path.join("recibos", recibo.name)
            with open(ruta_recibo, "wb") as f: f.write(recibo.getbuffer())
        
        # Lista para acumular los movimientos a insertar
        registros_a_guardar = []
        
        # Gasto principal
        registros_a_guardar.append({
            'Fecha': fecha, 
            'Tipo': tipo, 
            'Categoría': cat, 
            'Descripción': desc, 
            'Monto': monto, 
            'Recibo_Adjunto': ruta_recibo
        })
        
        # Si es Gasto por Transferencia a tercero, calcular 0.20% de impuesto bancario
        if tipo == "Gasto" and metodo_pago == "Transferencia a tercero":
            monto_impuesto = monto * 0.0020  # 0.20%
            registros_a_guardar.append({
                'Fecha': fecha,
                'Tipo': 'Gasto',
                'Categoría': 'Impuesto',
                'Descripción': 'Impuesto bancario (0.20% por transferencia a tercero)',
                'Monto': monto_impuesto,
                'Recibo_Adjunto': 'Sin recibo'
            })
            
        nuevo_df = pd.DataFrame(registros_a_guardar)
        st.session_state.movimientos = pd.concat([st.session_state.movimientos, nuevo_df], ignore_index=True)
        st.session_state.movimientos.to_csv('movimientos.csv', index=False)
        st.sidebar.success("¡Guardado exitosamente!")
        st.rerun()
else:
    st.sidebar.info("Modo Lector: Visualización de datos.")

# --- PESTAÑAS SEGÚN EL ROL ---
if st.session_state.rol == "Administrador":
    tabs = st.tabs(["📊 Quincena Actual", "💳 Tarjeta Lafise", "📁 Histórico y Tendencias", "👥 Usuarios"])
else:
    tabs = st.tabs(["📊 Quincena Actual", "💳 Tarjeta Lafise", "📁 Histórico y Tendencias"])

# PESTAÑA 1: QUINCENA ACTUAL
with tabs[0]:
    df = st.session_state.movimientos
    ing = df[df['Tipo'] == 'Ingreso']['Monto'].sum() if not df.empty else 0
    gas = df[df['Tipo'] == 'Gasto']['Monto'].sum() if not df.empty else 0
    restante = st.session_state.presupuesto + ing - gas

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos", f"RD${ing:,.2f}")
    col2.metric("Gastos", f"RD${gas:,.2f}")
    col3.metric("Restante", f"RD${restante:,.2f}")

    if restante <= 1000:
        st.warning("⚠️ ¡Atención! Tu presupuesto restante está por debajo de RD$ 1,000.00")

    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Distribución de Gastos (Pie)")
            fig_pie = px.pie(df[df['Tipo'] == 'Gasto'], values='Monto', names='Categoría', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            st.subheader("Ingresos vs Gastos (Barras)")
            df_resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
            fig_bar = px.bar(df_resumen, x='Tipo', y='Monto', color='Tipo', text_auto='.2s')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.subheader("🔍 Tabla de Movimientos y Consulta por Icono")
        for index, row in df.iterrows():
            col_r1, col_r2, col_r3, col_r4, col_r5, col_r6 = st.columns([1.5, 1, 1.5, 2, 1, 1])
            col_r1.write(str(row['Fecha']))
            col_r2.write(str(row['Tipo']))
            col_r3.write(str(row['Categoría']))
            col_r4.write(str(row['Descripción']))
            col_r5.write(f"RD${row['Monto']:,.2f}")
            
            tiene_adjunto = row['Recibo_Adjunto'] != "Sin recibo" and os.path.exists(str(row['Recibo_Adjunto']))
            texto_boton = "📎 🔍 Ver" if tiene_adjunto else "🔍 Ver"
            
            if col_r6.button(texto_boton, key=f"btn_modal_{index}"):
                mostrar_detalle_modal(row)
    else:
        st.info("No hay movimientos registrados en la quincena actual.")

# PESTAÑA 2: TARJETA LAFISE (VISA GOLD)
with tabs[1]:
    st.header("💳 Tarjeta de Crédito - Banco Lafise (Visa Gold)")
    st.write("**Terminal:** 5453")
    
    hoy = datetime.now()
    if hoy.day <= 15:
        corte_actual = datetime(hoy.year, hoy.month, 15)
        if hoy.month == 1:
            corte_anterior = datetime(hoy.year - 1, 12, 15)
        else:
            corte_anterior = datetime(hoy.year, hoy.month - 1, 15)
    else:
        corte_anterior = datetime(hoy.year, hoy.month, 15)
        if hoy.month == 12:
            corte_actual = datetime(hoy.year + 1, 1, 15)
        else:
            corte_actual = datetime(hoy.year, hoy.month + 1, 15)
            
    vencimiento = corte_actual + timedelta(days=26)
    
    limite_usd = 1735.00
    tasa_fija = 49.00
    limite_dop = limite_usd * tasa_fija
    
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Balance Actual DOP", f"RD$ {st.session_state.tc_dop:,.2f}", f"Límite: RD$ {limite_dop:,.2f}")
    tc2.metric("Balance Actual USD", f"US$ {st.session_state.tc_usd:,.2f}", f"Límite: US$ {limite_usd:,.2f}")
    tc3.metric("Fecha de Corte Actual", corte_actual.strftime("%d/%m/%Y"), f"Vencimiento: {vencimiento.strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    
    if st.session_state.rol == "Administrador":
        st.subheader("Registrar Movimiento de Tarjeta")
        with st.form("form_tc"):
            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
            tc_moneda = c_m1.selectbox("Moneda", ["DOP", "USD"])
            tc_tipo = c_m2.selectbox("Acción", ["Consumo (Sube Balance)", "Abono / Pago (Baja Balance)"])
            tc_monto = c_m3.number_input("Monto", min_value=0.01, step=100.0)
            tc_desc = c_m4.text_input("Descripción / Establecimiento")
            
            submit_tc = st.form_submit_button("Aplicar a Tarjeta")
            if submit_tc:
                if tc_moneda == "DOP":
                    if "Consumo" in tc_tipo:
                        st.session_state.tc_dop += tc_monto
                    else:
                        st.session_state.tc_dop -= tc_monto
                else:
                    if "Consumo" in tc_tipo:
                        st.session_state.tc_usd += tc_monto
                    else:
                        st.session_state.tc_usd -= tc_monto
                
                nuevo_mov_tc = pd.DataFrame([{
                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                    'Moneda': tc_moneda,
                    'Tipo': tc_tipo,
                    'Monto': tc_monto,
                    'Descripcion': tc_desc
                }])
                st.session_state.tc_movs = pd.concat([st.session_state.tc_movs, nuevo_mov_tc], ignore_index=True)
                guardar_estado_tc()
                st.success("¡Movimiento de tarjeta registrado con éxito!")
                st.rerun()
                
    st.subheader("Historial de Movimientos de la Tarjeta")
    if not st.session_state.tc_movs.empty:
        st.dataframe(st.session_state.tc_movs, use_container_width=True)
    else:
        st.info("No hay movimientos registrados en esta tarjeta aún.")

# PESTAÑA 3: HISTÓRICO, TENDENCIAS Y VISTA PREVIA
tab_hist = tabs[2]
with tab_hist:
    st.header("📄 Vista Previa del Estado de Situación Actual")
    st.write("Aquí puedes visualizar cómo quedará el resumen financiero de la quincena actual antes de ejecutar el cierre definitivo.")
    
    df_actual = st.session_state.movimientos
    ing_prev = df_actual[df_actual['Tipo'] == 'Ingreso']['Monto'].sum() if not df_actual.empty else 0
    gas_prev = df_actual[df_actual['Tipo'] == 'Gasto']['Monto'].sum() if not df_actual.empty else 0
    restante_prev = st.session_state.presupuesto + ing_prev - gas_prev
    
    vp1, vp2, vp3 = st.columns(3)
    vp1.metric("Ingresos Totales (Prev)", f"RD$ {ing_prev:,.2f}")
    vp2.metric("Gastos Totales (Prev)", f"RD$ {gas_prev:,.2f}")
    vp3.metric("Presupuesto Restante (Prev)", f"RD$ {restante_prev:,.2f}")
    
    with st.expander("🔍 Ver listado completo de movimientos que irán en el corte"):
        if not df_actual.empty:
            st.dataframe(df_actual, use_container_width=True)
        else:
            st.info("No hay movimientos en la quincena actual.")

    st.markdown("---")
    st.header("Cierre de Quincena y Acciones")
    
    if st.session_state.rol == "Administrador":
        if not df_actual.empty:
            if st.button("🔴 Generar Cierre Quincenal", use_container_width=True):
                fecha_c = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                resumen = {'ingresos': ing_prev, 'gastos': gas_prev, 'presupuesto': restante_prev}
                
                nuevo_cierre = pd.DataFrame({'Fecha_Cierre': [fecha_c], 'Ingresos': [ing_prev], 'Gastos': [gas_prev], 'Presupuesto_Restante': [restante_prev]})
                st.session_state.historico_cierres = pd.concat([st.session_state.historico_cierres, nuevo_cierre], ignore_index=True)
                st.session_state.historico_cierres.to_csv('historico_cierres.csv', index=False)
                
                df_c = df_actual.copy()
                df_c['Cierre_ID'] = fecha_c
                st.session_state.historico_movimientos = pd.concat([st.session_state.historico_movimientos, df_c], ignore_index=True)
                st.session_state.historico_movimientos.to_csv('historico_movimientos.csv', index=False)
                
                pdf_b = generar_pdf(df_c, resumen, fecha_c)
                st.session_state.ultimo_pdf = pdf_b
                
                hoy_str = datetime.now().strftime("%Y-%m-%d")
                gastos_fijos_iniciales = pd.DataFrame([
                    {'Fecha': hoy_str, 'Tipo': 'Gasto', 'Categoría': 'Combustible', 'Descripción': 'Combustible Quincenal Fijo', 'Monto': 5000.0, 'Recibo_Adjunto': 'Sin recibo'},
                    {'Fecha': hoy_str, 'Tipo': 'Gasto', 'Categoría': 'Deudas', 'Descripción': 'Cuota Alimentaria Hijo', 'Monto': 2500.0, 'Recibo_Adjunto': 'Sin recibo'}
                ])
                st.session_state.movimientos = gastos_fijos_iniciales
                st.session_state.movimientos.to_csv('movimientos.csv', index=False)
                
                st.success("¡Cierre generado con éxito!")
                st.rerun()
        else:
            st.info("No hay registros para cerrar.")
    else:
        st.info("Solo el Administrador puede realizar cierres.")

    if 'ultimo_pdf' in st.session_state:
        st.download_button("📥 Descargar PDF del Último Cierre", data=st.session_state.ultimo_pdf, file_name="Cierre_Quincenal.pdf", mime="application/pdf")

    st.markdown("---")
    st.header("📈 Gráfico de Tendencia Histórica")
    if not st.session_state.historico_cierres.empty:
        df_hist = st.session_state.historico_cierres.melt(id_vars=['Fecha_Cierre'], value_vars=['Ingresos', 'Gastos', 'Presupuesto_Restante'], var_name='Métrica', value_name='Monto')
        fig_tendencia = px.line(df_hist, x='Fecha_Cierre', y='Monto', color='Métrica', markers=True, title="Evolución Financiera por Quincena")
        st.plotly_chart(fig_tendencia, use_container_width=True)

# PESTAÑA 4: GESTIÓN DE USUARIOS (SOLO ADMIN)
if st.session_state.rol == "Administrador" and len(tabs) > 3:
    with tabs[3]:
        st.header("Administración de Usuarios")
        db_u = cargar_usuarios()
        c_reg, c_list = st.columns(2)
        with c_reg:
            st.subheader("Crear Usuario")
            with st.form("nuevo_u"):
                n_usr = st.text_input("Usuario")
                n_pas = st.text_input("Contraseña", type="password")
                n_rol = st.selectbox("Rol", ["Lector", "Administrador"])
                if st.form_submit_button("Crear"):
                    if n_usr and n_usr not in db_u:
                        db_u[n_usr] = {"password": n_pas, "rol": n_rol}
                        with open(ARCHIVO_USUARIOS, 'w') as f: json.dump(db_u, f)
                        st.success(f"Usuario {n_usr} creado.")
                        st.rerun()
                    else:
                        st.error("Nombre inválido o ya existe.")
        with c_list:
            st.subheader("Usuarios Registrados")
            for u, info in db_u.items():
                col_u1, col_u2, col_u3 = st.columns([2, 2, 1])
                col_u1.write(f"**{u}**")
                col_u2.write(f"*{info['rol']}*")
                if u != "admin":
                    if col_u3.button("Eliminar", key=f"del_{u}"):
                        del db_u[u]
                        with open(ARCHIVO_USUARIOS, 'w' ) as f: json.dump(db_u, f)
                        st.rerun()
                else:
                    col_u3.write("Protegido")   