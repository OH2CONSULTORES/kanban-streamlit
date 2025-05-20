import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import hashlib
import sqlite3

# Funciones de BD
def crear_base_datos():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_produccion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ome TEXT,
            cliente TEXT,
            f_ini TEXT,
            f_fin TEXT,
            etapa TEXT,
            t_ini TEXT,
            t_fin TEXT,
            duracion REAL
        )
    ''')
    conn.commit()
    conn.close()

def crear_tabla_usuarios():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            etapa TEXT
        )
    ''')
    conn.commit()
    conn.close()


def guardar_usuario(username, password, role, etapa=None):
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO usuarios (username, password, role, etapa)
        VALUES (?, ?, ?, ?)
    ''', (username, password, role, etapa))
    conn.commit()
    conn.close()

def cargar_usuarios():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, password, role, etapa FROM usuarios')
    usuarios = cursor.fetchall()
    conn.close()
    user_dict = {}
    for u, p, r, e in usuarios:
        # Si la contraseña no tiene formato hash (64 caracteres hex), la hasheamos y guardamos
        if len(p) != 64:
            p_hashed = hash_password(p)
            guardar_usuario(u, p_hashed, r, e)
        else:
            p_hashed = p
        user_dict[u] = {"password": p_hashed, "role": r}
        if r == "trabajador":
            user_dict[u]["etapa"] = e
    return user_dict

def eliminar_usuario(username):
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM usuarios WHERE username = ?', (username,))
    conn.commit()
    conn.close()

def insertar_historial(numero_ome, cliente, f_ini, f_fin, etapa, t_ini, t_fin, duracion):
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO historial_produccion (numero_ome, cliente, f_ini, f_fin, etapa, t_ini, t_fin, duracion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (numero_ome, cliente, f_ini, f_fin, etapa, t_ini, t_fin, duracion))
    conn.commit()
    conn.close()

def obtener_historial():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('SELECT numero_ome, cliente, f_ini, f_fin, etapa, t_ini, t_fin, duracion FROM historial_produccion')
    registros = cursor.fetchall()
    conn.close()
    return registros

# Al iniciar la app
crear_base_datos()
crear_tabla_usuarios()

# Definición de etapas
ETAPAS = [
    "En Cola", "Convertidora", "Guillotina",
    "Impresión GTOZ", "Impresión Komori", "Barnizado",
    "Plastificado", "Troquelado", "Acabado Manual",
    "Acabado Máquina", "Transporte", "OP Terminados"
]

# --- FUNCIONES AUXILIARES ---

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(username, password):
    if "users" not in st.session_state:
        return False
    hashed = hash_password(password)
    user = st.session_state.users.get(username)
    return user and user["password"] == hashed

def user_role(username):
    return st.session_state.users.get(username, {}).get("role", None)

def can_move_op(user, etapa_op):
    role = user_role(user)
    if role in ["maestro", "planificador"]:
        return True
    elif role == "trabajador":
        return st.session_state.users[user].get("etapa") == etapa_op
    return False

# --- INICIALIZACIÓN DE ESTADO ---
if "users" not in st.session_state:
    st.session_state.users = cargar_usuarios()

    # Usuarios por defecto
    usuarios_por_defecto = {
        "admin": {"password": hash_password("admin123"), "role": "maestro"},
        "planificador": {"password": hash_password("plan123"), "role": "planificador"},
        "trabajador_troquel": {"password": hash_password("troquel123"), "role": "trabajador", "etapa": "Troquelado"},
    }

    # Agrega o actualiza usuarios por defecto si es necesario
    for usuario, data in usuarios_por_defecto.items():
        if usuario not in st.session_state.users:
            guardar_usuario(usuario, data["password"], data["role"], data.get("etapa"))
        else:
            # Verifica si la contraseña almacenada está hasheada
            contrasena_actual = st.session_state.users[usuario]["password"]
            if len(contrasena_actual) != 64:  # No está hasheada
                guardar_usuario(usuario, data["password"], data["role"], data.get("etapa"))

    # Vuelve a cargar usuarios actualizados
    st.session_state.users = cargar_usuarios()

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
            etapa_texto = st.session_state.users[username].get("etapa", "Todas")
            st.success(f"Bienvenido, {username} ({user_role(username)}) - Etapa asignada: {etapa_texto}")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

if not st.session_state.logged_in:
    login()
    st.stop()


# --- PÁGINA PRINCIPAL ---
st.title(f"KANBAN DE PRODUCCIÓN LEAN - Usuario: {st.session_state.username} ({user_role(st.session_state.username)})")


# Mostrar etapa asignada si es trabajador
user_data = st.session_state.users.get(st.session_state.username)
etapa_asignada = user_data.get("etapa", "Todas") if user_data else "Todas"
st.markdown(f"### 🏭 Etapa asignada: **{etapa_asignada}**")

# Mostrar solo las OPs en la etapa del trabajador
if user_role(st.session_state.username) == "trabajador":
    st.markdown("### 📋 Órdenes en tu etapa")
    ops_en_etapa = False
    for op in st.session_state.ops:
        # En tu estructura, la etapa actual está en 'etapas[actual]'
        etapa_actual = op['etapas'][op['actual']]
        if etapa_actual == etapa_asignada:
            ops_en_etapa = True
            st.markdown(f"- OP: **{op['numero_op']}** | Cliente: {op['cliente']} | Etapa: {etapa_actual}")
            if st.button(f"➡️ Mover OP {op['numero_op']}", key=f"mover_{op['numero_op']}"):
                siguiente_index = ETAPAS.index(etapa_actual) + 1
                if siguiente_index < len(ETAPAS):
                    nueva_etapa = ETAPAS[siguiente_index]
                    # Solo mover si la nueva etapa está dentro de las etapas definidas para esa OP
                    if nueva_etapa in op['etapas']:
                        op['actual'] = op['etapas'].index(nueva_etapa)
                        st.success(f"OP {op['numero_op']} movida a etapa: {nueva_etapa}")
                    else:
                        st.warning(f"No puedes mover la OP a la etapa {nueva_etapa} porque no está asignada a esta OP.")
                else:
                    st.warning("Esta OP ya está en la última etapa.")
    if not ops_en_etapa:
        st.info("No hay órdenes asignadas a tu etapa actualmente.")


# Mostrar historial si se presiona el botón
if st.button("Mostrar Historial"):
    historial = obtener_historial()
    df_historial = pd.DataFrame(historial, columns=["Número OP", "Cliente", "Fecha Inicio", "Fecha Fin", "Etapa", "Inicio", "Fin", "Duración (min)"])
    st.dataframe(df_historial)


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

                guardar_usuario(nuevo_usuario, usuario_data["password"], rol_usuario, etapa_trabajador)

                st.success(f"Usuario '{nuevo_usuario}' creado con rol '{rol_usuario}'.")

        st.markdown("### Usuarios actuales")

        # Opcional: Filtros
        filtro_rol = st.selectbox("Filtrar por rol", options=["Todos", "maestro", "planificador", "trabajador"])
        filtro_etapa = st.selectbox("Filtrar por etapa", options=["Todos"] + ETAPAS)

        usuarios_filtrados = []
        for u, data in st.session_state.users.items():
            if filtro_rol != "Todos" and data["role"] != filtro_rol:
                continue
            if filtro_etapa != "Todos" and data.get("etapa") != filtro_etapa:
                continue
            usuarios_filtrados.append((u, data))

        # Mostrar usuarios con botón de eliminar
        for u, data in usuarios_filtrados:
            cols = st.columns([3, 2, 3, 2])
            cols[0].markdown(f"👤 **{u}**")
            cols[1].markdown(f"🔒 {data['role']}")
            cols[2].markdown(f"🏭 {data.get('etapa', '-')}")
            if cols[3].button("🗑️ Eliminar", key=f"del_{u}"):
                del st.session_state.users[u]
                eliminar_usuario(u)
                st.success(f"Usuario '{u}' eliminado.")
                st.rerun()  # refrescar interfaz


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

# --- OPCIÓN DE CERRAR SESIÓN ---
if st.button("Cerrar sesión"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()
