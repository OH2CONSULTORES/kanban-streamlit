from datetime import datetime
# Funciones de BD
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
        user_dict[u] = {"password": p, "role": r}
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

    # Si la tabla está vacía, se insertan los usuarios por defecto
    if not st.session_state.users:
        usuarios_por_defecto = {
            "admin": {"password": hash_password("admin123"), "role": "maestro"},
            "planificador": {"password": hash_password("plan123"), "role": "planificador"},
            "trabajador_troquel": {"password": hash_password("troquel123"), "role": "trabajador", "etapa": "Troquelado"},
        }

        for usuario, data in usuarios_por_defecto.items():
            guardar_usuario(usuario, data["password"], data["role"], data.get("etapa"))

        # Vuelve a cargar los usuarios desde la BD actualizada
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
            st.success(f"Bienvenido, {username} ({user_role(username)})")
            st.experimental_rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

if not st.session_state.logged_in:
    login()
    st.stop()



# --- PÁGINA PRINCIPAL ---
st.title(f"KANBAN DE PRODUCCIÓN LEAN - Usuario: {st.session_state.username} ({user_role(st.session_state.username)})")

# Mostrar historial si se presiona el botón
if st.button("Mostrar Historial"):
    historial = obtener_historial()
    df_historial = pd.DataFrame(historial, columns=["Número OP", "Cliente", "Fecha Inicio", "Fecha Fin", "Etapa", "Inicio", "Fin", "Duración (min)"])
    st.dataframe(df_historial)

# Aquí continúa el código original para gestión de usuarios, agregar OPs, mostrar tablero Kanban, mover OPs, etc.
# (omitido por brevedad pero sin modificar esa lógica)



# --- ADMINISTRACIÓN DE USUARIOS (solo maestro) ---
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
                st.experimental_rerun()  # refrescar interfaz


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
            if entrada and salida:
                duracion_min = (salida - entrada).total_seconds() / 60
                df_rows.append({
                    "Número OP": op["numero_op"],
                    "Cliente": op["cliente"],
                    "Etapa": etapa,
                    "Entrada": entrada.strftime('%Y-%m-%d %H:%M:%S'),
                    "Salida": salida.strftime('%Y-%m-%d %H:%M:%S'),
                    "Duración (min)": round(duracion_min, 2)
                })

                # Insertar en base de datos
                insertar_historial(
                    numero_ome=op["numero_op"],
                    cliente=op["cliente"],
                    f_ini=min(t[0] for t in op["tiempos"].values() if t[0]).strftime('%Y-%m-%d'),
                    f_fin=max(t[1] for t in op["tiempos"].values() if t[1]).strftime('%Y-%m-%d'),
                    etapa=etapa,
                    t_ini=entrada.strftime('%H:%M:%S'),
                    t_fin=salida.strftime('%H:%M:%S'),
                    duracion=round(duracion_min, 2)
                )

    df = pd.DataFrame(df_rows)
    df.to_excel(output, index=False)
    return output

  # Tu función de base de datos

if st.button("📥 Exportar historial de OPs a Excel"):
    if st.session_state.ops:
        excel_file = exportar_excel(st.session_state.ops)
        st.download_button(
            label="Descargar Excel",
            data=excel_file,
            file_name="historial_ops.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No hay OPs para exportar.")


# --- HISTORIAL Y ANÁLISIS ---
st.subheader("📜 Historial de Producción")
if st.button("📜 Mostrar Historial desde la BD"):
    registros = obtener_historial()
    if registros:
        df_historial = pd.DataFrame(registros, columns=["N° OP", "Cliente", "Fecha Inicio", "Fecha Fin", "Etapa", "Hora Inicio", "Hora Fin", "Duración (min)"])
        st.dataframe(df_historial)
    else:
        st.info("No hay registros en el historial.")


# Filtros
col1, col2, col3 = st.columns(3)
with col1:
    fecha_inicio = st.date_input("📅 Fecha de inicio", value=datetime.today())
with col2:
    fecha_fin = st.date_input("📅 Fecha de fin", value=datetime.today())
with col3:
    tiempo_ideal_min = st.number_input("⏱️ Tiempo ideal por OP (min)", min_value=1, value=60)

# Botón para mostrar historial
if st.button("Mostrar Historial eneral"):

    if user_role(st.session_state.username) in ["maestro", "planificador"]:
        historial_bruto = obtener_historial()

        historial = []
        for numero_ome, cliente, f_ini, f_fin, etapa, t_ini, t_fin, duracion in historial_bruto:
            entrada = datetime.fromisoformat(t_ini)
            salida = datetime.fromisoformat(t_fin)
            dur_min = round(duracion / 60, 2)

            if fecha_inicio <= entrada.date() <= fecha_fin:
                historial.append({
                    "Número OP": numero_ome,
                    "Cliente": cliente,
                    "Etapa": etapa,
                    "Entrada": entrada,
                    "Salida": salida,
                    "Duración (min)": dur_min
                })

        if not historial:
            st.warning("⚠️ No hay datos para el rango seleccionado.")
        else:
            df = pd.DataFrame(historial)

            # Crear columnas dinámicas por etapa
            etapas = df["Etapa"].unique()
            registros = []

            for (numero_op, cliente), group in df.groupby(["Número OP", "Cliente"]):
                registro = {"Número OP": numero_op, "Cliente": cliente}
                for _, fila in group.iterrows():
                    etapa = fila["Etapa"]
                    registro[f"{etapa} Entrada"] = fila["Entrada"].strftime("%Y-%m-%d %H:%M:%S")
                    registro[f"{etapa} Salida"] = fila["Salida"].strftime("%Y-%m-%d %H:%M:%S")
                    registro[f"{etapa} Duración"] = str(timedelta(minutes=fila["Duración (min)"]))
                registros.append(registro)

            df_final = pd.DataFrame(registros)

            # Calcular Total y Eficiencia
            def calcular_total_min(row):
                total = 0
                for etapa in etapas:
                    valor = row.get(f"{etapa} Duración", None)
                    if valor:
                        partes = valor.split(':')
                        minutos = int(partes[0]) * 60 + int(partes[1]) + int(partes[2]) / 60
                        total += minutos
                return total

            df_final["Total (min)"] = df_final.apply(calcular_total_min, axis=1)
            df_final["Total HH:MM:SS"] = df_final["Total (min)"].apply(lambda x: str(timedelta(minutes=x)))
            tiempo_ideal_seg = tiempo_ideal_min * 60
            df_final["Eficiencia (%)"] = round((tiempo_ideal_seg / (df_final["Total (min)"] * 60)) * 100, 1)

            # Mostrar tabla
            st.dataframe(df_final, use_container_width=True)

            # Exportar a Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Historial')
            st.download_button(
                label="📥 Descargar Historial en Excel",
                data=output.getvalue(),
                file_name="historial_produccion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    else:
        st.info("🔒 No tienes permiso para ver el historial completo.")
else:
    st.info("Haz clic en 'Mostrar Historial' para ver los datos.")


# --- OPCIÓN DE CERRAR SESIÓN ---
if st.button("Cerrar sesión"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.experimental_rerun()
