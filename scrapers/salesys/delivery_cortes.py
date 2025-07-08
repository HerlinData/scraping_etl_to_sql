import sys
sys.path.append('Z:\AMG Esuarezh\SysAnalistas')
from funciones.funcion import *
import sqlalchemy
from sqlalchemy import create_engine, text
import pyodbc
import pandas as pd
import locale
import pymssql
from collections import Counter
from unidecode import unidecode
from funciones.conexion import *
import mimetypes

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

fecha = str
mesNombre = str
dia = int
mes = int
año = int

def cargar_datos_Delivery():
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    fechacompleta = pd.Timestamp.now()
    print(fechacompleta)
    mesNombre = fechacompleta.strftime('%B').capitalize()  # Nombre del mes en español
    dia = fechacompleta.strftime('%d')  # Devuelve '01', '06', etc.
    mes = fechacompleta.strftime('%m')  # También puedes usar esto si quieres el mes con 2 dígitos
    año = fechacompleta.year

    ruta_Delivery = f'Z:\\DESCARGA INFORMES\\{año}\\Delivery\\{mesNombre}\\\General\\delivery{dia}.csv'   
    ruta_rend_baseIVR = f'Z:\\DESCARGA INFORMES\\{año}\\Delivery\\{mesNombre}\\IVR BASE\\IvrBase{dia}.xlsx'


    df_merged_Delivery = pd.read_csv(ruta_Delivery,sep=',', on_bad_lines='skip') #separador de , en el CSV#
    df_merged_baseIVR = pd.read_excel(ruta_rend_baseIVR) #separador de , en el excel#


    df_merged_Delivery.columns = [normalize_column_name(col) for col in df_merged_Delivery.columns]
    df_merged_baseIVR.columns = [normalize_column_name(col) for col in df_merged_baseIVR.columns]

    df_merged_Delivery['hora_inicio_contrata'] = pd.to_datetime(df_merged_Delivery['hora_inicio_contrata'])
    df_merged_Delivery['hora_inicio_call_center'] = pd.to_datetime(df_merged_Delivery['hora_inicio_call_center'])
    df_merged_Delivery['hora_fin_call_center'] = pd.to_datetime(df_merged_Delivery['hora_fin_call_center'])


    df_merged_baseIVR['fecha'] = pd.to_datetime(df_merged_baseIVR['fecha'],format='%d/%m/%Y')


    # Renombrar columnas con nombres duplicados
    
    new_cols = []
    counts = Counter()


    #print(df_unificado.columns)
    fechacompleta = str(fechacompleta)
    # -- Abro conexion con sqlalchemy
    engine = conectar_bdCargaExcel()

    with engine.connect() as connection:
        # Iniciar una transacción explícita
        with connection.begin() as transaction:
            connection.execute(text("DELETE FROM TblDeliveryExcel"))
            transaction.commit()

    with engine.connect() as connection:
        # Iniciar una transacción explícita
        with connection.begin() as transaction:
            connection.execute(text("DELETE FROM dbo.TblIvrCalidadExcel"))
            transaction.commit()           


    with engine.connect() as connection:
        df_merged_Delivery.to_sql('TblDeliveryExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
    print("Datos cargados exitosamente en la base de datos en Rechazo.")


    with engine.connect() as connection:
        df_merged_baseIVR.to_sql('TblIvrCalidadExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
    print("Datos cargados exitosamente en la base de datos en Ivr Calidad.")


    ######################################################################################################################
    conexion = conectar_bdStores()
    try:
        
        cursor = conexion.cursor()
        parametros = (fechacompleta, mes,año)   # Tupla de tres valores

        # Llamar al procedimiento almacenado
        cursor.callproc('Sp_CampañaDelivery', parametros)

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
            
cargar_datos_Delivery()