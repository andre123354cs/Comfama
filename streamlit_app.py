import streamlit as st
import pandas as pd
import requests
import io
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client
from requests.exceptions import RequestException
from datetime import date

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
        color: #8C8CFF;
        border-bottom: 2px solid #5A5A99;
        padding-bottom: 10px;
    }

    .stButton>button {
        background-color: #2E2E66;
        color: #E0E0FF;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s, background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #444488;
        transform: translateY(-2px);
    }
    
    .stTextInput>div>div>input, .st-emotion-cache-1v0u6pi {
        background-color: #1A1A2E;
        border: 1px solid #3A3A5A;
        color: #E0E0FF;
        border-radius: 8px;
        padding: 10px;
    }
    
    .stSelectbox>div>div, .stDateInput>div>div {
        background-color: #1A1A2E !important;
        border: 1px solid #3A3A5A !important;
        color: #E0E0FF !important;
        border-radius: 8px !important;
    }
    
    .st-emotion-cache-1v0u6pi {
        background-color: #1A1A2E !important;
        border: 1px solid #3A3A5A !important;
    }

    .st-emotion-cache-1g6x8q2 {
        background-color: #1A1A2E !important;
    }
    
    .st-emotion-cache-1xw80s2 {
        background-color: #0A0A0E !important;
    }

    .st-emotion-cache-1cpx684 {
        background-color: #1A1A2E !important;
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


# Initialize Firebase
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
    st.error("Error: El formato de FIREBASE_CONFIG en secrets no es un JSON válido. Revisa que las credenciales estén copiadas correctamente.")
    st.stop()


# URL del archivo Excel para descargar la lista de estudiantes
EXCEL_URL = 'https://powerbi.yesbpo.com/public.php/dav/files/m5ytip22YkX5SKt/'

@st.cache_data(show_spinner=False)
def obtener_estudiantes_de_excel():
    """
    Descarga el archivo Excel de la URL y
    lee la hoja 'Lista' para obtener los nombres completos.
    """
    try:
        response = requests.get(EXCEL_URL)
        response.raise_for_status() 
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='Lista')
        
        if 'Nombre' in df.columns and 'Apellido' in df.columns:
            df['Nombre Completo'] = df['Nombre'].fillna('') + ' ' + df['Apellido'].fillna('')
            df['Nombre Completo'] = df['Nombre Completo'].str.strip()
            df['Cedula'] = df['Cedula'].astype(str)
            df['Telefono'] = df['Telefono'].astype(str)
            
            return df[['Nombre Completo', 'Cedula', 'Telefono']]
        else:
            st.error("La hoja 'Lista' no contiene las columnas 'Nombre' y 'Apellido'.")
            return pd.DataFrame(columns=['Nombre Completo', 'Cedula', 'Telefono'])
    
    except RequestException as e:
        st.error(f"Error al descargar el archivo de Excel: {e}")
        return pd.DataFrame(columns=['Nombre Completo', 'Cedula', 'Telefono'])
    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo Excel: {e}")
        return pd.DataFrame(columns=['Nombre Completo', 'Cedula', 'Telefono'])

def obtener_estudiantes_agregados():
    """
    Obtiene los estudiantes de la base de datos Firestore.
    """
    estudiantes_ref = db.collection('estudiantes_agregados')
    docs = estudiantes_ref.stream()
    
    registros = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        registros.append(data)
    
    df = pd.DataFrame(registros)
    if not df.empty:
        df['Nombre Completo'] = df['Nombre'] + ' ' + df['Apellido']
        df['Nombre Completo'] = df['Nombre Completo'].str.strip()
    return df

def guardar_asistencia(fecha_asistencia, registros):
    """
    Guarda la asistencia en la base de datos Firestore.
    """
    asistencia_ref = db.collection('asistencia')
    doc_id = str(fecha_asistencia)
    asistencia_ref.document(doc_id).set({'registros': registros})
    st.success(f'¡Asistencia guardada con éxito para el {fecha_asistencia}!')

def agregar_estudiante(nombre, apellido, cedula, telefono):
    """
    Agrega un nuevo estudiante a la base de datos Firestore.
    """
    estudiantes_ref = db.collection('estudiantes_agregados')
    
    doc_ref = estudiantes_ref.document(str(cedula))
    doc = doc_ref.get()
    
    if doc.exists:
        st.error(f"Error: La cédula '{cedula}' ya existe en la base de datos.")
    else:
        estudiantes_ref.document(str(cedula)).set({
            'Nombre': nombre,
            'Apellido': apellido,
            'Cedula': cedula,
            'Telefono': telefono
        })
        st.success(f"¡Estudiante '{nombre} {apellido}' agregado exitosamente!")
    st.rerun()

def modificar_estudiante(cedula, nuevo_nombre, nuevo_apellido, nuevo_telefono):
    """
    Modifica un estudiante existente en la base de datos Firestore.
    """
    estudiantes_ref = db.collection('estudiantes_agregados').document(str(cedula))
    estudiantes_ref.update({
        'Nombre': nuevo_nombre,
        'Apellido': nuevo_apellido,
        'Telefono': nuevo_telefono
    })
    st.success(f"¡Estudiante con cédula '{cedula}' modificado exitosamente!")
    st.rerun()

def eliminar_estudiante(cedula):
    """
    Elimina un estudiante de la base de datos Firestore.
    """
    estudiantes_ref = db.collection('estudiantes_agregados').document(str(cedula))
    estudiantes_ref.delete()
    st.success(f"¡Estudiante con cédula '{cedula}' eliminado exitosamente!")
    st.rerun()

