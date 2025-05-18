import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

ETAPAS = [
    "En Cola", "Convertidora", "Guillotina",
    "Impresión GTOZ", "Impresión Komori", "Barnizado",
    "Plastificado", "Troquelado", "Acabado Manual",
    "Acabado Máquina", "Transporte", "OP Terminados"
]

USUARIOS = {
    "admin": {"password": "admin123", "roles": ["admin"]},
    "convertidora": {"password": "convpass", "roles": ["Convertidora"]},
    "troquelado": {"password": "troquel123", "roles": ["Troquelado"]},
}

def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        if username in USUARIOS and USUARIOS[username]["password"] == password:
            st.session_state["usuario"] = username
            st.session_state["roles"] = USUARIOS[username]["roles"]
            st.success(f"Bienvenido {username}")
        else:
            st.sidebar.error("Usuario o contraseña incorrectos")

def exportar_excel(ops):
    output = BytesIO()
    df_rows = []
    for op in ops:
        for etapa, tiempos in op["tiempos"].items():
            entrada, salida = tiempos
            duracion = (salida - entrada).total_seconds() / 60 if entrada and salida else None
            df_rows.append({
                "Número OP": op["numero_op"],
                "Cliente": op["cliente"],
                "Etapa": etapa,
                "Entrada": entrada,
                "Salida": salida,
                "Duración (min)": round(duracion, 1) if duracion else ""
            })
    df = pd.DataFrame(df_rows)
    df.to_excel(output, index=False)
    return output

if "usuario" not in st.session_state:
    login()
    st.stop()

usuario = st.session_state["usuario"]
roles = st.session_state["roles"]

if "ops" not in st.session_state:
    st.session_state.ops = []

st.title(f"Kanban de Producción - Usuario: {usuario}")

if "admin" in roles:
    with st.expander("➕ Agregar nueva OP"):
        cliente = st.text_input("Cliente", key="cliente")
        numero_op = st.text_input("Número OP", key="numero_op")
        etapas_seleccionadas = st.multiselect("Seleccione etapas", ETAPAS, default=["En Cola", "Transporte", "OP Terminados"])
        if st.button("Agregar OP"):
            if not cliente or not numero_op:
                st.error("Debe ingresar Cliente y Número OP.")
            else:
                op = {
                    "cliente": cliente,
                    "numero_op": numero_op,
                    "etapas": etapas_seleccionadas,
                    "actual": 0,
                    "tiempos": {etapa: [None, None] for etapa in etapas_seleccionadas}
                }
                primer_etapa = etapas_seleccionadas[0]
                op["tiempos"][primer_etapa][0] = datetime.now()
                st.session_state.ops.append(op)
                st.success(f"OP {numero_op} agregada.")

if "admin" in roles:
    ops_visibles = st.session_state.ops
else:
    ops_visibles = [op for op in st.session_state.ops if op["etapas"][op["actual"]] in roles]

st.subheader("Tablero Kanban")

etapas_visibles = ETAPAS if "admin" in roles else roles

kanban_html = '<div class="kanban-container">'
for etapa in ETAPAS:
    if etapa not in etapas_visibles:
        continue
    kanban_html += f'<div class="kanban-column"><h4>{etapa}</h4>'
    ops_en_etapa = [op for op in ops_visibles if op["etapas"][op["actual"]] == etapa]
    if ops_en_etapa:
        for idx, op in enumerate(ops_en_etapa):
            kanban_html += f'<div class="kanban-card"><b>OP:</b> {op["numero_op"]}<br><b>Cliente:</b> {op["cliente"]}</div>'
    else:
        kanban_html += "<i>Sin OP</i>"
    kanban_html += '</div>'
kanban_html += '</div>'

st.markdown(kanban_html, unsafe_allow_html=True)

st.subheader("Mover OP a siguiente etapa")
for idx, op in enumerate(ops_visibles):
    etapa_actual = op["etapas"][op["actual"]]
    st.markdown(f"**OP:** {op['numero_op']} - **Cliente:** {op['cliente']} - **Etapa actual:** {etapa_actual}")
    if ("admin" in roles) or (etapa_actual in roles):
        if st.button(f"Avanzar OP {op['numero_op']}", key=f"avanzar_{idx}"):
            actual_idx = op["actual"]
            actual_etapa = op["etapas"][actual_idx]
            op["tiempos"][actual_etapa][1] = datetime.now()
            if actual_idx + 1 < len(op["etapas"]):
                siguiente_etapa = op["etapas"][actual_idx + 1]
                op["tiempos"][siguiente_etapa][0] = datetime.now()
                op["actual"] += 1
            else:
                st.success(f"OP {op['numero_op']} finalizada.")
    else:
        st.write("_No autorizado para mover esta OP_")

if "admin" in roles:
    st.subheader("Historial y Análisis")
    if st.button("Mostrar Historial"):
        historial = []
        for op in st.session_state.ops:
            for etapa, tiempos in op["tiempos"].items():
                entrada, salida = tiempos
                duracion = (salida - entrada).total_seconds() / 60 if entrada and salida else None
                historial.append({
                    "Número OP": op["numero_op"],
                    "Cliente": op["cliente"],
                    "Etapa": etapa,
                    "Entrada": entrada.strftime("%Y-%m-%d %H:%M:%S") if entrada else "",
                    "Salida": salida.strftime("%Y-%m-%d %H:%M:%S") if salida else "",
                    "Duración (min)": round(duracion, 1) if duracion else ""
                })
        df_hist = pd.DataFrame(historial)
        st.dataframe(df_hist)

        excel_data = exportar_excel(st.session_state.ops)
        st.download_button(
            label="\ud83d\udcc5 Descargar Historial en Excel",
            data=excel_data,
            file_name="historial_kanban.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("No autorizado para ver historial.")