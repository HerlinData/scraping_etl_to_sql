import sys
sys.path.append('Z:\AMG Esuarezh\SysAnalistas')
import locale
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine,text,Table, MetaData
from funciones.conexion import *
import pyodbc
from datetime import datetime, timedelta
from funciones.funcionEstadoAgente import *
import warnings
warnings.filterwarnings("ignore")
from datetime import timedelta

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

fecha = str
mesNombre = str
dia = int
mes = int
año = int

# Establecer configuración regional en español
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

# Leer fecha/hora compartida desde archivo
with open("shared_timestamp.txt", "r") as f:
    fecha_hora = f.read().strip()

fecha_hora = pd.to_datetime(fecha_hora)
# Sumarle 120 segundos
fecha_hora = fecha_hora + timedelta(seconds=120)

def cargar_datos_estadoagente():
    mesNombre = fecha_hora.strftime('%B').capitalize()  # Nombre del mes en español
    dia = fecha_hora.strftime('%d')  # Devuelve '01', '06', etc.
    mes = fecha_hora.strftime('%m')  # También puedes usar esto si quieres el mes con 2 dígitos
    año = fecha_hora.year

# Datos de conexión SQLALCHEMY

    # Generar conexión con la BD, para enviar los datos procesados

# Ruta origen de los archivos
    ruta_origen = f'Z:\\DESCARGA INFORMES\\{año}\\Estado Agente\\{mesNombre}\\EstadoAgente{dia}.csv'
    

    #df_ea = check_and_concatenate_csv_files(ruta_origen)
    df = pd.read_csv(ruta_origen,sep=",")

    df['Hora inicio'] = pd.to_datetime(df['Hora inicio'])
    df['Hora fin'] = pd.to_datetime(df['Hora fin'])

    # COLOCAMOS HORA FIN CON LA INFO ACTUAL DEL CORTE
    df['Hora fin'] = df['Hora fin'].fillna(fecha_hora)

    # Obtener la fecha de las columnas DATETIME
    df['fecha_inicio'] = df['Hora inicio'].dt.date
    df['fecha_fin'] = df['Hora fin'].dt.date

    # Asegurarse de que 'fecha_inicio' y 'fecha_fin' sean tipo datetime
    df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio'])
    df['fecha_fin'] = pd.to_datetime(df['fecha_fin'], errors='coerce')  # Manejar valores vacíos (NaT)

    # Condición: si 'fecha_fin' es distinta de 'fecha_inicio' o si 'fecha_fin' está vacía (NaT)
    df.loc[(df['fecha_fin'] != df['fecha_inicio']) | (df['fecha_fin'].isna()), 'Hora fin'] = df['Hora inicio']

    #print(df)
    # Procesamiento para eliminar SOF - Sign Off consecutivos por cada asesor
    for agente, grupo in df.groupby('Codigo del Agente'):
        indices_a_eliminar = []  # Para almacenar los índices de los SOF consecutivos a eliminar
        ultimo_sign_off = None  # Para almacenar el índice del último SOF consecutivo
        
        for i in range(1, len(grupo)):
            registro_actual = grupo.iloc[i]
            registro_anterior = grupo.iloc[i - 1]
            
            # Si el registro actual y el anterior son 'SOF - Sign Off'
            if registro_actual['Funcion'] == 'SOF - Sign Off':
                if registro_anterior['Funcion'] == 'SOF - Sign Off':
                    # Marcar el anterior para eliminar
                    indices_a_eliminar.append(grupo.index[i - 1])
                ultimo_sign_off = grupo.index[i]  # Guardar el índice del último SOF consecutivo
        
        # Si encontramos varios consecutivos, eliminar todos menos el último
        if indices_a_eliminar:
            # Si el último SOF consecutivo está en la lista de eliminación, no lo eliminamos
            if ultimo_sign_off in indices_a_eliminar:
                indices_a_eliminar.remove(ultimo_sign_off)
        
        # Eliminar los registros marcados como duplicados
        df = df.drop(indices_a_eliminar)

    # Reiniciar el índice del DataFrame después de eliminar registros
    df = df.reset_index(drop=True)

    # Generar una copia independiente del DF
    df_final = df.copy()
                        
    # Procesamiento para ajustar 'Hora fin' por cada asesor
    for agente, grupo in df_final.groupby('Codigo del Agente'):
        for i in range(1, len(grupo)):
            # Registro actual en el grupo
            registro_actual = grupo.iloc[i]

            if registro_actual['Funcion'] == 'SOF - Sign Off':
                # Registro anterior
                registro_anterior = grupo.iloc[i - 1]
                
                # Verificar si existe un siguiente registro para aplicar la lógica de los 5 minutos
                if i < len(grupo) - 1:
                    registro_siguiente = grupo.iloc[i + 1]
                    
                    # Comparar la diferencia entre la Hora inicio del SOF - Sign Off y el siguiente registro
                    diferencia_tiempo = registro_siguiente['Hora inicio'] - registro_actual['Hora inicio']
                    
                    # Si la diferencia de tiempo es menor o igual a 5 minutos
                    if diferencia_tiempo <= pd.Timedelta(minutes=5):
                        # Ajustar 'Hora fin' del registro anterior al 'Hora inicio' del registro siguiente
                        df_final.at[grupo.index[i - 1], 'Hora fin'] = registro_siguiente['Hora inicio']
                    else:
                        # Si la diferencia de tiempo es mayor a 5 minutos, ajustar 'Hora fin' del registro anterior con la 'Hora fin' del registro actual
                        df_final.at[grupo.index[i - 1], 'Hora fin'] = registro_actual['Hora inicio']                
            
            # Ajuste en caso de que no haya SOF - Sign Off
            else:
                if i > 0:  # Evitar índice fuera de rango
                    registro_anterior = grupo.iloc[i - 1]
                    # Ajustar 'Hora fin' del registro anterior al 'Hora inicio' del registro actual
                    df_final.at[grupo.index[i - 1], 'Hora fin'] = registro_actual['Hora inicio']

        # Caso donde el SOF - Sign Off es el último estado de un asesor
        if len(grupo) > 1 and grupo.iloc[-1]['Funcion'] == 'SOF - Sign Off':
            df_final.at[grupo.index[-2], 'Hora fin'] = grupo.iloc[-1]['Hora inicio']

    # Filtrar los registros de 'SOF - Sign Off'
    df_final = df_final[df_final['Funcion'] != 'SOF - Sign Off'].reset_index(drop=True)

    # Aplicar una operación entre columnas solo a las filas que cumplen la condición
    df_final['Total estimado'] = df_final['Hora fin'] - df_final['Hora inicio']  # Ejemplo de suma entre dos columnas
    df_final['Total estimado'] = df_final['Total estimado'].astype(str).str.split().str[-1]

    # Paso 1: Contar la frecuencia de cada fecha en 'fecha_inicio'
    fecha_frecuencia = df_final['fecha_inicio'].value_counts(normalize=True)

    # Paso 2: Verificar si la frecuencia más alta es mayor o igual al 90%
    fecha_mas_frecuente = fecha_frecuencia.idxmax()
    porcentaje_mas_frecuente = fecha_frecuencia.max()

    if porcentaje_mas_frecuente >= 0.9:
        # Paso 3: Si cumple con el 90%, filtrar los registros con esa fecha
        df_final = df_final[df_final['fecha_inicio'] == fecha_mas_frecuente]
    else:
        # Paso 4: Si no cumple, eliminar todos los registros
        df_final = pd.DataFrame()  # O eliminar las filas que no cumplen
        print("No hay una fecha válida con al menos el 90% de coincidencia. Se eliminaron los registros.")

    # Columnas necesarias para enviar a SQL
    columnas = ['Codigo del Agente','Agente', 'Funcion', 'Gestion',	'Hora inicio',	'Hora fin',	'Total estimado']
    df_to_sql = df_final[columnas]

    # Obtener la fecha actual como un objeto datetime
    fecha_actual = datetime.now()

    fechacompleta = str(fecha_hora)

    df_to_sql.to_csv('data_rev.csv', index=False)

    engine = conectar_bdCargaExcel()
        # Ejecutar la eliminación en la base de datos
    with engine.connect() as connection:
        connection.execute(text(f"DELETE FROM TblEstadoAgenteExcel"))
        connection.execute(text("COMMIT"))

    #print(f"Registros eliminados en la tabla TblEstadoAgentePre con 'Hora inicio' igual a {Fechacompleta.split('= ')[1]}.")

    # Cargar los datos combinados a la base de datos
    with engine.connect() as connection:
        df_to_sql.to_sql('TblEstadoAgenteExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
        
    VAR = 'EA'
    # Mover archivos de la carpeta de seguimiento
    # mover_archivos_ea(ruta_origen, ruta_destino, VAR)
        
    # print(f"Datos cargados en la tabla TblEstadoAgentePre fecha: {fecha_mas_frecuente}.")
    #######################################################################################
    conexion = conectar_bdStores()
    try:
        
        cursor = conexion.cursor()
        parametros = (fechacompleta, mes,año,)   # Tupla de tres valores

        # Llamar al procedimiento almacenado
        cursor.callproc('Sp_EstadoagenteSalesys', parametros)

        # Obtener el resultado
        result = cursor.fetchone()
        conexion.commit() 
        print(f"Resultado obtenido: {result}")  # Depuración, muestra el resultado antes de procesar

        if result:  # Si hay resultados
            return result['Total']  # Accede a la clave 'Total' del diccionario
        else:
            return "No Data"  # Si no hay resultados

    except pymssql.DatabaseError as e:
        # Manejo de errores específicos de la base de datos
        print(f"Error en la base de datos: {e}")
        return f"Error en la base de datos: {e}"

    except Exception as e:
        # Captura de la traza completa del error
        import traceback
        error_details = traceback.format_exc()
        print(f"Error ocurrió: {error_details}")  # Imprime el error completo
        return f"Error en la obtención de datos: {error_details}"

    finally:
        # Asegurarse de cerrar tanto el cursor como la conexión
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()             
            
cargar_datos_estadoagente()
