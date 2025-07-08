# core/login.py

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def salesys_login(driver, login_url, username, password, extension="4271", device="PC4271", log=print):
    """
    Realiza el login en Salesys y deja el driver logueado y posicionado en la pestaña de formulario.
    Devuelve True si fue exitoso, False si no.
    """
    try:
        driver.get(login_url)
        driver.find_element(By.ID, "extension").clear()
        driver.find_element(By.ID, "extension").send_keys(extension)
        driver.find_element(By.ID, "deviceName").clear()
        driver.find_element(By.ID, "deviceName").send_keys(device)
        driver.find_element(By.ID, "submitButton").click()
        driver.find_element(By.ID, "slt-userName").clear()
        driver.find_element(By.ID, "slt-userName").send_keys(username)
        driver.find_element(By.ID, "slt-userPass").clear()
        driver.find_element(By.ID, "slt-userPass").send_keys(password)
        driver.find_element(By.XPATH, "//input[@type='submit']").click()
        time.sleep(2.2)
        driver.refresh()
        time.sleep(1.1)
        return True
    except Exception as e:
        log(f"[LOGIN] ❌ Error en login: {e}")
        return False