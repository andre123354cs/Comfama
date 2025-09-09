import streamlit as st
import pandas as pd
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client
from datetime import datetime

# --- Configuración de la página y Estilos Futuristas ---
st.set_page_config(layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    body {
        font-family: 'Inter', sans-serif;
        background-color: #0A0A0E;
        color: #E0E0FF;
    }
    .st-emotion-cache-18ni7ap {
        background-color: #0A0A0E !important;
    }
    .st-emotion-cache-1w0l7rx {
        background-color: #0A0A0E !important;
    }
    .st-emotion-cache-16yaizd {
        background-color: #0A0A0E !important;
    }
    .st-emotion-cache-1r4qj8m {
        background-color: #0A0A0E !important;
    }
    .st-emotion-cache-1av54w0 {
        background-color: #0A0A0E !important;
    }
    .st-emotion-cache-1a80y5d {
        background-color: #0A0A0E !important;
    }

    .css-1jc7p55, .css-1dp5vir, .css-1gh1r0 {
        color: #E0E0FF !important;
    }
    
    h1, h2, h3, h4 {
        color: #6A99D9; /* Azul claro más vibrante */
        border-bottom: 2px solid #5A7EAD; /* Borde más claro */
        padding-bottom: 10px;
    }

    .stButton>button {
        background-color: #2E4566; /* Azul oscuro más claro */
        color: #E0E0FF;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s, background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #3B5A80; /* Tono más claro al pasar el mouse */
        transform: translateY(-2px);
    }
    
    .stTextInput>div>div>input, .st-emotion-cache-1v0u6pi {
        background-color: #1A243B; /* Fondo de entrada más claro */
        border: 1px solid #3A4E6B; /* Borde de entrada más claro */
        color: #E0E0FF;
        border-radius: 8px;
        padding: 10px;
    }
    
    .stSelectbox>div>div, .stDateInput>div>div {
        background-color: #1A243B !important;
        border: 1px solid #3A4E6B !important;
        color: #E0E0FF !important;
        border-radius: 8px !important;
    }
    
    .st-emotion-cache-1v0u6pi {
        background-color: #1A243B !important;
        border: 1px solid #3A4E6B !important;
    }

    .st-emotion-cache-1g6x8q2 {
        background-color: #1A243B !important;
    }
    
    .st-emotion-cache-1xw80s2 {
        background-color: #0A0A0E !important;
    }

    .st-emotion-cache-1cpx684 {
        background-color: #1A243B !important;
    }
    
    .st-emotion-cache-1k1qf03 {
        color: #E0E0FF !important;
    }

    .st-emotion-cache-1h61g10 {
        background-color: #0A0A0E !important;
    }

    .st-emotion-cache-s2s9y8 {
        background-color: #0A0A0E !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Funciones de Firestore ---
try:
    firebase_config_str = st.secrets["FIREBASE_CONFIG"]
    firebase_config = json.loads(firebase_config_str)
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except KeyError:
    st.error("Error: FIREBASE_CONFIG not found in secrets. Please configure it in your Streamlit app's secrets.")
    st.stop()
except ValueError:
    st.error("Error: The format of FIREBASE_CONFIG in secrets is not a valid JSON. Please check that the credentials have been copied correctly.")
    st.stop()


def guardar_producto(id_referencia, nombre_referencia):
    """Guarda una nueva referencia de producto en Firestore."""
    doc_ref = db.collection('productos').document(id_referencia)
    doc_ref.set({'nombre': nombre_referencia})

def guardar_movimiento_inventario(id_referencia, cantidad, tipo_movimiento):
    """Guarda un movimiento de inventario (entrada o salida) en Firestore."""
    db.collection('inventario_movimientos').add({
        'id_referencia': id_referencia,
        'cantidad': cantidad,
        'tipo_movimiento': tipo_movimiento,
        'fecha': datetime.now().isoformat()
    })

def guardar_pedido(mesa, encargado, items):
    """Guarda un pedido en Firestore y actualiza el inventario."""
    try:
        doc_ref = db.collection('pedidos').add({
            'mesa': mesa,
            'encargado': encargado,
            'fecha': datetime.now().isoformat(),
            'items': items
        })
        # Actualizar inventario (salida)
        for item in items:
            guardar_movimiento_inventario(item['id_referencia'], item['cantidad'], 'salida')
        st.success("Pedido guardado exitosamente y el inventario ha sido actualizado.")
    except Exception as e:
        st.error(f"Error al guardar el pedido: {e}")

@st.cache_data
def obtener_productos():
    """Obtiene todas las referencias de productos de Firestore."""
    productos = db.collection('productos').stream()
    return {doc.id: doc.to_dict()['nombre'] for doc in productos}

@st.cache_data
def obtener_movimientos_inventario():
    """Obtiene todos los movimientos de inventario de Firestore."""
    movimientos = db.collection('inventario_movimientos').stream()
    return [doc.to_dict() for doc in movimientos]

@st.cache_data
def obtener_pedidos():
    """Obtiene todos los pedidos de Firestore."""
    pedidos = db.collection('pedidos').stream()
    return [doc.to_dict() for doc in pedidos]

def obtener_inventario_actual(productos_map, movimientos_inventario):
    """Calcula el inventario actual a partir de los movimientos."""
    inventario_actual = {id_ref: 0 for id_ref in productos_map.keys()}
    for mov in movimientos_inventario:
        id_ref = mov['id_referencia']
        cantidad = mov['cantidad']
        if mov['tipo_movimiento'] == 'entrada':
            inventario_actual[id_ref] += cantidad
        elif mov['tipo_movimiento'] == 'salida':
            inventario_actual[id_ref] -= cantidad
    
    df_inventario = pd.DataFrame(list(inventario_actual.items()), columns=['ID Referencia', 'Cantidad'])
    df_inventario['Nombre Referencia'] = df_inventario['ID Referencia'].map(productos_map)
    return df_inventario[['Nombre Referencia', 'ID Referencia', 'Cantidad']]

def pagina_inventario():
    st.header('📦 Gestión de Inventario')
    st.write('Agrega nuevas referencias de productos o registra movimientos de stock.')

    productos_map = obtener_productos()
    
    # --- Agregar nueva referencia de producto ---
    st.markdown("---")
    st.subheader('➕ Agregar Nueva Referencia')
    with st.form(key='add_product_form'):
        col1, col2 = st.columns(2)
        with col1:
            nombre_referencia = st.text_input("Nombre de la Referencia (ej. 'Aguila')").strip()
        with col2:
            id_referencia = st.text_input("ID de Referencia (ej. 'aguila001')").strip()
        
        submit_product = st.form_submit_button('Guardar Referencia')
    
    if submit_product:
        if nombre_referencia and id_referencia:
            guardar_producto(id_referencia, nombre_referencia)
            st.cache_data.clear()
            st.experimental_rerun()
        else:
            st.error("Por favor, llena ambos campos.")

    # --- Registrar movimiento de inventario ---
    st.markdown("---")
    st.subheader('✍️ Registrar Movimiento de Inventario')
    
    if not productos_map:
        st.warning("No hay referencias de productos. Por favor, agrega una primero.")
    else:
        with st.form(key='stock_movement_form'):
            producto_movimiento = st.selectbox("Selecciona la Referencia", options=sorted(productos_map.keys()), format_func=lambda x: f"{productos_map[x]} ({x})")
            
            col_mov1, col_mov2 = st.columns(2)
            with col_mov1:
                cantidad_movimiento = st.number_input("Cantidad", min_value=1, value=1)
            with col_mov2:
                tipo_movimiento = st.selectbox("Tipo de Movimiento", options=['entrada', 'salida'])
            
            submit_movement = st.form_submit_button('Registrar Movimiento')
            
        if submit_movement:
            guardar_movimiento_inventario(producto_movimiento, cantidad_movimiento, tipo_movimiento)
            st.cache_data.clear()
            st.experimental_rerun()

    # --- Ver Inventario actual ---
    st.markdown("---")
    st.subheader('📊 Inventario Actual')
    movimientos_inventario = obtener_movimientos_inventario()
    if movimientos_inventario:
        df_inventario = obtener_inventario_actual(productos_map, movimientos_inventario)
        st.dataframe(df_inventario, use_container_width=True)
    else:
        st.info("Aún no hay movimientos de inventario.")


def pagina_despacho():
    st.header('🧾 Despacho de Pedidos')
    st.write('Registra las ventas y el consumo de productos por mesa.')
    
    productos_map = obtener_productos()
    
    if not productos_map:
        st.warning("No hay referencias de productos. Por favor, agrega algunas en el módulo de Inventario.")
        return

    # --- Formulario de pedido ---
    st.markdown("---")
    st.subheader('📝 Registrar Nuevo Pedido')
    with st.form(key='order_form'):
        col1, col2 = st.columns(2)
        with col1:
            mesa = st.text_input("Número o Nombre de la Mesa (ej. 'Mesa 5', 'Terraza')")
        with col2:
            encargado = st.text_input("Nombre del Encargado")

        st.markdown("#### Artículos del Pedido")
        articulos_pedido = {}
        for id_ref, nombre_ref in productos_map.items():
            cantidad = st.number_input(f"{nombre_ref}", min_value=0, value=0, key=f"item_{id_ref}")
            if cantidad > 0:
                articulos_pedido[id_ref] = cantidad

        submit_order = st.form_submit_button('Guardar Pedido')
    
    if submit_order:
        if not mesa or not encargado or not articulos_pedido:
            st.error("Por favor, completa la mesa, el encargado y agrega al menos un artículo.")
        else:
            items_list = [{'id_referencia': id_ref, 'cantidad': cantidad} for id_ref, cantidad in articulos_pedido.items()]
            guardar_pedido(mesa, encargado, items_list)
            st.cache_data.clear()
            st.experimental_rerun()

    # --- Historial de pedidos ---
    st.markdown("---")
    st.subheader('📄 Historial de Pedidos')
    pedidos = obtener_pedidos()
    if pedidos:
        df_pedidos = pd.DataFrame(pedidos)
        df_pedidos['fecha'] = pd.to_datetime(df_pedidos['fecha']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # Procesar los items para una mejor visualización
        def format_items(items_list):
            if not isinstance(items_list, list):
                return ""
            return ", ".join([f"{productos_map.get(item['id_referencia'], item['id_referencia'])} x{item['cantidad']}" for item in items_list])

        df_pedidos['Productos'] = df_pedidos['items'].apply(format_items)
        df_display = df_pedidos[['fecha', 'mesa', 'encargado', 'Productos']]

        opcion_agrupar = st.selectbox(
            "Agrupar por:",
            options=['No agrupar', 'Mesa', 'Encargado']
        )
        
        if opcion_agrupar == 'Mesa':
            st.dataframe(df_display.sort_values(by='mesa'), use_container_width=True)
        elif opcion_agrupar == 'Encargado':
            st.dataframe(df_display.sort_values(by='encargado'), use_container_width=True)
        else:
            st.dataframe(df_display.sort_values(by='fecha', ascending=False), use_container_width=True)
    else:
        st.info("Aún no hay pedidos registrados.")

def main():
    st.title('🍻 Sistema de Gestión para Bar')
    st.sidebar.title('Menú')
    opcion = st.sidebar.radio('Navegación', ['Gestión de Inventario', 'Despacho de Pedidos'])
    
    if opcion == 'Gestión de Inventario':
        pagina_inventario()
    elif opcion == 'Despacho de Pedidos':
        pagina_despacho()

if __name__ == '__main__':
    main()
