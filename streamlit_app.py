import streamlit as st
import pandas as pd
import os
from datetime import date
import requests
import io
import zipfile

# Nombre del archivo para guardar la asistencia
ASISTENCIA_FILE = 'asistencia.csv'

# URL del archivo Excel para descargar la lista de estudiantes
EXCEL_URL = 'https://powerbi.yesbpo.com/public.php/dav/files/m5ytip22YkX5SKt/?accept=zip'

@st.cache_data
def obtener_estudiantes_de_excel():
    """
    Descarga el archivo Excel de la URL, lo descomprime,
    lee la hoja 'Lista' y devuelve la columna de nombres.
    """
    try:
        # Descarga el archivo zip
        response = requests.get(EXCEL_URL)
        response.raise_for_status() # Lanza un error para códigos de estado HTTP incorrectos
        
        # Lee el contenido del zip en memoria
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Busca el archivo .xlsx dentro del zip
            excel_file_path = [f for f in z.namelist() if f.endswith('.xlsx') or f.endswith('.xls')]
            if not excel_file_path:
                st.error("No se encontró ningún archivo de Excel dentro del zip.")
                return []
            
            # Abre el archivo de Excel y lo lee con pandas
            with z.open(excel_file_path[0]) as f:
                df = pd.read_excel(f, sheet_name='Lista')
                # Asume que la columna de nombres se llama 'NOMBRE'. Puedes cambiarla si es diferente.
                if 'NOMBRE' in df.columns:
                    return df['NOMBRE'].tolist()
                else:
                    st.error("La hoja 'Lista' no contiene la columna 'NOMBRE'.")
                    return []
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error al descargar el archivo: {e}")
        return []
    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        return []

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

def main():
    """Lógica principal de la aplicación Streamlit."""
    st.set_page_config(layout="wide")
    st.title('📋 Registro de Asistencia del Salón')
    st.write('Selecciona la fecha y marca la asistencia de cada estudiante. La lista se carga automáticamente desde el archivo de Excel.')
    
    # Intenta obtener la lista de estudiantes del archivo Excel
    estudiantes = obtener_estudiantes_de_excel()
    if not estudiantes:
        st.warning("No se pudo cargar la lista de estudiantes. Por favor, revisa la URL y el contenido del archivo de Excel.")
        return
        
    st.markdown("---")
    
    # Selector de fecha
    fecha_seleccionada = st.date_input('Selecciona la fecha:', date.today())
    
    st.markdown("---")
    
    # Crear un diccionario para almacenar el estado de los checkboxes
    asistencia_del_dia = {}
    st.subheader('Lista de Estudiantes')
    
    # Mostrar la lista de estudiantes con un checkbox para cada uno
    for estudiante in estudiantes:
        asistencia_del_dia[estudiante] = st.checkbox(estudiante)
        
    st.markdown("---")
    
    if st.button('✅ Guardar Asistencia'):
        # Recolectar los datos para guardar
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
