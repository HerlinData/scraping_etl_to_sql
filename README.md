# 🤖 ScrapeBot - Sistema de Scraping Automatizado

Sistema automatizado para extraer reportes operativos del sistema SalesYs de telecomunicaciones.

## 🚀 Ejecución Rápida

```bash
# Ejecutar sistema principal
python main.py

# Ver dashboard de monitoreo
python dashboard.py

# Ver estado del sistema
python scripts/status_check.py

# Consultar base de datos
python utils/db_viewer.py
```

## ⏰ Horarios de Ejecución

El sistema se ejecuta automáticamente cada hora desde las **10:50** hasta las **18:50**:
- 10:50, 11:50, 12:50, 13:50, 14:50, 15:50, 16:50, 17:50, 18:50

## 📊 Módulos de Scraping

1. **RGA** - Registro General de Averías
2. **Estado Agente v2** - Performance del personal
3. **Nómina** - Datos de personal
4. **EA Corte** - Cortes de servicios
5. **Delivery Cortes** - Entregas y cortes
6. **Activaciones Cortes** - Altas/bajas de servicios
7. **Ocupación Activaciones** - Carga de trabajo

## 🔧 Configuración

1. **Crear archivo de configuración:**
   ```bash
   cp .env.example .env
   ```

2. **Editar credenciales en `.env`:**
   ```env
   SALESYS_USERNAME=tu_usuario
   SALESYS_PASSWORD=tu_password
   ```

3. **Instalar dependencias:**
   ```bash
   pip install python-dotenv
   ```

## 📈 Monitoreo

- **Dashboard Web:** `python dashboard.py` → http://localhost:8080
- **Base de datos:** SQLite en `logs/scraping_processes.db`
- **Logs:** Archivos diarios en `logs/`

## 📋 Documentación Completa

- **Guía de Deployment:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Sistema de Monitoreo:** [README_MONITORING.md](README_MONITORING.md)

## 🎯 Características

- ✅ **Ejecución automática** cada hora
- ✅ **Reintentos automáticos** ante fallos
- ✅ **Logs estructurados** y persistentes
- ✅ **Base de datos SQLite** para tracking
- ✅ **Dashboard web** de monitoreo
- ✅ **Alertas configurables** (email/Slack)
- ✅ **Credenciales seguras** en variables de entorno