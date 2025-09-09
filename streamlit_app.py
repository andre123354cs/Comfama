import streamlit as st
import pandas as pd
import os
from datetime import date

# Nombre del archivo para guardar la asistencia
ASISTENCIA_FILE = 'asistencia.csv'

# Lista de estudiantes del salón (puedes modificar esta lista)
estudiantes = [
    'Ana García',
    'Juan Pérez',
    'María López',
    'Carlos Ruíz',
    'Sofía Fernández',
    'Daniel Gómez',
    'Valentina Vargas',
    'Manuel Castro'
]

def guardar_asistencia(fecha_asistencia, registros):
    """
    Guarda la asistencia en un archivo CSV.
    Si el archivo existe, añade los nuevos registros.
    """
    df_nuevos = pd.DataFrame(registros)
    
    # Verifica si el archivo ya existe
    if os.path.exists(ASISTENCIA_FILE):
        df_existente = pd.read_csv(ASISTENCIA_FILE)
        
        # Elimina los registros antiguos para la fecha actual antes de guardar
        df_limpio = df_existente[df_existente['Fecha'] != str(fecha_asistencia)]
        
        # Combina los datos existentes con los nuevos
        df_final = pd.concat([df_limpio, df_nuevos], ignore_index=True)
    else:
        df_final = df_nuevos
    
    df_final.to_csv(ASISTENCIA_FILE, index=False)

def main():
    """Lógica principal de la aplicación Streamlit."""
    st.set_page_config(layout="wide")
    st.title('📋 Registro de Asistencia del Salón')
    st.write('Selecciona la fecha y marca la asistencia de cada estudiante. Al finalizar, haz clic en "Guardar Asistencia".')
    
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
        
        # Llamar a la función para guardar los datos
        guardar_asistencia(fecha_seleccionada, registros_a_guardar)
        st.success(f'¡Asistencia guardada con éxito para el {fecha_seleccionada}!')
    
    st.markdown("---")
    
    st.subheader('📊 Historial de Asistencia')
    # Mostrar la tabla con la asistencia guardada
    if os.path.exists(ASISTENCIA_FILE):
        df_asistencia = pd.read_csv(ASISTENCIA_FILE)
    else:
        # Si el archivo no existe, crea un DataFrame vacío para evitar errores
        df_asistencia = pd.DataFrame(columns=['Fecha', 'Nombre', 'Presente'])

    st.dataframe(df_asistencia, use_container_width=True)

if __name__ == '__main__':
    main()
