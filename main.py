import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from core.metrics import metrics_collector, start_session, finish_session, start_module, finish_module
from core.alerts import alert_manager
from core.database import process_db

# Configurar logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configurar handler para archivo (con emojis)
file_handler = logging.FileHandler(
    log_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log",
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Configurar handler para consola (sin emojis)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formateador para archivo (con emojis)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Formateador para consola (sin emojis)
class NoEmojiFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        # Reemplazar emojis con texto
        emoji_replacements = {
            '🏁': '[START]',
            '📅': '[SCHEDULE]',
            '⏰': '[TIME]',
            '📊': '[METRICS]',
            '🚀': '[LAUNCH]',
            '✅': '[SUCCESS]',
            '❌': '[ERROR]',
            '💥': '[CRASH]',
            '🔄': '[RETRY]',
            '🎯': '[COMPLETE]',
            '⚠️': '[WARNING]',
            '🛑': '[STOP]',
            '🎉': '[CELEBRATION]'
        }
        for emoji, replacement in emoji_replacements.items():
            msg = msg.replace(emoji, replacement)
        return msg

console_formatter = NoEmojiFormatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Configurar logger principal
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Horas objetivo: cada hora desde 10:50 hasta 18:50
horas_objetivo = [f"{hour}:50" for hour in range(10, 19)]  # 10:50, 11:50, ..., 18:50
ejecutadas_hoy = set()

# Configuración de retry
MAX_RETRIES = 3
RETRY_DELAY = 60  # segundos entre reintentos
MODULE_TIMEOUT = 1800  # 30 minutos timeout por módulo

def generar_timestamp_compartido():
    """Genera un archivo con la fecha/hora actual para sincronizar los módulos."""
    try:
        fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open("shared_timestamp.txt", "w") as f:
            f.write(fecha_hora)
        logger.info(f"Timestamp compartido generado: {fecha_hora}")
        return True
    except Exception as e:
        logger.error(f"Error generando timestamp: {e}")
        return False

def ejecutar_modulo_con_retry(module_name, session_id, max_retries=MAX_RETRIES):
    """Ejecuta un módulo con reintentos automáticos, métricas y tracking en BD."""
    module_metrics = start_module(module_name)
    process_db.start_module(session_id, module_name)
    last_error = None
    output_log = ""
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[{attempt}/{max_retries}] Ejecutando módulo: {module_name}")
            
            result = subprocess.run(
                ['python', '-m', module_name], 
                check=True,
                timeout=MODULE_TIMEOUT,
                capture_output=True,
                text=True
            )
            
            logger.info(f"✅ Módulo {module_name} completado exitosamente")
            output_log = result.stdout.strip() if result.stdout else ""
            
            if result.stdout:
                logger.debug(f"Salida de {module_name}: {output_log}")
            
            # Registrar éxito en métricas y BD
            finish_module(module_name, "success")
            process_db.finish_module(session_id, module_name, "success", attempt, output_log=output_log)
            
            # Si se recuperó después de fallos previos, enviar alerta de recuperación
            if attempt > 1:
                alert_manager.send_system_recovery_alert(module_name)
            
            return True
            
        except subprocess.TimeoutExpired as e:
            last_error = f"Timeout después de {MODULE_TIMEOUT}s"
            logger.error(f"⏰ Timeout en módulo {module_name} (intento {attempt}/{max_retries})")
            metrics_collector.record_error(module_name, last_error)
            
            if attempt < max_retries:
                logger.info(f"Reintentando en {RETRY_DELAY} segundos...")
                time.sleep(RETRY_DELAY)
                
        except subprocess.CalledProcessError as e:
            last_error = f"Exit code {e.returncode}: {e.stderr.strip() if e.stderr else 'Unknown error'}"
            output_log = e.stderr.strip() if e.stderr else ""
            logger.error(f"❌ Error en módulo {module_name} (intento {attempt}/{max_retries}): {e}")
            if e.stderr:
                logger.error(f"Error detallado: {e.stderr.strip()}")
            
            metrics_collector.record_error(module_name, last_error)
            
            if attempt < max_retries:
                logger.info(f"Reintentando en {RETRY_DELAY} segundos...")
                time.sleep(RETRY_DELAY)
                
        except Exception as e:
            last_error = f"Error inesperado: {str(e)}"
            output_log = str(e)
            logger.error(f"💥 Error inesperado en módulo {module_name}: {e}")
            metrics_collector.record_error(module_name, last_error)
            
            if attempt < max_retries:
                logger.info(f"Reintentando en {RETRY_DELAY} segundos...")
                time.sleep(RETRY_DELAY)
    
    logger.error(f"🚫 Módulo {module_name} falló después de {max_retries} intentos")
    
    # Registrar fallo en métricas y BD
    finish_module(module_name, "failed")
    process_db.finish_module(session_id, module_name, "failed", max_retries, 
                            error_message=last_error, output_log=output_log)
    
    # Enviar alerta de fallo crítico
    alert_manager.send_module_failure_alert(module_name, last_error or "Unknown error", max_retries)
    
    return False

def ejecutar_todos_scripts(session_id):
    """Ejecutar scripts como módulos con manejo robusto de errores."""
    modules = [
        'scrapers.salesys.rga',
        'scrapers.salesys.estado_agente_v2',
        'scrapers.salesys.nomina',
        'scrapers.salesys.ea_corte',
        'scrapers.salesys.delivery_cortes',
        'scrapers.salesys.activaciones_cortes',
        'scrapers.salesys.ocupacion_activaciones'
    ]

    exitosos = []
    fallidos = []
    
    logger.info(f"🚀 Iniciando ejecución de {len(modules)} módulos")
    
    for module in modules:
        if ejecutar_modulo_con_retry(module, session_id):
            exitosos.append(module)
        else:
            fallidos.append(module)
            # Continuar con el siguiente módulo incluso si este falló
            logger.warning(f"⚠️ Continuando con el siguiente módulo tras fallo de {module}")
    
    # Resumen final
    logger.info(f"📊 Resumen de ejecución:")
    logger.info(f"✅ Exitosos ({len(exitosos)}): {exitosos}")
    if fallidos:
        logger.warning(f"❌ Fallidos ({len(fallidos)}): {fallidos}")
    else:
        logger.info("🎉 Todos los módulos ejecutados exitosamente")
    
    return len(exitosos), len(fallidos)

if __name__ == "__main__":
    logger.info("🏁 Iniciando sistema de scraping automatizado")
    logger.info(f"📅 Horas programadas: {horas_objetivo}")
    
    try:
        while True:
            ahora = datetime.now()
            hora_actual = ahora.strftime("%H:%M")

            if hora_actual in horas_objetivo and hora_actual not in ejecutadas_hoy:
                logger.info(f"⏰ [{hora_actual}] Hora programada detectada. Iniciando ejecución...")

                # 🕒 Generar timestamp compartido antes de ejecutar los módulos
                if not generar_timestamp_compartido():
                    logger.error("❌ Error generando timestamp. Saltando ejecución.")
                    continue

                # 🚀 Ejecutar los módulos
                try:
                    session_id = start_session()
                    logger.info(f"📊 Iniciando sesión de métricas: {session_id}")
                    
                    # Registrar sesión en base de datos
                    process_db.start_session(session_id)
                    
                    exitosos, fallidos = ejecutar_todos_scripts(session_id)
                    
                    if fallidos == 0:
                        logger.info(f"🎯 Ejecución completa exitosa a las {hora_actual}")
                        finish_session("success")
                        process_db.finish_session(session_id, "success", f"Todos los módulos ejecutados correctamente")
                    else:
                        logger.warning(f"⚠️ Ejecución parcial: {exitosos} exitosos, {fallidos} fallidos")
                        finish_session("partial_success")
                        process_db.finish_session(session_id, "partial_success", f"{fallidos} módulos fallaron")
                        
                    # Enviar resumen si hay fallos
                    if fallidos > 0:
                        current_metrics = metrics_collector.get_current_metrics()
                        if current_metrics:
                            alert_manager.send_daily_summary_alert({
                                'modules': [
                                    {'name': m.module_name, 'success': m.status == 'success', 'downloads': m.downloads_successful}
                                    for m in current_metrics.modules
                                ],
                                'successful_modules': exitosos,
                                'failed_modules': fallidos
                            })
                        
                except Exception as e:
                    logger.error(f"💥 Error crítico durante ejecución: {e}")
                    finish_session("error")
                    if 'session_id' in locals():
                        process_db.finish_session(session_id, "error", f"Error crítico: {str(e)}")

                ejecutadas_hoy.add(hora_actual)

            # Reset diario de ejecuciones
            if hora_actual == "00:00":
                logger.info("🔄 Nuevo día: reseteando registro de ejecuciones")
                ejecutadas_hoy.clear()

            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("🛑 Deteniendo sistema por solicitud del usuario")
    except Exception as e:
        logger.error(f"💀 Error crítico en bucle principal: {e}")
        logger.info("🔄 Reiniciando en 60 segundos...")
        time.sleep(60)
