# config/form_routes.py

import yaml
from pathlib import Path

FORM_ROUTES = yaml.safe_load(
    Path(__file__).with_suffix(".yaml").read_text(encoding="utf-8")
)