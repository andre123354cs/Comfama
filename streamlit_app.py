import streamlit as st
import pandas as pd
import os
from datetime import date
import requests
import io
from requests.exceptions import RequestException

# Nombre del archivo para guardar la asistencia
ASISTENCIA_FILE = 'asistencia.csv'

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
            # Asegurar que las columnas Cedula y Telefono existan, aunque estén vacías
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

def guardar_asistencia(fecha_asistencia, registros):
    """
    Guarda la asistencia en un archivo CSV.
    Si el archivo existe, añade los nuevos registros.
    """
    df_nuevos = pd.DataFrame(registros)
    
    if os.path.exists(ASISTENCIA_FILE):
        df_existente = pd.read_csv(ASISTENCIA_FILE)
        df_limpio = df_existente[df_existente['Fecha'] != str(fecha_asistencia)]
        df_final = pd.concat([df_limpio, df_nuevos], ignore_index=True)
    else:
        df_final = df_nuevos
    
    df_final.to_csv(ASISTENCIA_FILE, index=False)

def agregar_estudiante(nombre, apellido, cedula, telefono):
    """
    Agrega un nuevo estudiante a los secretos de Streamlit.
    """
    nuevo_registro = {
        'Nombre': nombre,
        'Apellido': apellido,
        'Cedula': cedula,
        'Telefono': telefono
    }
    
    # Obtener el diccionario de registros, o crear uno si no existe
    registros = st.secrets.get('registros_agregados', {})
    
    # Usar la cédula como clave para evitar duplicados
    registros[cedula] = nuevo_registro
    
    # Guardar el diccionario actualizado en los secretos
    st.secrets['registros_agregados'] = registros
    
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
    
    # Cargar registros de st.secrets
    registros_secrets = st.secrets.get('registros_agregados', {})
    df_registros = pd.DataFrame.from_dict(registros_secrets, orient='index')
    
    # Si hay registros, crear la columna de Nombre Completo
    if not df_registros.empty:
        df_registros['Nombre Completo'] = df_registros['Nombre'].fillna('') + ' ' + df_registros['Apellido'].fillna('')
        df_registros['Nombre Completo'] = df_registros['Nombre Completo'].str.strip()
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
        st.success(f'¡Asistencia guardada con éxito para el {fecha_seleccionada}!')
    
    st.markdown("---")
    
    st.subheader('📊 Historial de Asistencia')
    if os.path.exists(ASISTENCIA_FILE):
        df_asistencia = pd.read_csv(ASISTENCIA_FILE)
    else:
        df_asistencia = pd.DataFrame(columns=['Fecha', 'Nombre', 'Presente'])

    st.dataframe(df_asistencia, use_container_width=True)

if __name__ == '__main__':
    main()
