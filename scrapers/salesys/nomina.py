import sys
sys.path.append('Z:\AMG Esuarezh\SysAnalistas')
from functools import partial  # Importamos partial
import flet as ft
from datetime import datetime,timedelta
import locale
locale.setlocale(locale.LC_TIME, 'Spanish_Spain')
########################################################################################################################
from funciones.conexion import *
from ejecutable_nomina.Campañas.Activaciones import *
from ejecutable_nomina.Campañas.Delivery_Bio_Mensajeria_Soporte import *
from ejecutable_nomina.Campañas.Delivery_Seguimiento import *
from ejecutable_nomina.Campañas.FotosAlambrico import *
from ejecutable_nomina.Campañas.FotosCorporativo import *
from ejecutable_nomina.Campañas.MesaDeAyuda import *
from ejecutable_nomina.Campañas.MesaDeSoporte import *
from ejecutable_nomina.Campañas.PlantaExternaMultiskill import *
from ejecutable_nomina.Campañas.ProgramacionFija import *
from ejecutable_nomina.Campañas.Validaciones import *
from ejecutable_nomina.Campañas.SeguimientoFija import *
from ejecutable_nomina.Campañas.Aghaso import *
from ejecutable_nomina.Campañas.SoporteVentaFibraFija import *
########################################################################################################################
from funciones.Nomina import *
from funciones.Nomina.ConsultasBD import *
########################################################################################################################
import datetime


def cargar_Nomina_actual():
    try:
        # Obtener fecha actual
        hoy = datetime.date.today()
        fecha_value = hoy.strftime("%Y-%m-%d")     # '2025-07-02'
        fecha_año_value = hoy.strftime("%Y")       # '2025'
        mes_value = hoy.strftime("%m")             # '07'
        fecha_dia_value = hoy.strftime("%d")       # '02'

        # Mes en español (opcional)
        meses_es = {
            "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
            "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
            "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
        }
        fecha_mes_value = meses_es[mes_value]

        print(f"🚀 Iniciando carga de nómina para: {fecha_value} ({fecha_mes_value})")

        # Lógica de carga
        CargaNominaValidaciones(fecha_value, fecha_año_value, mes_value)
        CargaNominaActivaciones(fecha_value, fecha_año_value, mes_value)
        CargaNominaDeliveryBioMensajeriaSoporte(fecha_value, fecha_año_value, mes_value)
        CargaNominaDeliverySeguimiento(fecha_value, fecha_año_value, mes_value)
        CargaNominaFotosAlambrico(fecha_value, fecha_año_value, mes_value)
        CargaNominaFotosCorporativo(fecha_value, fecha_año_value, mes_value)
        CargaNominaMesaDeAyuda(fecha_value, fecha_año_value, mes_value)
        CargaNominaMesaDeSoporte(fecha_value, fecha_año_value, mes_value)
        CargaNominaPlantaExternaMultiskill(fecha_value, fecha_año_value, mes_value)
        CargaNominaSeguimientoFija(fecha_value, fecha_año_value, mes_value)
        CargaNominaProgramacionFija(fecha_value, fecha_año_value, mes_value)
        CargaNominaAghaso(fecha_value, fecha_año_value, mes_value)
        CargaNominaSoporteVentaFibraFija(fecha_value, fecha_año_value, mes_value)

        print(f"✅ Carga de nómina finalizada para: {fecha_value}")

    except Exception as e:
        print(f"❌ Error al ejecutar la carga de nómina: {str(e)}")

cargar_Nomina_actual()