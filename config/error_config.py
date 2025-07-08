# Configuración para manejo de errores y recuperación

import os
from pathlib import Path

# Configuración de reintentos
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', 60))  # segundos

# Timeouts (en segundos)
MODULE_TIMEOUT = int(os.getenv('MODULE_TIMEOUT', 1800))  # 30 minutos
LOGIN_TIMEOUT = int(os.getenv('LOGIN_TIMEOUT', 300))     # 5 minutos
DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', 600)) # 10 minutos

# Configuración de logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', 30))

# Configuración de recuperación ante fallos
CRITICAL_MODULES = [
    'scrapers.salesys.rga',
    'scrapers.salesys.estado_agente_v2'
]

# Si estos módulos críticos fallan, el sistema puede pausar
PAUSE_ON_CRITICAL_FAILURE = os.getenv('PAUSE_ON_CRITICAL_FAILURE', 'false').lower() == 'true'
CRITICAL_FAILURE_DELAY = int(os.getenv('CRITICAL_FAILURE_DELAY', 3600))  # 1 hora

# Configuración de alertas (para futuras implementaciones)
ENABLE_EMAIL_ALERTS = os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true'
ALERT_EMAIL = os.getenv('ALERT_EMAIL', '')

# Configuración de métricas
METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
METRICS_FILE = Path(os.getenv('METRICS_FILE', 'logs/metrics.json'))

# Configuración de limpieza automática
AUTO_CLEANUP_TEMP = os.getenv('AUTO_CLEANUP_TEMP', 'true').lower() == 'true'
TEMP_CLEANUP_HOURS = int(os.getenv('TEMP_CLEANUP_HOURS', 24))