import streamlit as st
import pandas as pd
import requests
import io
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client
from requests.exceptions import RequestException

# Initialize Firebase (already done in the environment)
try:
    # Cargar la configuración como una cadena y luego parsearla a JSON
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
            for col in ['Cedula', 'Telefono']:
                if col not in df.columns:
                    df[col] = ''
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
        registros.append(doc.to_dict())
    
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
    
    # Verifica si la cédula ya existe para evitar duplicados
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

def main():
    """Lógica principal de la aplicación Streamlit."""
    st.set_page_config(layout="wide")
    st.title('📋 Sistema de Asistencia y Gestión de Estudiantes')
    
    # ------------------
    # Gestión de registros
    # ------------------
    st.markdown("---")
    st.header('➕ Administrar Estudiantes')
    st.write('Agrega nuevos estudiantes a la lista de asistencia.')
    
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

    # ------------------
    # Registro de asistencia
    # ------------------
    st.markdown("---")
    st.header('📝 Registro de Asistencia')
    st.write('Selecciona la fecha y marca la asistencia de cada estudiante.')
    
    # Intenta obtener la lista de estudiantes
    with st.spinner('Cargando lista de estudiantes...'):
        df_excel = obtener_estudiantes_de_excel()
        df_registros = obtener_estudiantes_agregados()
    
    # Unir las listas y quitar duplicados
    if not df_registros.empty:
        df_final = pd.concat([df_excel, df_registros[['Nombre Completo']]], ignore_index=True).drop_duplicates(subset=['Nombre Completo'])
    else:
        df_final = df_excel.copy()

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

if __name__ == '__main__':
    main()
