# 📊 Sistema de Logging y Monitoreo

## Características Implementadas

### ✅ **Logging Estructurado**
- **Logs por módulo** en `logs/modulo_YYYYMMDD.log`
- **Niveles apropiados**: DEBUG, INFO, WARNING, ERROR
- **Contexto estructurado** con session_id y metadatos
- **Rotación diaria** automática

### 🚨 **Sistema de Alertas Multi-Canal**
- **Email**: SMTP configurable (Gmail, Outlook, etc.)
- **Slack**: Webhooks con formato rich
- **Webhook genérico**: Para integraciones personalizadas
- **Throttling**: Evita spam de alertas
- **Alertas automáticas** para fallos críticos y recuperaciones

### 📈 **Métricas y Tracking**
- **Métricas por sesión** y por módulo
- **Rates de éxito** de descargas y módulos
- **Duración** de ejecuciones
- **Historial** persistente en JSON
- **Reportes automáticos** de resumen

### 🌐 **Dashboard Web**
- **Interfaz visual** en `http://localhost:8080`
- **Estado en tiempo real** del sistema
- **Métricas históricas** últimos 7 días
- **Prueba de alertas** integrada
- **Auto-refresh** cada 30 segundos

### 🔍 **Health Checks**
- **Script de verificación** de estado del sistema
- **Validación** de archivos críticos
- **Exit codes** para integración con monitoreo externo
- **Formato JSON** para APIs

## Configuración

### 1. **Alertas por Email**
```bash
# En tu archivo .env
ENABLE_EMAIL_ALERTS=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password  # App Password de Gmail
FROM_EMAIL=tu_email@gmail.com
ALERT_EMAILS=admin@empresa.com,it@empresa.com
```

### 2. **Alertas por Slack**
```bash
# En tu archivo .env
ENABLE_SLACK_ALERTS=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#alerts
SLACK_USERNAME=ScrapeBot
```

### 3. **Webhook Personalizado**
```bash
# En tu archivo .env
ENABLE_WEBHOOK_ALERTS=true
WEBHOOK_URL=https://your-monitoring-system.com/webhook
```

## Uso

### **Iniciar Dashboard**
```bash
cd monitoring
python dashboard.py
```
- Se abre automáticamente en http://localhost:8080
- Muestra estado actual y métricas históricas
- Permite probar configuración de alertas

### **Verificar Estado del Sistema**
```bash
# Verificación rápida
python scripts/status_check.py

# Salida JSON para scripts
python scripts/status_check.py --json

# Solo health check (útil para monitoreo externo)
python scripts/status_check.py --health-only
```

### **Usar Logger en Scrapers**
```python
from core.logger import get_logger

# En tu scraper
logger = get_logger(__name__)

logger.info("Iniciando proceso")
logger.login_attempt(1, 3)
logger.download_started("archivo.csv", "2024-01-15")
logger.download_success("archivo.csv", 1024)
logger.session_summary()  # Al final
```

## Integración con Scrapers Existentes

### **Reemplazar prints con logging estructurado**
```python
# ❌ Antes
print(f"Descargando archivo para {fecha}")

# ✅ Ahora
logger.download_started(filename, fecha)
```

### **Métricas automáticas**
```python
from core.metrics import start_module, finish_module

# Al inicio del scraper
start_module("mi_scraper")

# Al final (automático en main.py)
finish_module("mi_scraper", "success")
```

## Tipos de Alertas

### **Automáticas**
- ✅ **Fallo de módulo** después de todos los reintentos
- ✅ **Recuperación** cuando un módulo vuelve a funcionar
- ✅ **Resumen diario** si hay fallos
- ✅ **Resumen semanal** los domingos

### **Manuales**
- 🧪 **Prueba de alertas** desde dashboard
- 📊 **Reportes bajo demanda** con status_check.py

## Archivos de Log

### **Estructura**
```
logs/
├── scraper_20240115.log          # Log principal diario
├── scrapers.salesys.rga_20240115.log    # Log por módulo
├── metrics.json                   # Métricas históricas
└── alerts_history.json           # Historial de alertas
```

### **Formato de Log**
```
2024-01-15 10:30:15 - scrapers.salesys.rga - INFO - [20240115_103000] - ✅ Descarga exitosa: reporte.csv
```

## Monitoreo Externo

### **Health Check Endpoint**
```bash
# Para integrar con sistemas como Nagios, Zabbix, etc.
python scripts/status_check.py --health-only --json
echo $?  # 0 = healthy, 1 = degraded/unhealthy, 2 = error
```

### **Métricas Prometheus** (Future)
El sistema está preparado para exportar métricas a Prometheus agregando un endpoint `/metrics`.

## Troubleshooting

### **No llegan alertas por email**
1. Verificar App Password en Gmail (no usar contraseña normal)
2. Confirmar SMTP_SERVER y SMTP_PORT
3. Probar con dashboard: botón "Enviar Alerta de Prueba"

### **Dashboard no se conecta**
1. Puerto 8080 ocupado → cambiar puerto en dashboard.py
2. Firewall → permitir tráfico local en puerto 8080

### **Métricas no se guardan**
1. Verificar permisos de escritura en carpeta `logs/`
2. Verificar espacio en disco

El sistema ahora tiene **visibilidad completa** de su operación y **alertas proactivas** para problemas críticos.