def pagina_toma_asistencia(df_final):
    st.header('📝 Toma de Asistencia')
    st.write('Selecciona la fecha y marca la asistencia de cada estudiante.')
    
    estudiantes = df_final['Nombre Completo'].tolist()
    
    if not estudiantes:
        st.warning("No se pudo cargar la lista de estudiantes. Revisa la conexión y el contenido de los archivos.")
        st.stop()
        
    st.markdown("---")
    
    fecha_seleccionada = st.date_input('Selecciona la fecha:', date.today())
    
    st.markdown("---")
    
    asistencia_del_dia = {}
    st.subheader('Lista de Estudiantes')
    
    for estudiante in estudiantes:
        asistencia_del_dia[estudiante] = st.checkbox(estudiante)
        
    st.markdown("---")
    
    if st.button('✅ Guardar Asistencia'):
        registros_a_guardar = []
        for nombre, presente in asistencia_del_dia.items():
            registros_a_guardar.append({
                'Fecha': str(fecha_seleccionada),
                'Nombre': nombre,
                'Presente': 'Sí' if presente else 'No'
            })
        
        guardar_asistencia(fecha_seleccionada, registros_a_guardar)
    
    st.markdown("---")
    
    st.subheader('📊 Historial de Asistencia')
    asistencia_docs = db.collection('asistencia').stream()
    asistencia_historial = []
    for doc in asistencia_docs:
        doc_data = doc.to_dict()
        for registro in doc_data.get('registros', []):
            asistencia_historial.append(registro)
    
    if asistencia_historial:
        df_asistencia = pd.DataFrame(asistencia_historial)
        st.dataframe(df_asistencia, use_container_width=True)
    else:
        st.info("Aún no hay registros de asistencia.")

def pagina_gestion_estudiantes(df_final):
    st.header('🛠️ Gestión de Estudiantes')
    st.write('Aquí puedes ver, agregar, modificar y eliminar registros de estudiantes.')
    
    # ------------------
    # Gestión de registros
    # ------------------
    st.markdown("---")
    
    st.subheader('➕ Agregar Nuevo Estudiante')
    with st.form(key='agregar_estudiante_form'):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nombre = st.text_input('Nombre', key='nuevo_nombre')
            nueva_cedula = st.text_input('Cédula', key='nueva_cedula')
        with col2:
            nuevo_apellido = st.text_input('Apellido', key='nuevo_apellido')
            nuevo_telefono = st.text_input('Teléfono', key='nuevo_telefono')
            
        submit_button = st.form_submit_button(label='Guardar Estudiante')
        
    if submit_button:
        if nuevo_nombre and nuevo_apellido and nueva_cedula:
            agregar_estudiante(nuevo_nombre, nuevo_apellido, nueva_cedula, nuevo_telefono)
        else:
            st.error("Por favor, completa los campos de Nombre, Apellido y Cédula.")
            st.stop()

    st.markdown("---")

    st.subheader('✏️ Modificar o Eliminar Estudiante')
    if not df_final.empty:
        df_final = df_final.set_index('Cedula')
        estudiante_cedulas = df_final.index.tolist()
        estudiante_seleccionado = st.selectbox(
            'Selecciona un estudiante por cédula:',
            options=estudiante_cedulas
        )

        if estudiante_seleccionado:
            estudiante_data = df_final.loc[estudiante_seleccionado]
            
            with st.form(key='modificar_estudiante_form'):
                col1, col2 = st.columns(2)
                with col1:
                    mod_nombre = st.text_input('Nombre', value=estudiante_data.get('Nombre', ''), key='mod_nombre')
                    mod_cedula = st.text_input('Cédula', value=estudiante_data.name, key='mod_cedula', disabled=True)
                with col2:
                    mod_apellido = st.text_input('Apellido', value=estudiante_data.get('Apellido', ''), key='mod_apellido')
                    mod_telefono = st.text_input('Teléfono', value=estudiante_data.get('Telefono', ''), key='mod_telefono')

                col_mod, col_del = st.columns([1, 1])
                with col_mod:
                    modificar_button = st.form_submit_button('Modificar Estudiante')
                with col_del:
                    eliminar_button = st.form_submit_button('Eliminar Estudiante')

            if modificar_button:
                modificar_estudiante(mod_cedula, mod_nombre, mod_apellido, mod_telefono)
            
            if eliminar_button:
                st.warning("Estás a punto de eliminar este estudiante. Esta acción es irreversible.")
                if st.button('Confirmar Eliminación'):
                    eliminar_estudiante(mod_cedula)
    
    st.markdown("---")
    st.subheader('Tabla de Todos los Estudiantes')
    st.dataframe(df_final, use_container_width=True)

def main():
    st.title('📋 Sistema de Asistencia y Gestión de Estudiantes')
    
    # Intenta obtener la lista de estudiantes
    with st.spinner('Cargando lista de estudiantes...'):
        df_excel = obtener_estudiantes_de_excel()
        df_registros = obtener_estudiantes_agregados()
    
    # Unir las listas y quitar duplicados. Los de la base de datos tienen prioridad.
    df_registros_filtrados = df_registros[['Nombre Completo', 'Cedula', 'Telefono', 'id']] if 'id' in df_registros.columns else pd.DataFrame(columns=['Nombre Completo', 'Cedula', 'Telefono', 'id'])
    
    df_final = pd.concat([df_excel, df_registros_filtrados], ignore_index=True).drop_duplicates(subset=['Cedula'], keep='last')

    st.sidebar.title('Menú')
    opcion = st.sidebar.radio('Navegación', ['Toma de Asistencia', 'Gestión de Estudiantes'])
    
    if opcion == 'Toma de Asistencia':
        pagina_toma_asistencia(df_final)
    elif opcion == 'Gestión de Estudiantes':
        pagina_gestion_estudiantes(df_final)

if __name__ == '__main__':
    main()
