import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Credenciales - OBLIGATORIAS desde variables de entorno
SALESYS_USERNAME = os.getenv('SALESYS_USERNAME')
SALESYS_PASSWORD = os.getenv('SALESYS_PASSWORD')

if not SALESYS_USERNAME or not SALESYS_PASSWORD:
    raise ValueError("SALESYS_USERNAME y SALESYS_PASSWORD deben estar definidas en .env")

# URLs de login y formularios
LOGIN_URL = "http://amgclaro.touscorp.com/SaleSys/index.php/config"
# (los formularios concretos se definen en form_routes.yaml)

# Carpetas
BASE_DOWNLOAD_PATH = Path(r"Z:/DESCARGA INFORMES")
TEMP_DOWNLOAD_DIR  = Path(r"Z:/AMG Esuarezh/scraping/temp")

# Parámetros generales
MAX_LOGIN_ATTEMPTS  = 3
PRODUCTOS_DEFAULT  = ["LTE", "HFC", "EMPRESA", "FTTH", "OTROS", "DELIVERY"]
MESES_ES = {
    1:"ENERO", 2:"FEBRERO", 3:"MARZO", 4:"ABRIL",
    5:"MAYO", 6:"JUNIO", 7:"JULIO", 8:"AGOSTO",
    9:"SEPTIEMBRE",10:"OCTUBRE",11:"NOVIEMBRE",12:"DICIEMBRE"
}