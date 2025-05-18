import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd

# Archivo donde se guardan las órdenes
DATA_FILE = "ordenes_produccion.json"

# Lista de etapas en orden
ETAPAS = [
    "En cola",
    "Convertidora",
    "Guillotina",
    "Impresión GTOZ",
    "Impresión Komori",
    "Barnizado",
    "Plastificado",
    "Troquelado",
    "Acabado manual",
    "Acabado máquina",
    "Transporte",
    "OP Terminada"
]

# Usuarios simulados (usuario: contraseña, rol)
USUARIOS = {
    "admin": ("admin123", "admin"),
    "juan": ("1234", "convertidora"),
    "maria": ("abcd", "troquelado"),
}

# --------------------------------------------
# Funciones combinadas de utils.py aquí mismo
# --------------------------------------------

def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    else:
        return []

def guardar_datos(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def crear_nueva_op(cliente, descripcion, procesos):
    return {
        "id": f"OP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "cliente": cliente,
        "descripcion": descripcion,
        "procesos": procesos,
        "etapa_actual": "En cola",
        "historial": {
            "En cola": datetime.now().isoformat()
        }
    }

def mover_op(op, nueva_etapa):
    ahora = datetime.now().isoformat()
    op["etapa_actual"] = nueva_etapa
    op["historial"][nueva_etapa] = ahora

def calcular_duracion(historial, inicio, fin):
    if inicio in historial and fin in historial:
        t1 = datetime.fromisoformat(historial[inicio])
        t2 = datetime.fromisoformat(historial[fin])
        return str(t2 - t1)
    return "N/A"

def exportar_excel(datos):
    registros = []
    for op in datos:
        fila = {
            "ID": op["id"],
            "Cliente": op["cliente"],
            "Descripción": op["descripcion"],
            "Etapa actual": op["etapa_actual"]
        }
        for etapa in ETAPAS:
            fila[f"{etapa} - Timestamp"] = op["historial"].get(etapa, "")
        registros.append(fila)
    df = pd.DataFrame(registros)
    return df.to_excel("historial_produccion.xlsx", index=False)

# --------------------------------------------
# Interfaz Streamlit
# --------------------------------------------

st.set_page_config(page_title="Kanban Producción", layout="wide")

if "usuario" not in st.session_state:
    st.session_state.usuario = None
    st.session_state.rol = None

if st.session_state.usuario is None:
    st.title("🔐 Login")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        if username in USUARIOS and USUARIOS[username][0] == password:
            st.session_state.usuario = username
            st.session_state.rol = USUARIOS[username][1]
            st.success(f"Bienvenido {username}")
            st.experimental_rerun()
        else:
            st.error("Credenciales incorrectas")
else:
    st.sidebar.title(f"👤 Usuario: {st.session_state.usuario}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.usuario = None
        st.session_state.rol = None
        st.experimental_rerun()

    st.title("📦 Sistema Kanban de Producción")

    datos = cargar_datos()

    # Sección para agregar nuevas OPs
    if st.session_state.rol == "admin":
        st.subheader("➕ Agregar nueva Orden de Producción")
        with st.form("form_nueva_op"):
            cliente = st.text_input("Cliente")
            descripcion = st.text_input("Descripción del producto")
            procesos_seleccionados = st.multiselect("Procesos involucrados", ETAPAS, default=["En cola", "Transporte", "OP Terminada"])
            submitted = st.form_submit_button("Agregar")
            if submitted and cliente and descripcion and procesos_seleccionados:
                nueva_op = crear_nueva_op(cliente, descripcion, procesos_seleccionados)
                datos.append(nueva_op)
                guardar_datos(datos)
                st.success(f"Orden {nueva_op['id']} agregada")

    # Tablero Kanban
    st.subheader("📋 Tablero Kanban")
    cols = st.columns(len(ETAPAS))
    for i, etapa in enumerate(ETAPAS):
        with cols[i]:
            st.markdown(f"### {etapa}")
            for op in datos:
                if op["etapa_actual"] == etapa and etapa in op["procesos"]:
                    st.markdown(f"🆔 **{op['id']}**")
                    st.markdown(f"👤 {op['cliente']}")
                    st.markdown(f"📝 {op['descripcion']}")
                    etapa_actual_index = op["procesos"].index(op["etapa_actual"])
                    if etapa_actual_index + 1 < len(op["procesos"]):
                        siguiente = op["procesos"][etapa_actual_index + 1]
                        if st.button(f"➡️ Mover a {siguiente}", key=f"{op['id']}-{siguiente}"):
                            mover_op(op, siguiente)
                            guardar_datos(datos)
                            st.experimental_rerun()

    # Historial
    st.subheader("📑 Historial de Producción")
    filtro_cliente = st.text_input("🔍 Filtrar por cliente")
    historial = []
    for op in datos:
        if filtro_cliente.lower() in op["cliente"].lower():
            fila = {
                "ID": op["id"],
                "Cliente": op["cliente"],
                "Etapa actual": op["etapa_actual"]
            }
            for etapa in ETAPAS:
                fila[f"{etapa}"] = op["historial"].get(etapa, "")
            historial.append(fila)
    df = pd.DataFrame(historial)
    st.dataframe(df, use_container_width=True)

    if st.button("📤 Exportar historial a Excel"):
        exportar_excel(datos)
        st.success("Archivo exportado como historial_produccion.xlsx")
