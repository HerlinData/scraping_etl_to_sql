import sys
sys.path.append('Z:\AMG Esuarezh\SysAnalistas')
from funciones.funcion import *
import sqlalchemy
from sqlalchemy import create_engine, text
import pyodbc
import pandas as pd
from datetime import datetime, timedelta
import locale
import pymssql
from unidecode import unidecode
from funciones.conexion import *


fechacompleta = datetime
mesNombre = str
dia = int
mes = int
año = int
######################################################################################################################
def cargar_datos_activaciones_corte():
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    fechacompleta = pd.Timestamp.now()
    print(fechacompleta)
    mesNombre = fechacompleta.strftime('%B').capitalize()  # Nombre del mes en español
    dia = fechacompleta.strftime('%d')  # Devuelve '01', '06', etc.
    mes = fechacompleta.strftime('%m')  # También puedes usar esto si quieres el mes con 2 dígitos
    año = fechacompleta.year
    ###############################################################################################
    ruta_Activaciones_HFC = f'Z:\\DESCARGA INFORMES\\{año}\\Activaciones\\{mesNombre}\\HFC\\hfc{dia}.csv'
    ruta_Activaciones_EMPRESA = f'Z:\\DESCARGA INFORMES\\{año}\\Activaciones\\{mesNombre}\\EMPRESA\\empresa{dia}.csv'
    ruta_Activaciones_LTE = f'Z:\\DESCARGA INFORMES\\{año}\\Activaciones\\{mesNombre}\\LTE\\lte{dia}.csv'
    ruta_Activaciones_FTTH = f'Z:\\DESCARGA INFORMES\\{año}\\Activaciones\\{mesNombre}\\FTTH\\ftth{dia}.csv'
    ruta_Activaciones_OTROS = f'Z:\\DESCARGA INFORMES\\{año}\\Activaciones\\{mesNombre}\\OTROS\\otros{dia}.csv'
    #ruta_DetalleSot = f'Z:\\DESCARGA INFORMES\\{año}\\Activaciones Detalle\\Detalle Sot\\Detalle_Sot_{mesNombre}.xlsm'
    ##
    # assasdasda   
    ######################################################################################################################    
    df_merged_HFC = pd.read_csv(ruta_Activaciones_HFC,sep=',',encoding='latin1') #separador de , en el CSV#
    df_merged_EMPRESA = pd.read_csv(ruta_Activaciones_EMPRESA,sep=',',encoding='latin1') #separador de , en el CSV#
    df_merged_LTE = pd.read_csv(ruta_Activaciones_LTE,sep=',',encoding='latin1') #separador de , en el CSV#
    df_merged_FTTH = pd.read_csv(ruta_Activaciones_FTTH,sep=',',encoding='latin1') #separador de , en el CSV#
    df_merged_OTROS = pd.read_csv(ruta_Activaciones_OTROS,sep=',',encoding='latin1') #separador de , en el CSV#  
    #df_merged_DetalleSot = pd.read_excel(ruta_DetalleSot)
    ######################################################################################################################
    #df_merged_Laraigo = pd.read_csv(ruta_Laraigo,sep='|',encoding='latin1') 
    #-1-#####################################################################################################################

    df_merged_HFC.columns = [normalize_column_name(col) for col in df_merged_HFC.columns]
    df_merged_HFC['hora_inicio_contrata'] = df_merged_HFC['hora_inicio_contrata'].apply(parse_fecha) 
    df_merged_HFC['hora_inicio_call_center'] = df_merged_HFC['hora_inicio_call_center'].apply(parse_fecha) 
    df_merged_HFC['hora_fin_call_center'] = df_merged_HFC['hora_fin_call_center'].apply(parse_fecha) 
    #-2-#####################################################################################################################
    df_merged_EMPRESA.columns = [normalize_column_name(col) for col in df_merged_EMPRESA.columns]
    df_merged_EMPRESA['hora_inicio_contrata'] = df_merged_EMPRESA['hora_inicio_contrata'].apply(parse_fecha) 
    df_merged_EMPRESA['hora_inicio_call_center'] = df_merged_EMPRESA['hora_inicio_call_center'].apply(parse_fecha) 
    df_merged_EMPRESA['hora_fin_call_center'] = df_merged_EMPRESA['hora_fin_call_center'].apply(parse_fecha) 
    #-3-#####################################################################################################################
    df_merged_LTE.columns = [normalize_column_name(col) for col in df_merged_LTE.columns]
    df_merged_LTE['hora_inicio_contrata'] = df_merged_LTE['hora_inicio_contrata'].apply(parse_fecha) 
    df_merged_LTE['hora_inicio_call_center'] = df_merged_LTE['hora_inicio_call_center'].apply(parse_fecha) 
    df_merged_LTE['hora_fin_call_center'] = df_merged_LTE['hora_fin_call_center'].apply(parse_fecha)
    #-4-#####################################################################################################################
    df_merged_FTTH.columns = [normalize_column_name(col) for col in df_merged_FTTH.columns]
    df_merged_FTTH['hora_inicio_contrata'] = df_merged_FTTH['hora_inicio_contrata'].apply(parse_fecha) 
    df_merged_FTTH['hora_inicio_call_center'] = df_merged_FTTH['hora_inicio_call_center'].apply(parse_fecha) 
    df_merged_FTTH['hora_fin_call_center'] = df_merged_FTTH['hora_fin_call_center'].apply(parse_fecha)
    #-5-#####################################################################################################################
    df_merged_OTROS.columns = [normalize_column_name(col) for col in df_merged_OTROS.columns]
    df_merged_OTROS['hora_inicio_contrata'] = df_merged_OTROS['hora_inicio_contrata'].apply(parse_fecha) 
    df_merged_OTROS['hora_inicio_call_center'] = df_merged_OTROS['hora_inicio_call_center'].apply(parse_fecha) 
    df_merged_OTROS['hora_fin_call_center'] = df_merged_OTROS['hora_fin_call_center'].apply(parse_fecha)
    #-6-#####################################################################################################################
    #df_merged_DetalleSot.columns = [normalize_column_name(col) for col in df_merged_DetalleSot.columns]
    ######################################################################################################################
    # Configuración de la conexión a la base de datos
    df_merged_HFC['nombre_usuario'] = df_merged_HFC['nombre_usuario'].astype(str).str.replace('A', '0')
    df_merged_EMPRESA['nombre_usuario'] = df_merged_EMPRESA['nombre_usuario'].astype(str).str.replace('A', '0')
    df_merged_LTE['nombre_usuario'] = df_merged_LTE['nombre_usuario'].astype(str).str.replace('A', '0')
    df_merged_FTTH['nombre_usuario'] = df_merged_FTTH['nombre_usuario'].astype(str).str.replace('A', '0')
    df_merged_OTROS['nombre_usuario'] = df_merged_OTROS['nombre_usuario'].astype(str).str.replace('A', '0')


    engine = conectar_bdCargaExcel()
    #-1-#####################################################################################################################
    with engine.connect() as connection:
        # Iniciar una transacción explícita
        with connection.begin() as transaction:
            connection.execute(text("DELETE FROM dbo.TblActivacionesHFCExcel"))
            transaction.commit()

    with engine.connect() as connection:
        df_merged_HFC.to_sql('TblActivacionesHFCExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
    print("Datos cargados exitosamente en la base de datos TblActivacionesHFCExcel.")
    #-2-#####################################################################################################################
    with engine.connect() as connection:
        # Iniciar una transacción explícita
        with connection.begin() as transaction:
            connection.execute(text("DELETE FROM dbo.TblActivacionesEmpresaExcel"))
            transaction.commit()

    with engine.connect() as connection:
        df_merged_EMPRESA.to_sql('TblActivacionesEmpresaExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
    print("Datos cargados exitosamente en la base de datos TblActivacionesEmpresaExcel.")
    #-3-#####################################################################################################################
    with engine.connect() as connection:
        # Iniciar una transacción explícita
        with connection.begin() as transaction:
            connection.execute(text("DELETE FROM dbo.TblActivacionesLTEExcel"))
            transaction.commit()

    with engine.connect() as connection:
        df_merged_LTE.to_sql('TblActivacionesLTEExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
    print("Datos cargados exitosamente en la base de datos TblActivacionesLTEExcel.")
    #-4-#####################################################################################################################
    with engine.connect() as connection:
        # Iniciar una transacción explícita
        with connection.begin() as transaction:
            connection.execute(text("DELETE FROM dbo.TblActivacionesFTTHExcel"))
            transaction.commit()

    with engine.connect() as connection:
        df_merged_FTTH.to_sql('TblActivacionesFTTHExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
    print("Datos cargados exitosamente en la base de datos TblActivacionesFTTHExcel.")
    #-5-#####################################################################################################################
    with engine.connect() as connection:
        # Iniciar una transacción explícita
        with connection.begin() as transaction:
            connection.execute(text("DELETE FROM dbo.TblActivacionesOTROSExcel"))
            transaction.commit()

    with engine.connect() as connection:
        df_merged_OTROS.to_sql('TblActivacionesOTROSExcel', con=connection, if_exists='append', index=False)
        connection.execute(text("COMMIT"))
    print("Datos cargados exitosamente en la base de datos TblActivacionesOTROSExcel.")

    # -6-#####################################################################################################################
    # with engine.connect() as connection:
    #     # Iniciar una transacción explícita
    #     with connection.begin() as transaction:
    #         connection.execute(text("DELETE FROM dbo.TblDetalleSotExcel"))
    #         transaction.commit()

    # with engine.connect() as connection:
    #     df_merged_DetalleSot.to_sql('TblDetalleSotExcel', con=connection, if_exists='append', index=False)
    #     connection.execute(text("COMMIT"))
    # print("Datos cargados exitosamente en la base de datos TblDetalleSotExcel.")

    #####################################################################################################################
    #Conectar a la base de datos Pym
    fechacompleta = str(fechacompleta)
    conexion = conectar_bdStores()
    try:

        cursor = conexion.cursor()
        parametros = (fechacompleta, mes,año,)  # Tupla de tres valores

        # Llamar al procedimiento almacenado
        cursor.callproc('Sp_CampañaActivaciones', parametros)

        # Obtener el resultado
        result = cursor.fetchone()
        conexion.commit() 
        print(f"Resultado obtenido: {result}")  # Depuración, muestra el resultado antes de procesar

        if result:  # Si hay resultados
            print("hola")# return result['Total']  # Accede a la clave 'Total' del diccionario
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

cargar_datos_activaciones_corte()