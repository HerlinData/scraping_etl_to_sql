"""
Sistema de alertas para notificar fallos críticos
"""
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import os

# Importaciones de email solo si están disponibles
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    print("⚠️ Alertas por email no disponibles - falta configuración de email")

class AlertManager:
    """Gestor de alertas multi-canal."""
    
    def __init__(self):
        self.config = self._load_config()
        self.alert_history = []
        
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración de alertas."""
        return {
            'email': {
                'enabled': os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true',
                'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('SMTP_PORT', 587)),
                'username': os.getenv('SMTP_USERNAME', ''),
                'password': os.getenv('SMTP_PASSWORD', ''),
                'from_email': os.getenv('FROM_EMAIL', ''),
                'to_emails': os.getenv('ALERT_EMAILS', '').split(','),
            },
            'webhook': {
                'enabled': os.getenv('ENABLE_WEBHOOK_ALERTS', 'false').lower() == 'true',
                'url': os.getenv('WEBHOOK_URL', ''),
                'timeout': int(os.getenv('WEBHOOK_TIMEOUT', 10))
            },
            'slack': {
                'enabled': os.getenv('ENABLE_SLACK_ALERTS', 'false').lower() == 'true',
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
                'channel': os.getenv('SLACK_CHANNEL', '#alerts'),
                'username': os.getenv('SLACK_USERNAME', 'ScrapeBot')
            }
        }
    
    def _should_send_alert(self, alert_type: str, module: str) -> bool:
        """Determina si debe enviar alerta (evita spam)."""
        # Throttling: max 1 alerta del mismo tipo por módulo cada 30 min
        now = datetime.now()
        for alert in self.alert_history[-50:]:  # Solo revisar últimas 50
            if (alert['type'] == alert_type and 
                alert['module'] == module and
                (now - datetime.fromisoformat(alert['timestamp'])).seconds < 1800):
                return False
        return True
    
    def _record_alert(self, alert_type: str, module: str, message: str):
        """Registra alerta enviada."""
        self.alert_history.append({
            'type': alert_type,
            'module': module,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Mantener solo últimas 100 alertas
        self.alert_history = self.alert_history[-100:]
    
    def _send_email_alert(self, subject: str, body: str, is_html: bool = False):
        """Envía alerta por email."""
        if not EMAIL_AVAILABLE:
            print("❌ Email no disponible - saltando alerta por email")
            return False
            
        try:
            config = self.config['email']
            if not config['enabled'] or not config['to_emails'][0]:
                return False
                
            msg = MimeMultipart()
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])
            msg['Subject'] = f"[ScrapeBot] {subject}"
            
            msg.attach(MimeText(body, 'html' if is_html else 'plain'))
            
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            return False
    
    def _send_webhook_alert(self, payload: Dict[str, Any]):
        """Envía alerta por webhook."""
        try:
            config = self.config['webhook']
            if not config['enabled'] or not config['url']:
                return False
                
            response = requests.post(
                config['url'],
                json=payload,
                timeout=config['timeout']
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error enviando webhook: {e}")
            return False
    
    def _send_slack_alert(self, message: str, color: str = "danger"):
        """Envía alerta a Slack."""
        try:
            config = self.config['slack']
            if not config['enabled'] or not config['webhook_url']:
                return False
                
            payload = {
                "channel": config['channel'],
                "username": config['username'],
                "attachments": [{
                    "color": color,
                    "text": message,
                    "ts": datetime.now().timestamp()
                }]
            }
            
            response = requests.post(config['webhook_url'], json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error enviando a Slack: {e}")
            return False
    
    def send_module_failure_alert(self, module: str, error: str, attempts: int):
        """Alerta para fallo de módulo después de reintentos."""
        if not self._should_send_alert('module_failure', module):
            return
            
        subject = f"Fallo crítico en módulo {module}"
        
        body = f"""
        <h2>🚨 Fallo crítico detectado</h2>
        <p><strong>Módulo:</strong> {module}</p>
        <p><strong>Error:</strong> {error}</p>
        <p><strong>Intentos realizados:</strong> {attempts}</p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h3>Acciones recomendadas:</h3>
        <ul>
            <li>Verificar conectividad de red</li>
            <li>Revisar credenciales en .env</li>
            <li>Comprobar logs detallados en logs/{module}_{datetime.now().strftime('%Y%m%d')}.log</li>
        </ul>
        """
        
        # Enviar por todos los canales habilitados
        self._send_email_alert(subject, body, True)
        self._send_slack_alert(f"🚨 *{subject}*\nMódulo: `{module}`\nError: {error}")
        self._send_webhook_alert({
            'type': 'module_failure',
            'module': module,
            'error': error,
            'attempts': attempts,
            'timestamp': datetime.now().isoformat()
        })
        
        self._record_alert('module_failure', module, error)
    
    def send_system_recovery_alert(self, module: str):
        """Alerta cuando un módulo se recupera después de fallos."""
        subject = f"Recuperación exitosa - {module}"
        
        body = f"""
        <h2>✅ Sistema recuperado</h2>
        <p><strong>Módulo:</strong> {module}</p>
        <p><strong>Estado:</strong> Funcionando correctamente</p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        self._send_email_alert(subject, body, True)
        self._send_slack_alert(f"✅ *Recuperación exitosa*\nMódulo: `{module}` vuelve a funcionar", "good")
        
    def send_daily_summary_alert(self, stats: Dict[str, Any]):
        """Resumen diario de ejecuciones."""
        total_modules = len(stats.get('modules', []))
        successful = stats.get('successful_modules', 0)
        failed = stats.get('failed_modules', 0)
        
        subject = f"Resumen diario - {successful}/{total_modules} módulos exitosos"
        
        body = f"""
        <h2>📊 Resumen diario de scraping</h2>
        <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
        <p><strong>Módulos exitosos:</strong> {successful}/{total_modules}</p>
        <p><strong>Módulos fallidos:</strong> {failed}</p>
        <p><strong>Tasa de éxito:</strong> {(successful/total_modules*100):.1f}%</p>
        
        <h3>Detalle por módulo:</h3>
        <ul>
        """
        
        for module_stats in stats.get('modules', []):
            status = "✅" if module_stats['success'] else "❌"
            body += f"<li>{status} {module_stats['name']}: {module_stats.get('downloads', 0)} descargas</li>"
        
        body += "</ul>"
        
        # Solo enviar si hay fallos o es fin de semana (resumen semanal)
        if failed > 0 or datetime.now().weekday() == 6:  # Domingo
            self._send_email_alert(subject, body, True)
    
    def send_test_alert(self):
        """Envía alerta de prueba para verificar configuración."""
        subject = "Prueba de alertas - Sistema funcionando"
        body = f"""
        <h2>🧪 Alerta de prueba</h2>
        <p>Este es un mensaje de prueba del sistema de alertas.</p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Si recibes este mensaje, las alertas están configuradas correctamente.</p>
        """
        
        results = {
            'email': self._send_email_alert(subject, body, True),
            'slack': self._send_slack_alert("🧪 *Prueba de alertas*\nSistema funcionando correctamente", "good"),
            'webhook': self._send_webhook_alert({
                'type': 'test',
                'message': 'Test alert',
                'timestamp': datetime.now().isoformat()
            })
        }
        
        print(f"📧 Resultados de prueba de alertas: {results}")
        return results

# Instancia global
alert_manager = AlertManager()

def send_failure_alert(module: str, error: str, attempts: int):
    """Función de conveniencia para alertas de fallo."""
    alert_manager.send_module_failure_alert(module, error, attempts)

def send_recovery_alert(module: str):
    """Función de conveniencia para alertas de recuperación."""
    alert_manager.send_system_recovery_alert(module)