import yaml
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from config.settings import *
from config.form_routes import FORM_ROUTES  # ver abajo
from core.utils import clear_temp_folder, wait_for_csv, move_file

class BaseScraper:
    def __init__(self):
        self.temp_dir = TEMP_DOWNLOAD_DIR
        clear_temp_folder(self.temp_dir)
        opts = Options()
        opts.add_argument("--disable-gpu")
        opts.add_argument(f"--window-size=1920,1080")
        prefs = {"download.default_directory": str(self.temp_dir),
                 "download.prompt_for_download": False,
                 "directory_upgrade": True,
                 "safebrowsing.enabled": False,
                 "profile.default_content_setting_values.automatic_downloads": 1}
        opts.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Chrome(options=opts)
        # cargo rutas de YAML
        self.form_routes = yaml.safe_load(
            Path(__file__).parent.parent / 'config' / 'form_routes.yaml'
        )

    def login(self):
        raise NotImplementedError

    def download_for_date(self, fecha):
        raise NotImplementedError

    def run(self, fechas):
        try:
            self.login()
            for f in fechas:
                self.download_for_date(f)
        finally:
            self.driver.quit()