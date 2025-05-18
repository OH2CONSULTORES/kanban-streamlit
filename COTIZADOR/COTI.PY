import streamlit as st
import json
import os
from datetime import datetime
from fpdf import FPDF

# Archivo para guardar configuración y cotizaciones
CONFIG_FILE = "config.json"
COTIZACIONES_FILE = "cotizaciones.json"

# Lista inicial de servicios con costo por hora
SERVICIOS_INICIALES = {
    "Estrategias de Suministro y Calidad": 150,
    "Gestión de la cadena de suministro": 140,
    "Gestión de la calidad total": 130,
    "Mejora de procesos y Proyectos": 160,
    "Optimización de procesos": 150,
    "Gestión de almacén": 120,
    "Gestión de proyectos": 170,
    "Innovación Digital y Social": 180,
    "Gestión de redes sociales": 110,
    "Gestión organizacional": 140,
    "Gestión del talento humano": 150,
    "Transformación digital": 200,
}

IGV = 0.18  # 18%

# --- FUNCIONES ---

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        # Crear config inicial
        config = {
            "servicios": SERVICIOS_INICIALES,
            "terminos": "Condiciones y cláusulas estándar:\n- Pago a 30 días\n- Validez de cotización 15 días\n- Transporte y comida incluidos según distancia",
            "costos_traslado_por_km": 2.0,
            "costos_comida_por_dia": 15.0
        }
        guardar_config(config)
        return config

def guardar_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def cargar_cotizaciones():
    if os.path.exists(COTIZACIONES_FILE):
        with open(COTIZACIONES_FILE, "r") as f:
            return json.load(f)
    else:
        return []

def guardar_cotizaciones(cotizaciones):
    with open(COTIZACIONES_FILE, "w") as f:
        json.dump(cotizaciones, f, indent=4)

def crear_pdf(cotizacion):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Cotización de Servicios de Consultoría", 0, 1, "C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Cliente: {cotizacion['cliente']['nombre']}", 0, 1)
    pdf.cell(0, 10, f"Fecha: {cotizacion['fecha']}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Servicios Cotizados:", 0, 1)
    
    pdf.set_font("Arial", "", 12)
    for s in cotizacion['servicios']:
        pdf.cell(0, 10, f"- {s['nombre']} ({s['horas']} hrs) - S/ {s['costo']:.2f}", 0, 1)
    pdf.ln(5)
    
    pdf.cell(0, 10, f"Costo transporte (S/): {cotizacion['costos']['transporte']:.2f}", 0, 1)
    pdf.cell(0, 10, f"Costo comida (S/): {cotizacion['costos']['comida']:.2f}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Subtotal: S/ {cotizacion['totales']['subtotal']:.2f}", 0, 1)
    pdf.cell(0, 10, f"IGV (18%): S/ {cotizacion['totales']['igv']:.2f}", 0, 1)
    pdf.cell(0, 10, f"Total: S/ {cotizacion['totales']['total']:.2f}", 0, 1)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Términos y Condiciones:", 0, 1)
    pdf.set_font("Arial", "", 10)
    for line in cotizacion['terminos'].split("\n"):
        pdf.multi_cell(0, 8, line)
    
    filename = f"cotizacion_{cotizacion['cliente']['nombre'].replace(' ','_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

def login_page():
    st.title("Login")
    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if user == "admin" and pwd == "1234":
            st.session_state["logged_in"] = True
            st.success("Login correcto")
        else:
            st.error("Usuario o contraseña incorrectos")

def configuracion_page(config):
    st.header("Configuración de Servicios y Costos")
    
    # Mostrar servicios existentes
    servicios = config["servicios"]
    st.subheader("Servicios y costos por hora (S/)")
    servicios_nuevos = {}
    for nombre, costo in servicios.items():
        costo_nuevo = st.number_input(f"{nombre}", min_value=0.0, value=float(costo), step=1.0, format="%.2f", key=f"serv_{nombre}")
        servicios_nuevos[nombre] = costo_nuevo
    
    # Agregar servicio nuevo
    st.subheader("Agregar nuevo servicio")
    nuevo_servicio = st.text_input("Nombre del servicio nuevo")
    nuevo_costo = st.number_input("Costo por hora (S/)", min_value=0.0, value=100.0, step=1.0)
    if st.button("Agregar servicio"):
        if nuevo_servicio.strip() != "":
            if nuevo_servicio in servicios_nuevos:
                st.warning("El servicio ya existe")
            else:
                servicios_nuevos[nuevo_servicio.strip()] = nuevo_costo
                st.success(f"Servicio '{nuevo_servicio}' agregado")
        else:
            st.warning("Ingrese un nombre válido")
    
    # Editar costos adicionales y términos
    st.subheader("Costos adicionales")
    traslado_km = st.number_input("Costo por km de traslado (S/)", min_value=0.0, value=config.get("costos_traslado_por_km", 2.0), step=0.1)
    costo_comida = st.number_input("Costo por día de comida (S/)", min_value=0.0, value=config.get("costos_comida_por_dia", 15.0), step=0.5)
    
    st.subheader("Términos y condiciones")
    terminos = st.text_area("Ingrese términos y condiciones", value=config.get("terminos", ""), height=150)
    
    if st.button("Guardar configuración"):
        config["servicios"] = servicios_nuevos
        config["costos_traslado_por_km"] = traslado_km
        config["costos_comida_por_dia"] = costo_comida
        config["terminos"] = terminos
        guardar_config(config)
        st.success("Configuración guardada")

