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


def guardar_producto(id_referencia, nombre_referencia, precio):
    """Guarda una nueva referencia de producto en Firestore."""
    doc_ref = db.collection('productos').document(id_referencia)
    doc_ref.set({'nombre': nombre_referencia, 'precio': precio})

def actualizar_producto(id_referencia, nombre_referencia, precio):
    """Actualiza una referencia de producto existente en Firestore."""
    doc_ref = db.collection('productos').document(id_referencia)
    doc_ref.update({'nombre': nombre_referencia, 'precio': precio})

def guardar_movimiento_inventario(id_referencia, cantidad, tipo_movimiento):
    """Guarda un movimiento de inventario (entrada o salida) en Firestore."""
    db.collection('inventario_movimientos').add({
        'id_referencia': id_referencia,
        'cantidad': cantidad,
        'tipo_movimiento': tipo_movimiento,
        'fecha': datetime.now().isoformat()
    })

def guardar_pedido(mesa, encargado, items, valor_total):
    """Guarda un pedido en Firestore y actualiza el inventario."""
    try:
        doc_ref = db.collection('pedidos').add({
            'mesa': mesa,
            'encargado': encargado,
            'fecha': datetime.now().isoformat(),
            'items': items,
            'valor_total': valor_total,
            'estado': 'pendiente'  # Nuevo campo de estado
        })
        # Actualizar inventario (salida)
        for item in items:
            guardar_movimiento_inventario(item['id_referencia'], item['cantidad'], 'salida')
        st.success("Pedido guardado exitosamente y el inventario ha sido actualizado.")
    except Exception as e:
        st.error(f"Error al guardar el pedido: {e}")

def marcar_pedidos_pagados(pedido_ids):
    """Actualiza el estado de varios pedidos a 'pagado'."""
    batch = db.batch()
    for pedido_id in pedido_ids:
        doc_ref = db.collection('pedidos').document(pedido_id)
        batch.update(doc_ref, {'estado': 'pagado'})
    batch.commit()

@st.cache_data
def obtener_productos():
    """Obtiene todas las referencias de productos de Firestore."""
    productos = db.collection('productos').stream()
    productos_map = {}
    for doc in productos:
        data = doc.to_dict()
        precio = data.get('precio', 0)
        # Asegurarse de que el precio es un número antes de almacenarlo
        if isinstance(precio, (int, float)):
            data['precio'] = float(precio)
        else:
            data['precio'] = 0.0 # Valor por defecto si no es numérico
        productos_map[doc.id] = data
    return productos_map

@st.cache_data
def obtener_movimientos_inventario():
    """Obtiene todos los movimientos de inventario de Firestore."""
    movimientos = db.collection('inventario_movimientos').stream()
    return [doc.to_dict() for doc in movimientos]

@st.cache_data
def obtener_pedidos():
    """Obtiene todos los pedidos de Firestore."""
    pedidos_data = []
    pedidos_stream = db.collection('pedidos').stream()
    for doc in pedidos_stream:
        doc_dict = doc.to_dict()
        doc_dict['id'] = doc.id
        doc_dict['valor_total'] = doc_dict.get('valor_total', 0)  # Manejar el caso de 'valor_total' ausente
        doc_dict['estado'] = doc_dict.get('estado', 'pendiente')  # Manejar el caso de 'estado' ausente
        pedidos_data.append(doc_dict)
    return pedidos_data

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
    df_inventario['Nombre Referencia'] = df_inventario['ID Referencia'].map({k: v['nombre'] for k, v in productos_map.items()})
    df_inventario['Precio Unitario'] = df_inventario['ID Referencia'].map({k: v['precio'] for k, v in productos_map.items()})
    return df_inventario[['Nombre Referencia', 'ID Referencia', 'Cantidad', 'Precio Unitario']]

