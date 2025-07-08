# core/utils.py

import os
import shutil
from pathlib import Path
import time

def limpiar_temp(temp_folder):
    """Elimina archivos temporales (.crdownload/.tmp) en la carpeta."""
    os.makedirs(temp_folder, exist_ok=True)
    for nombre in os.listdir(temp_folder):
        if nombre.endswith(".crdownload") or nombre.endswith(".tmp"):
            try:
                os.remove(os.path.join(temp_folder, nombre))
            except Exception:
                pass

def esperar_archivo(temp_folder, start_time, ext=".csv", timeout=30):
    """Espera un archivo de cierta extensión en la carpeta, máximo 'timeout' segundos."""
    elapsed = 0
    archivo = None
    while elapsed < timeout:
        for nombre in os.listdir(temp_folder):
            ruta = os.path.join(temp_folder, nombre)
            if (
                os.path.isfile(ruta)
                and nombre.lower().endswith(ext)
                and os.path.getmtime(ruta) >= start_time
            ):
                archivo = nombre
                return archivo
        time.sleep(0.5)
        elapsed += 0.5
    return None

def renombrar_archivo(origen, destino):
    """Renombra/mueve un archivo, maneja errores de permisos."""
    intentos = 6
    for _ in range(intentos):
        try:
            if origen != destino:
                if os.path.exists(destino):
                    os.remove(destino)
                os.rename(origen, destino)
            return True
        except PermissionError:
            time.sleep(0.5)
    return False

def mover_a_destinos(path_temp, rutas_destino):
    """Mueve el archivo desde temp a todas las rutas destino (crea carpetas)."""
    for destino in rutas_destino:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path_temp), str(destino))