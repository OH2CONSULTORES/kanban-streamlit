import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import hashlib

# Definición de etapas
ETAPAS = [
    "En Cola", "Convertidora", "Guillotina",
    "Impresión GTOZ", "Impresión Komori", "Barnizado",
    "Plastificado", "Troquelado", "Acabado Manual",
    "Acabado Máquina", "Transporte", "OP Terminados"
]

# --- FUNCIONES AUXILIARES ---

def hash_password(password):
    """Hashea la contraseña para guardarla."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(username, password):
    """Verifica si usuario y contraseña son correctos."""
    if "users" not in st.session_state:
        return False
    hashed = hash_password(password)
    user = st.session_state.users.get(username)
    if user and user["password"] == hashed:
        return True
    return False

def user_role(username):
    """Devuelve el rol del usuario."""
    return st.session_state.users.get(username, {}).get("role", None)

def can_move_op(user, etapa_op):
    """Determina si el usuario puede mover OP en la etapa dada."""
    role = user_role(user)
    if role in ["maestro", "planificador"]:
        return True
    elif role == "trabajador":
        # El trabajador solo puede mover OP en SU etapa
        etapa_usuario = st.session_state.users[user].get("etapa")
        return etapa_usuario == etapa_op
    return False

# --- INICIALIZACIÓN DE ESTADO ---

if "users" not in st.session_state:
    # Usuarios por defecto: admin maestro y planificador
    st.session_state.users = {
        "admin": {"password": hash_password("admin123"), "role": "maestro"},
        "planificador": {"password": hash_password("plan123"), "role": "planificador"},
        # Ejemplo trabajador para Troquelado
        "trabajador_troquel": {"password": hash_password("troquel123"), "role": "trabajador", "etapa": "Troquelado"},
    }

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "ops" not in st.session_state:
    st.session_state.ops = []

# --- LOGIN ---

def login():
    st.title("Login - Kanban de Producción Lean")

    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if check_password(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Bienvenido, {username} ({user_role(username)})")
            st.experimental_rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

if not st.session_state.logged_in:
    login()
    st.stop()

# --- PÁGINA PRINCIPAL ---

st.title(f"KANBAN DE PRODUCCIÓN LEAN - Usuario: {st.session_state.username} ({user_role(st.session_state.username)})")

# --- ADMINISTRACIÓN DE USUARIOS (solo maestro) ---
if user_role(st.session_state.username) == "maestro":
    with st.expander("👤 Gestión de Usuarios (solo Maestro)"):
        st.subheader("Agregar nuevo usuario")
        nuevo_usuario = st.text_input("Nuevo Usuario")
        nueva_contrasena = st.text_input("Nueva Contraseña", type="password")
        rol_usuario = st.selectbox("Rol", options=["maestro", "planificador", "trabajador"])
        etapa_trabajador = None
        if rol_usuario == "trabajador":
            etapa_trabajador = st.selectbox("Asignar etapa al trabajador", options=ETAPAS)

        if st.button("Agregar Usuario"):
            if nuevo_usuario.strip() == "" or nueva_contrasena.strip() == "":
                st.error("Debe ingresar usuario y contraseña.")
            elif nuevo_usuario in st.session_state.users:
                st.error("El usuario ya existe.")
            else:
                usuario_data = {
                    "password": hash_password(nueva_contrasena),
                    "role": rol_usuario
                }
                if rol_usuario == "trabajador":
                    usuario_data["etapa"] = etapa_trabajador
                st.session_state.users[nuevo_usuario] = usuario_data
                st.success(f"Usuario '{nuevo_usuario}' creado con rol '{rol_usuario}'.")
        st.markdown("### Usuarios actuales")
        df_usuarios = []
        for u, data in st.session_state.users.items():
            etapa = data.get("etapa", "")
            df_usuarios.append({"Usuario": u, "Rol": data["role"], "Etapa (si trabajador)": etapa})
        st.table(df_usuarios)

# --- AGREGAR NUEVA OP (solo maestro y planificador) ---
if user_role(st.session_state.username) in ["maestro", "planificador"]:
    with st.expander("➕ Agregar nueva OP"):
        cliente = st.text_input("Cliente", key="cliente")
        numero_op = st.text_input("Número OP", key="numero_op")
        etapas_seleccionadas = st.multiselect("Seleccione etapas", ETAPAS, default=ETAPAS)
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

# --- MOSTRAR TABLERO KANBAN ---

st.subheader("Tablero Kanban")

st.markdown("""
<style>
.kanban-container {
  display: flex;
  overflow-x: auto;
  padding: 10px 0;
  gap: 15px;
}
.kanban-column {
  flex: 0 0 250px;
  background-color: #f0f2f6;
  border-radius: 8px;
  padding: 10px;
  min-height: 300px;
}
.kanban-card {
  background: white;
  padding: 8px;
  margin-bottom: 10px;
  border-radius: 5px;
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.1);
}
</style>
""", unsafe_allow_html=True)

kanban_html = '<div class="kanban-container">'

for etapa in ETAPAS:
    kanban_html += f'<div class="kanban-column"><h4>{etapa}</h4>'

    # Filtrar OP según visibilidad
    if user_role(st.session_state.username) in ["maestro", "planificador"]:
        # Ven todo
        ops_en_etapa = [op for op in st.session_state.ops if etapa in op["etapas"] and op["etapas"][op["actual"]] == etapa]
    else:
        # Trabajador solo ve OP en su etapa asignada
        etapa_usuario = st.session_state.users[st.session_state.username]["etapa"]
        if etapa == etapa_usuario:
            ops_en_etapa = [op for op in st.session_state.ops if etapa in op["etapas"] and op["etapas"][op["actual"]] == etapa]
        else:
            ops_en_etapa = []

    if ops_en_etapa:
        for idx, op in enumerate(ops_en_etapa):
            kanban_html += f'<div class="kanban-card"><b>OP:</b> {op["numero_op"]}<br><b>Cliente:</b> {op["cliente"]}</div>'
    else:
        kanban_html += "<i>Sin OP</i>"

    kanban_html += '</div>'

kanban_html += '</div>'

st.markdown(kanban_html, unsafe_allow_html=True)

# --- BOTONES PARA AVANZAR OP ---

st.subheader("Mover OP a siguiente etapa")

for idx, op in enumerate(st.session_state.ops):
    etapa_actual = op["etapas"][op["actual"]]
    # Mostrar solo si el usuario puede mover OP en esa etapa
    if can_move_op(st.session_state.username, etapa_actual):
        st.markdown(f"**OP:** {op['numero_op']} - **Cliente:** {op['cliente']} - **Etapa actual:** {etapa_actual}")
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

# --- HISTORIAL Y ANÁLISIS ---

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

st.subheader("Historial y Análisis")
if st.button("Mostrar Historial"):
    # Mostrar todo solo para maestro y planificador
    if user_role(st.session_state.username) in ["maestro", "planificador"]:
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
            label="📥 Descargar Historial en Excel",
            data=excel_data,
            file_name="historial_kanban.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No tienes permiso para ver el historial completo.")

else:
    st.info("Haz clic en 'Mostrar Historial' para ver los datos.")

# --- OPCIÓN DE CERRAR SESIÓN ---
if st.button("Cerrar sesión"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.experimental_rerun()
