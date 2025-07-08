import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoAlertPresentException
from config.form_routes import FORM_ROUTES
from config.settings import SALESYS_USERNAME, SALESYS_PASSWORD, MESES_ES, MAX_LOGIN_ATTEMPTS, LOGIN_URL
from core.utils import limpiar_temp, esperar_archivo, renombrar_archivo
from core.login import salesys_login

TEMP_FOLDER = r"Z:\AMG Esuarezh\scraping\temp"

def descargar_estado_agente(
    fechas,
    ruta_base=r"Z:\\DESCARGA INFORMES",
    temp_folder=TEMP_FOLDER,
    log_fn=None
):
    def log(msg):
        if log_fn:
            log_fn(msg)
        else:
            print(msg)

    limpiar_temp(temp_folder)

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
    prefs = {
        "download.default_directory": temp_folder,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": False,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    options.add_experimental_option("prefs", prefs)

    form_name = "estado_agente_v2"
    form_config = FORM_ROUTES[form_name]
    FORM_URL = form_config["form_url"]

    driver = webdriver.Chrome(options=options)
    try:
        login_ok = False
        for attempt in range(MAX_LOGIN_ATTEMPTS):
            log(f"Intento de login #{attempt+1}")
            login_ok = salesys_login(driver, LOGIN_URL, SALESYS_USERNAME, SALESYS_PASSWORD, log=log)
            if not login_ok:
                continue
            # Abre el form
            driver.execute_script(f"window.open('{FORM_URL}');")
            WebDriverWait(driver, 30).until(lambda d: len(d.window_handles) > 1)
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(FORM_URL)
            WebDriverWait(driver, 8).until(lambda d: d.current_url.startswith("http"))
            if driver.current_url.lower().startswith(FORM_URL.lower()):
                log("[SUCCESS] Login exitoso y en formulario correcto.")
                login_ok = True
                break
            else:
                log(f"[WARNING]  No se llegó al formulario, url actual: {driver.current_url}")
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                login_ok = False
        if not login_ok:
            driver.quit()
            raise Exception("No se pudo ingresar al formulario tras 3 intentos.")

        for fecha in fechas:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d") if isinstance(fecha, str) else fecha
            anio = fecha_dt.year
            mes_nombre = MESES_ES[fecha_dt.month]
            dia = fecha_dt.strftime('%d')
            fecha_sistema = fecha_dt.strftime('%Y/%m/%d')

            log(f"\n[SCHEDULE] ==== Fecha: {fecha} ====")
            res = {'status': None, 'mensaje': ''}
            try:
                driver.switch_to.window(driver.window_handles[1])
                # 1. LLENAR FECHAS
                fecha_from = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "from"))
                )
                fecha_from.clear()
                fecha_from.send_keys(fecha_sistema)
                fecha_to = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "to"))
                )
                fecha_to.clear()
                fecha_to.send_keys(fecha_sistema)

                # Ocultar calendario flotante
                for _ in range(3):
                    try:
                        calendar = WebDriverWait(driver, 1).until(
                            EC.visibility_of_element_located((By.CLASS_NAME, "ui-datepicker"))
                        )
                        driver.execute_script("arguments[0].style.display = 'none';", calendar)
                        WebDriverWait(driver, 1).until_not(
                            EC.visibility_of_element_located((By.CLASS_NAME, "ui-datepicker"))
                        )
                        break
                    except TimeoutException:
                        break

                # 2. Click en el botón "Submit" para generar el reporte
                WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.ID, "subreport"))
                ).click()
                
                # 3. Esperar y cambiar a la pestaña de descarga
                t5b_start = time.time()
                timeout_new_tab = 30
                while len(driver.window_handles) <= 2 and time.time() - t5b_start < timeout_new_tab:
                    WebDriverWait(driver, 2).until(lambda d: True)
                if len(driver.window_handles) > 2:
                    driver.switch_to.window(driver.window_handles[-1])
                else:
                    raise TimeoutException("No se abrió la pestaña de resultados en tiempo")
                # --- DETECCIÓN de "No data found" en el popup ---
                regresar_a_form = False
                try:
                    popup = WebDriverWait(driver, 4).until(
                        EC.presence_of_element_located((By.ID, "MGSJE"))
                    )
                    if "no data found" in popup.text.lower():
                        log(f"[ESTADO AGENTE] [WARNING] No data found (en popup #MGSJE): Saltando directo al formulario.")
                        res['status'] = "no_data"
                        res['mensaje'] = "No data found"
                        regresar_a_form = True
                except TimeoutException:
                    regresar_a_form = False
                # --- DETECCIÓN Y CIERRE DEL POP-UP JS ---
                if not regresar_a_form:
                    pop_up_detectado = False
                    for _ in range(10):
                        try:
                            alert = driver.switch_to.alert
                            alert_text = alert.text
                            alert.accept()
                            log(f"[ESTADO AGENTE] [WARNING] Pop-up detectado y cerrado: '{alert_text}'. Sin data, saltando directo al formulario.")
                            pop_up_detectado = True
                            res['status'] = "popup"
                            res['mensaje'] = f"Pop-up cerrado: {alert_text}"
                            break
                        except Exception:
                            time.sleep(0.2)
                    if not pop_up_detectado:
                        # --- DESCARGA NORMAL SI TODO LO DEMÁS FALLA ---
                        try:
                            elem_descarga = WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable((By.CLASS_NAME, "download"))
                            )
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem_descarga)
                            elem_descarga.click()
                            log("Clic en botón de descarga enviado.")
                            # ESPERAR ARCHIVO SOLO .csv
                            descarga_start = time.time()
                            archivo_descargado = esperar_archivo(temp_folder, descarga_start, ext=".csv", timeout=30)
                            if archivo_descargado:
                                ext = os.path.splitext(archivo_descargado)[1]
                                nuevo_nombre = f"EstadoAgente{dia}{ext}"
                                old_path = os.path.join(temp_folder, archivo_descargado)
                                new_path = os.path.join(temp_folder, nuevo_nombre)
                                if not renombrar_archivo(old_path, new_path):
                                    res['status'] = "error"
                                    res['mensaje'] = f"No se pudo renombrar el archivo '{archivo_descargado}'."
                                    log(f"[ESTADO AGENTE] [WARNING] {res['mensaje']}")
                                    continue
                                # Lógica de rutas desde YAML (rutas, no archivos)
                                tpl_list = form_config.get("rutas", [])
                                destinos = [
                                    Path(ruta_base) / tpl.format(year=anio, month=mes_nombre) / nuevo_nombre
                                    for tpl in tpl_list
                                ]
                                for dest in destinos:
                                    dest.parent.mkdir(parents=True, exist_ok=True)
                                    os.replace(new_path, dest)
                                    log(f"[ESTADO AGENTE] Archivo movido a: {dest}")
                                res['status'] = "descargado"
                                res['mensaje'] = f"Movido a {tpl_list}"
                            else:
                                res['status'] = "no_descarga"
                                res['mensaje'] = "Descarga NO detectada en tiempo"
                                log(f"[ESTADO AGENTE] {res['mensaje']}")
                        except TimeoutException:
                            res['status'] = "no_descarga"
                            res['mensaje'] = "No apareció el botón de descarga ni 'no data found', revisar manualmente."
                            log(f"[ESTADO AGENTE] {res['mensaje']}")
                # --- Regresa al formulario ---
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[1])
                else:
                    log("No queda pestaña de formulario. Terminando bucle.")
            except Exception as e:
                res['status'] = "error"
                res['mensaje'] = f"Excepción general: {e}"
                log(f"[ESTADO AGENTE] [ERROR] {e}")

        driver.quit()
    except Exception as e:
        driver.quit()
        print(f"Error general: {e}")

if __name__ == "__main__":
    fechas = [datetime.now().strftime("%Y-%m-%d")]
    # Descargar todos los tipos de reporte
    descargar_estado_agente(fechas)