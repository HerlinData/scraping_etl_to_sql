import pandas as pd
import sys
import sqlalchemy
from sqlalchemy import create_engine,text,Table, MetaData
import locale
import pyodbc
from datetime import datetime, timedelta
from unidecode import unidecode
import warnings
warnings.filterwarnings('ignore')

def procesar_ocupacion_activaciones(
    fechas, 
    log_fn=None
):
    def log(msg):
        if log_fn:
            log_fn(msg)
        else:
            print(msg)

    def conectar_bd(servidor, nombre_base_datos, usuario, contraseña):
        connection_string = f'mssql+pyodbc://{usuario}:{contraseña}@{servidor}/{nombre_base_datos}?driver=ODBC+Driver+17+for+SQL+Server'
        engine = create_engine(connection_string)
        log('Conexión exitosa')
        return engine

    franjas = pd.read_csv('Z:\\AMG Esuarezh\\scraping\\scrapers\\salesys\\franjas_horarias.csv', sep=',')

    servidor = '192.168.16.103'
    nombre_base_datos = 'BD_AMG'
    usuario = 'sqladmin'
    contraseña = 'Rf1pGIw7C42m'
    engine = conectar_bd(servidor, nombre_base_datos, usuario, contraseña)

    # Establecer configuración regional en español
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        log("[WARNING] No se pudo establecer locale es_ES.UTF-8, usando default")
        locale.setlocale(locale.LC_TIME, 'C')

    for fecha_input in fechas:
        # Procesar cada fecha
        if isinstance(fecha_input, str):
            fechacompleta = datetime.strptime(fecha_input, "%Y-%m-%d")
        else:
            fechacompleta = fecha_input
            
        fecha = fechacompleta.date()
        log(f"\\n[PROCESANDO] Fecha: {fecha}")
        
        try:
            mesNombre = fechacompleta.strftime('%B').capitalize()
            dia = fechacompleta.strftime('%d')
            mes = fechacompleta.strftime('%m')
            año = fechacompleta.year

            # Leer datos desde la base de datos a un DataFrame
            with engine.connect() as connection:
                df = pd.read_sql(f"""SELECT nombre_usuario codigo_salesys, asesor, hora_inicio_call_center,
                                        hora_fin_call_center FROM TblActivacionesBD 
                                            WHERE CONVERT(DATE, hora_inicio_call_center ) = '{fecha}'
                                            AND NOT hora_inicio_call_center IS NULL""", con=connection)

            with engine.connect() as connection:
                df_2 = pd.read_sql(f"SELECT CONVERT(DATE, hora_inicio) fecha, codigo_del_agente codigo_salesys, [FUNCION] funcion, [hora_inicio], [hora_fin] FROM TblEstadoAgenteSaleSysBD WHERE CONVERT(DATE,[hora_inicio]) = '{fecha}'", con=connection)
            df_2['fecha'] = pd.to_datetime(df_2['fecha'])

            with engine.connect() as connection:
                df_3 = pd.read_sql(f"SELECT [fecha], [Codigo SaleSys] codigo_salesys, [Nombre Completo] nombre, [condicion], [cargo], [CAMPAÑA] campana FROM View_TblNomina WHERE CONVERT(DATE, [fecha]) = '{fecha}' AND campaña = 'ACTIVACIONES'", con=connection)
            df_3['codigo_salesys'] = df_3['codigo_salesys'].astype('Int64')
            df_3['fecha'] = pd.to_datetime(df_3['fecha'])

            ###############
            fecha_hora = pd.to_datetime(fechacompleta)
            fechacompleta_adj = fecha_hora + timedelta(seconds=60)
            df_filt_con_inicio_call = df[(df['hora_inicio_call_center'].notna())]
            df_filt_con_inicio_call['hora_fin_call_center'] = df_filt_con_inicio_call['hora_fin_call_center'].fillna(fechacompleta_adj)
            ###############

            ###############
            df_activaciones = df_filt_con_inicio_call.copy()
            df_estado_agente = df_2.copy()
            df_nomina = df_3.copy()

            # Normalización de los nombres de columnas
            def normalize_column_name(col):
                col = unidecode(col)  
                col = col.strip().lower().replace(' ', '_')  
                return col

            franjas['Fecha_Hora_Inicio'] = pd.to_datetime(franjas['Fecha_Hora_Inicio'], format='%d-%m-%Y %H:%M:%S')
            franjas['Fecha_Hora_Fin'] = pd.to_datetime(franjas['Fecha_Hora_Fin'], format='%d-%m-%Y %H:%M:%S')
            franjas.columns = [normalize_column_name(col) for col in franjas.columns]

            # Filtrar del estado-agente los "SIGN ON" y RES RESUME"
            df_estado_agente_sig_on = df_estado_agente[df_estado_agente['funcion'] == 'SON - Sign On'].copy()
            df_estado_agente_res_resume = df_estado_agente[df_estado_agente['funcion'] == 'RES - RESUME'].copy()

            # Crear la columna total_sec calculando la diferencia en segundos
            df_estado_agente_res_resume['total_sec'] = (df_estado_agente_res_resume['hora_fin'] - df_estado_agente_res_resume['hora_inicio']).dt.total_seconds().astype('Int64')
            df_estado_agente_sig_on['total_sec'] = (df_estado_agente_sig_on['hora_fin'] - df_estado_agente_sig_on['hora_inicio']).dt.total_seconds().astype('Int64')

            # Filtrar solo los estado agente 'RES RESUME' que tengan más o igual a 30 segundos
            filtro_res_resume = df_estado_agente_res_resume[(df_estado_agente_res_resume['total_sec'] >= 30)]
            filtro_sig_on = df_estado_agente_sig_on[(df_estado_agente_sig_on['total_sec'] >= 30)]

            df_estado_agente_res_resume_filtro = filtro_res_resume.drop('total_sec', axis=1)
            df_estado_agente_sig_on_filtro = filtro_sig_on.drop('total_sec', axis=1)

            # Hacemos un merge de df1 con df2 basado en las columnas 'asesor' y 'fecha'
            filtro_res_resume_por_nomina = df_estado_agente_res_resume_filtro.merge(df_nomina, on=['codigo_salesys', 'fecha'])
            filtro_sig_on_por_nomina = df_estado_agente_sig_on_filtro.merge(df_nomina, on=['codigo_salesys', 'fecha'])

            def generar_tiempos_por_franja(df_agentes, df_franjas):
                resultados = []
                
                for _, agente_row in df_agentes.iterrows():
                    agente_inicio = agente_row['hora_inicio']
                    agente_fin = agente_row['hora_fin']
                    agente_fecha = agente_inicio.date()  # Extraer solo la fecha
                    codigo_salesys = agente_row['codigo_salesys']
                    agente_funcion = agente_row['funcion']

                    # Filtrar franjas por la fecha del agente
                    franjas_fecha = df_franjas[(df_franjas['fecha_hora_inicio'].dt.date == agente_fecha)]
                    
                    for _, franja_row in franjas_fecha.iterrows():
                        franja_inicio = franja_row['fecha_hora_inicio']
                        franja_fin = franja_row['fecha_hora_fin']
                        etiqueta_franja = franja_row['etiqueta_franja']
                        
                        # Encontrar la intersección entre el intervalo del agente y la franja
                        interseccion_inicio = max(agente_inicio, franja_inicio)
                        interseccion_fin = min(agente_fin, franja_fin)
                        
                        if interseccion_inicio < interseccion_fin:
                            # Calcular la duración en segundos
                            duracion_segundos = (interseccion_fin - interseccion_inicio).total_seconds()
                            
                            resultados.append({
                                'codigo_salesys': codigo_salesys,
                                'funcion': agente_funcion,
                                'fecha': agente_fecha,
                                'franja': etiqueta_franja,
                                'tiempo_segundos': duracion_segundos
                           })

                return pd.DataFrame(resultados)

            # Generar tiempos por franjas para cada registro 'SIG ON' y 'RES RESUME'
            df_resultado_sig_on = generar_tiempos_por_franja(filtro_sig_on_por_nomina, franjas)
            df_resultado_res_resume = generar_tiempos_por_franja(filtro_res_resume_por_nomina, franjas)

            # Concatenar ambos DFs que tienen solo el estado agente 'SIG ON' y 'RES RESUME'
            df_consolidado = pd.concat([df_resultado_sig_on, df_resultado_res_resume])
            df_consolidado['fecha'] = pd.to_datetime(df_consolidado['fecha'])

            df_activaciones['codigo_salesys'] = df_activaciones['codigo_salesys'].astype('Int64')

            # Agrupamos por 'codigo_salesys', 'funcion', 'fecha', y 'franja', y sumamos el tiempo en segundos
            df_consolidado_agrupado = df_consolidado.groupby(['codigo_salesys', 'funcion', 'fecha', 'franja']).agg({'tiempo_segundos': 'sum'}).reset_index()

            # Cambiar los registros de la columna función por 'DISPONIBLE'
            df_consolidado_agrupado['funcion'] = 'DISPONIBLE'  # Puedes usar cualquier etiqueta común

            # Agrupar por agente, fecha, franja y sumar los tiempos
            df_consolidado_final = df_consolidado_agrupado.groupby(['fecha', 'codigo_salesys', 'franja']).agg({'tiempo_segundos': 'sum'}).reset_index()
            df_consolidado_final['tiempo_segundos'] = df_consolidado_final['tiempo_segundos'].astype('Int64')

            # Realizar el merge y seleccionar solo las columnas deseadas del DataFrame secundario
            es_agente_nomina = pd.merge(
                df_consolidado_final,
                df_nomina[['fecha', 'codigo_salesys', 'nombre', 'condicion', 'cargo', 'campana']],  # Seleccionar columnas deseadas
                on=['fecha', 'codigo_salesys'],
                how='left')

            # Ordenar columnas de la tabla generada del merge
            columnas_agen_nom = ['fecha', 'codigo_salesys', 'nombre', 'condicion', 'cargo', 'campana', 'franja', 'tiempo_segundos']
            es_agente_nomina_select = es_agente_nomina[columnas_agen_nom]
            es_agente_nomina_select['codigo_salesys'] = es_agente_nomina_select['codigo_salesys'].astype('Int64')

            # Ordenar columnas de la tabla validaciones
            columnas_validaciones = ['asesor', 'codigo_salesys', 'hora_inicio_call_center', 'hora_fin_call_center']
            df_activaciones_select2 = df_activaciones[columnas_validaciones]

            # Función para dividir gestiones por franjas y calcular tiempo en cada una
            def mapear_segundos_por_franja(df_gestiones, df_franjas):
                registros = []

                for index, row in df_gestiones.iterrows():
                    hora_inicio = row['hora_inicio_call_center']
                    hora_fin = row['hora_fin_call_center']

                    # Filtrar franjas que intersectan con la gestión
                    franjas_intersectadas = df_franjas[(df_franjas['fecha_hora_inicio'] < hora_fin) & (df_franjas['fecha_hora_fin'] > hora_inicio)]

                    for _, franja in franjas_intersectadas.iterrows():
                        inicio_franja = max(hora_inicio, franja['fecha_hora_inicio'])
                        fin_franja = min(hora_fin, franja['fecha_hora_fin'])
                        tiempo_segundos = (fin_franja - inicio_franja).total_seconds()

                        registros.append({
                            'codigo_salesys': row['codigo_salesys'],
                            'fecha': hora_inicio.date(),
                            'franja': franja['etiqueta_franja'],
                            'tiempo_segundos': tiempo_segundos
                        })

                return pd.DataFrame(registros)

            # Asignar tiempos por cada franja que le corresponde según la hora
            df_resultado = mapear_segundos_por_franja(df_activaciones_select2, franjas)

            # Confirmar el tipo de dato de la columna fecha a 'datetime'
            df_resultado['fecha'] = pd.to_datetime(df_resultado['fecha'])

            # Convertir la columna 'tiempo_segundos' a entero
            df_resultado['tiempo_segundos'] = df_resultado['tiempo_segundos'].astype('int64')

            # Agrupar por franja y sumar los tiempos
            df_agrupado = df_resultado.groupby(['fecha', 'codigo_salesys', 'franja']).agg({'tiempo_segundos': 'sum'}).reset_index()

            df_agrupado_2 = df_agrupado.rename(columns={'tiempo_segundos': 'segundos_gestionados'})
            df_agrupado_2['codigo_salesys'] = df_agrupado_2['codigo_salesys'].astype('Int64')

            # Realizar el merge y seleccionar solo las columnas deseadas del DataFrame secundario
            df_agrupado_final = pd.merge(
                df_agrupado_2,
                df_nomina[['fecha', 'codigo_salesys', 'nombre']],  # Seleccionar columnas deseadas
                on=['fecha', 'codigo_salesys'],
                how='left')

            # Renombrar columna, para diferenciar a que tiempo se refiere
            es_agente_nomina_select = es_agente_nomina_select.rename(columns={'tiempo_segundos': 'segundos_disponible'})

            # Realizar el merge y seleccionar solo las columnas deseadas del DataFrame secundario
            ocupacion_final = pd.merge(
                es_agente_nomina_select,
                df_agrupado_final[['fecha', 'codigo_salesys', 'franja', 'segundos_gestionados']],  # Seleccionar columnas deseadas
                on=['fecha', 'codigo_salesys', 'franja'],
                how='left')

            franjas['fecha_hora_inicio'] = pd.to_datetime(franjas['fecha_hora_inicio'], format='%d-%m-%Y %H:%M:%S')
            franjas['fecha'] = franjas['fecha_hora_inicio'].dt.date
            franjas['hora_inicio'] = franjas['fecha_hora_inicio'].dt.time
            franjas['fecha'] = pd.to_datetime(franjas['fecha'])
            franjas = franjas.rename(columns={'etiqueta_franja': 'franja'})

            # Realizar el merge y seleccionar solo las columnas deseadas del DataFrame secundario
            df_agrupado_final_franjas = pd.merge(
                ocupacion_final,
                franjas[['fecha', 'franja', 'hora_inicio']],  # Seleccionar columnas deseadas
                on=['fecha','franja'],
                how='left')

            df_to_sql = df_agrupado_final_franjas.rename(columns={'hora_inicio': 'rango_15min'})

            # Eliminar registros existentes de la misma fecha en la base de datos
            with engine.connect() as connection:
                delete_query = text(f"DELETE FROM Tbl_Ocupacion_Activaciones WHERE fecha = '{fecha}'")
                connection.execute(delete_query)
                connection.execute(text("COMMIT"))
                log(f"Registros eliminados de la base de datos fecha: {fecha}.")
                
            #Cargar los datos combinados a la base de datos
            with engine.connect() as connection:
                df_to_sql.to_sql('Tbl_Ocupacion_Activaciones', con=connection, if_exists='append',index=False)
                connection.execute(text("COMMIT"))
            log(f"Datos cargados exitosamente en la base de datos ({len(df_to_sql)} registros).")
            
        except Exception as e:
            log(f"[ERROR] Error procesando fecha {fecha}: {e}")
            continue

if __name__ == "__main__":
    # Leer fecha/hora compartida desde archivo
    with open("shared_timestamp.txt", "r") as f:
        fecha_hora = f.read().strip()
    
    fechacompleta = pd.to_datetime(fecha_hora)
    fechas = [fechacompleta.strftime("%Y-%m-%d")]
    
    procesar_ocupacion_activaciones(fechas)