def pagina_inventario():
    st.header('📦 Gestión de Inventario')
    st.write('Agrega nuevas referencias de productos o registra movimientos de stock.')

    productos_map = obtener_productos()
    
    # --- Agregar nueva referencia de producto ---
    st.markdown("---")
    st.subheader('➕ Agregar Nueva Referencia')
    with st.form(key='add_product_form'):
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre_referencia = st.text_input("Nombre de la Referencia (ej. 'Aguila')").strip()
        with col2:
            id_referencia = st.text_input("ID de Referencia (ej. 'aguila001')").strip()
        with col3:
            precio = st.number_input("Precio por Unidad", min_value=0.0, step=0.01)
        
        submit_product = st.form_submit_button('Guardar Referencia')
    
    if submit_product:
        if nombre_referencia and id_referencia and precio > 0:
            guardar_producto(id_referencia, nombre_referencia, precio)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Por favor, llena todos los campos y asegúrate de que el precio sea mayor que 0.")

    # --- Editar referencia existente ---
    st.markdown("---")
    st.subheader('✏️ Editar Referencia Existente')
    if not productos_map:
        st.info("No hay referencias para editar.")
    else:
        with st.form(key='edit_product_form'):
            producto_a_editar = st.selectbox(
                "Selecciona la Referencia a editar",
                options=sorted(productos_map.keys()),
                format_func=lambda x: f"{productos_map[x]['nombre']} ({x})"
            )
            
            nombre_actual = productos_map[producto_a_editar]['nombre']
            # Asegurarse de que el precio es un float antes de usarlo
            precio_actual = float(productos_map[producto_a_editar]['precio'])

            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                nuevo_nombre = st.text_input("Nuevo Nombre de Referencia", value=nombre_actual).strip()
            with col_edit2:
                nuevo_precio = st.number_input("Nuevo Precio por Unidad", min_value=0.0, step=0.01, value=precio_actual)
            
            submit_edit = st.form_submit_button('Guardar Cambios')

        if submit_edit:
            if nuevo_nombre and nuevo_precio > 0:
                actualizar_producto(producto_a_editar, nuevo_nombre, nuevo_precio)
                st.success(f"Referencia '{nuevo_nombre}' actualizada exitosamente.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Por favor, llena todos los campos y asegúrate de que el precio sea mayor que 0.")


    # --- Registrar movimiento de inventario ---
    st.markdown("---")
    st.subheader('✍️ Registrar Movimiento de Inventario')
    
    if not productos_map:
        st.warning("No hay referencias de productos. Por favor, agrega una primero.")
    else:
        with st.form(key='stock_movement_form'):
            producto_movimiento = st.selectbox("Selecciona la Referencia", options=sorted(productos_map.keys()), format_func=lambda x: f"{productos_map[x]['nombre']} ({x})")
            
            col_mov1, col_mov2 = st.columns(2)
            with col_mov1:
                cantidad_movimiento = st.number_input("Cantidad", min_value=1, value=1)
            with col_mov2:
                tipo_movimiento = st.selectbox("Tipo de Movimiento", options=['entrada', 'salida'])
            
            submit_movement = st.form_submit_button('Registrar Movimiento')
            
        if submit_movement:
            guardar_movimiento_inventario(producto_movimiento, cantidad_movimiento, tipo_movimiento)
            st.cache_data.clear()
            st.rerun()

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
            # Dropdown con mesas predefinidas y opción opcional
            mesa_opciones = [str(i) for i in range(1, 9)]
            mesa_seleccionada = st.selectbox(
                "Número de Mesa (Selecciona de la lista)",
                options=mesa_opciones,
                index=0
            )
            mesa_personalizada = st.text_input("O agregar una mesa personalizada (ej. 'Barra')").strip()
            
            # Usar la mesa personalizada si se ha escrito, de lo contrario, usar la seleccionada
            mesa = mesa_personalizada if mesa_personalizada else mesa_seleccionada
        
        with col2:
            encargado = st.text_input("Nombre del Encargado")

        st.markdown("#### Artículos del Pedido")
        articulos_pedido = {}
        total_pedido = 0.0
        
        for id_ref, data in productos_map.items():
            cantidad = st.number_input(f"{data['nombre']} (Precio: ${data['precio']:,.2f})", min_value=0, value=0, key=f"item_{id_ref}")
            if cantidad > 0:
                articulos_pedido[id_ref] = {'cantidad': cantidad, 'precio_unitario': data['precio']}
                total_pedido += cantidad * data['precio']

        st.markdown(f"**Valor Total del Pedido:** **${total_pedido:,.2f}**")
        
        submit_order = st.form_submit_button('Guardar Pedido')
    
    if submit_order:
        if not mesa or not encargado or not articulos_pedido:
            st.error("Por favor, completa la mesa, el encargado y agrega al menos un artículo.")
        else:
            items_list = [{'id_referencia': id_ref, 'cantidad': data['cantidad']} for id_ref, data in articulos_pedido.items()]
            guardar_pedido(mesa, encargado, items_list, total_pedido)
            st.cache_data.clear()
            st.rerun()

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
            return ", ".join([f"{productos_map.get(item['id_referencia'], {'nombre': item['id_referencia']})['nombre']} x{item['cantidad']}" for item in items_list])

        df_pedidos['Productos'] = df_pedidos['items'].apply(format_items)
        df_display = df_pedidos[['fecha', 'mesa', 'encargado', 'Productos', 'valor_total']]
        df_display = df_display.rename(columns={'valor_total': 'Valor Total'})
        df_display['Valor Total'] = df_display['Valor Total'].apply(lambda x: f"${x:,.2f}")

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