def cotizar_page(config, cotizaciones):
    st.header("Cotización de Servicios")
    
    # Datos cliente
    st.subheader("Datos del cliente")
    nombre_cliente = st.text_input("Nombre completo")
    empresa = st.text_input("Empresa")
    email = st.text_input("Correo electrónico")
    telefono = st.text_input("Teléfono")
    
    # Servicios
    st.subheader("Servicios a cotizar")
    servicios = config["servicios"]
    servicios_seleccionados = st.multiselect("Seleccione servicios", list(servicios.keys()))
    
    servicios_detalle = []
    total_horas = 0.0
    costo_servicios = 0.0
    
    for s in servicios_seleccionados:
        horas = st.number_input(f"Horas para '{s}'", min_value=0.0, value=1.0, step=0.5, key=f"horas_{s}")
        costo_hora = servicios[s]
        costo = costo_hora * horas
        servicios_detalle.append({"nombre": s, "horas": horas, "costo": costo})
        total_horas += horas
        costo_servicios += costo
    
    # Costos adicionales
    st.subheader("Costos adicionales")
    distancia_km = st.number_input("Distancia estimada (km)", min_value=0.0, value=10.0)
    dias_comida = st.number_input("Días con alimentación requerida", min_value=0, value=1, step=1)
    
    costo_traslado = distancia_km * config.get("costos_traslado_por_km", 2.0)
    costo_comida = dias_comida * config.get("costos_comida_por_dia", 15.0)
    
    st.write(f"Costo traslado: S/ {costo_traslado:.2f}")
    st.write(f"Costo comida: S/ {costo_comida:.2f}")
    
    subtotal = costo_servicios + costo_traslado + costo_comida
    igv_valor = subtotal * IGV
    total = subtotal + igv_valor
    
    st.subheader("Totales")
    st.write(f"Subtotal: S/ {subtotal:.2f}")
    st.write(f"IGV (18%): S/ {igv_valor:.2f}")
    st.write(f"Total: S/ {total:.2f}")
    
    # Estado cotización
    estado = st.selectbox("Estado de la cotización", ["Pendiente", "Aceptada", "Rechazada"])
    
    if st.button("Generar PDF y Guardar cotización"):
        if not nombre_cliente.strip():
            st.warning("Ingrese el nombre del cliente")
            return
        cotizacion = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cliente": {
                "nombre": nombre_cliente,
                "empresa": empresa,
                "email": email,
                "telefono": telefono
            },
            "servicios": servicios_detalle,
            "costos": {
                "transporte": costo_traslado,
                "comida": costo_comida
            },
            "totales": {
                "subtotal": subtotal,
                "igv": igv_valor,
                "total": total
            },
            "terminos": config.get("terminos", ""),
            "estado": estado
        }
        filename = crear_pdf(cotizacion)
        cotizaciones.append(cotizacion)
        guardar_cotizaciones(cotizaciones)
        st.success(f"Cotización guardada y PDF generado: {filename}")
        with open(filename, "rb") as f:
            st.download_button("Descargar PDF", f, file_name=filename)
        
        # Mostrar link para WhatsApp (solo mensaje, usuario debe adjuntar PDF manualmente)
        texto_ws = f"Hola {nombre_cliente}, adjunto la cotización de servicios. Total: S/ {total:.2f}. Por favor revisar el PDF."
        link_ws = f"https://api.whatsapp.com/send?phone=&text={texto_ws.replace(' ','%20')}"
        st.markdown(f"[Enviar por WhatsApp]({link_ws})")

def historial_page(cotizaciones):
    st.header("Historial de Cotizaciones")
    if len(cotizaciones) == 0:
        st.info("No hay cotizaciones guardadas.")
        return
    
    estados = list(set(c["estado"] for c in cotizaciones))
    filtro_estado = st.selectbox("Filtrar por estado", ["Todos"] + estados)
    
    # Filtrar cotizaciones
    if filtro_estado != "Todos":
        filtradas = [c for c in cotizaciones if c["estado"] == filtro_estado]
    else:
        filtradas = cotizaciones
    
    # Mostrar tabla básica
    import pandas as pd
    data = []
    for c in filtradas:
        data.append({
            "Fecha": c["fecha"],
            "Cliente": c["cliente"]["nombre"],
            "Empresa": c["cliente"]["empresa"],
            "Total (S/)": c["totales"]["total"],
            "Estado": c["estado"]
        })
    df = pd.DataFrame(data)
    st.dataframe(df)

# --- MAIN ---

def main():
    st.set_page_config(page_title="Cotizador de Consultoría", layout="wide")
    
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if not st.session_state["logged_in"]:
        login_page()
        return
    
    config = cargar_config()
    cotizaciones = cargar_cotizaciones()
    
    st.sidebar.title("Menú")
    pagina = st.sidebar.radio("Navegación", ["Cotizar", "Configuración", "Historial", "Cerrar sesión"])
    
    if pagina == "Cerrar sesión":
        st.session_state["logged_in"] = False
        st.experimental_rerun()
    
    elif pagina == "Configuración":
        configuracion_page(config)
    elif pagina == "Cotizar":
        cotizar_page(config, cotizaciones)
    elif pagina == "Historial":
        historial_page(cotizaciones)

if __name__ == "__main__":
    main()