def pagina_facturacion():
    st.header('🧾 Facturación y Cuentas')
    st.write('Gestiona los cobros, consolida facturas y marca pedidos como pagados.')

    productos_map = obtener_productos()
    pedidos = obtener_pedidos()
    
    if not pedidos:
        st.info("No hay pedidos registrados para facturar.")
        return

    df_pedidos = pd.DataFrame(pedidos)
    df_pendientes = df_pedidos[df_pedidos['estado'] == 'pendiente'].copy()

    if df_pendientes.empty:
        st.success("🎉 Todas las cuentas están al día. ¡No hay pedidos pendientes!")
        return
        
    # Procesar los items para una mejor visualización
    def format_items(items_list):
        if not isinstance(items_list, list):
            return ""
        return ", ".join([f"{productos_map.get(item['id_referencia'], {'nombre': item['id_referencia']})['nombre']} x{item['cantidad']}" for item in items_list])

    df_pendientes['Productos'] = df_pendientes['items'].apply(format_items)
    
    opcion_agrupar = st.selectbox(
        "Agrupar y seleccionar cuentas por:",
        options=['Mesa', 'Encargado']
    )

    if opcion_agrupar == 'Mesa':
        opciones_seleccion = sorted(df_pendientes['mesa'].unique())
        seleccionados = st.multiselect("Selecciona las mesas a facturar:", options=opciones_seleccion)
        pedidos_seleccionados = df_pendientes[df_pendientes['mesa'].isin(seleccionados)]
    else: # Por Encargado
        opciones_seleccion = sorted(df_pendientes['encargado'].unique())
        seleccionados = st.multiselect("Selecciona los encargados a facturar:", options=opciones_seleccion)
        pedidos_seleccionados = df_pendientes[df_pendientes['encargado'].isin(seleccionados)]

    st.markdown("---")
    st.subheader('Factura Consolidada')

    if not pedidos_seleccionados.empty:
        total_factura = pedidos_seleccionados['valor_total'].sum()
        
        st.markdown(f"### Valor Total a Cobrar: **${total_factura:,.2f}**")

        st.write("#### Detalles del pedido")
        df_detalles = pedidos_seleccionados[['fecha', 'mesa', 'encargado', 'Productos', 'valor_total']]
        df_detalles = df_detalles.rename(columns={'valor_total': 'Valor Total'})
        df_detalles['Valor Total'] = df_detalles['Valor Total'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df_detalles, use_container_width=True)

        if st.button('💰 Marcar Cuentas como Pagadas'):
            pedido_ids_a_pagar = pedidos_seleccionados['id'].tolist()
            marcar_pedidos_pagados(pedido_ids_a_pagar)
            st.success("Las cuentas han sido marcadas como pagadas.")
            st.cache_data.clear()
            st.rerun()

    else:
        st.info("Selecciona una o más opciones para generar la factura.")

def main():
    st.title('🍻 Sistema de Gestión para Bar')
    st.sidebar.title('Menú')
    opcion = st.sidebar.radio('Navegación', ['Gestión de Inventario', 'Despacho de Pedidos', 'Facturación y Cuentas'])
    
    if opcion == 'Gestión de Inventario':
        pagina_inventario()
    elif opcion == 'Despacho de Pedidos':
        pagina_despacho()
    elif opcion == 'Facturación y Cuentas':
        pagina_facturacion()

if __name__ == '__main__':
    main()
