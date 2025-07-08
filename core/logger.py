"""
Sistema de logging centralizado para todos los scrapers
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class ScraperLogger:
    """Logger especializado para scrapers con contexto estructurado."""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.logger = logging.getLogger(module_name)
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'module': module_name,
            'downloads_attempted': 0,
            'downloads_successful': 0,
            'login_attempts': 0,
            'errors': [],
            'warnings': []
        }
        
    def setup_file_logging(self, log_dir: Path = None):
        """Configura logging específico para este módulo."""
        if not log_dir:
            log_dir = Path("logs")
        
        log_dir.mkdir(exist_ok=True)
        
        # Handler para archivo específico del módulo
        module_log_file = log_dir / f"{self.module_name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(module_log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formato detallado para archivos
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(session_id)s] - %(message)s'
        )
        file_handler.setFormatter(detailed_formatter)
        
        # Evitar duplicados
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.DEBUG)
        
    def _log_with_context(self, level: str, message: str, extra_data: Dict[str, Any] = None):
        """Log con contexto estructurado."""
        context = {
            'session_id': self.session_id,
            'module': self.module_name,
            'timestamp': datetime.now().isoformat()
        }
        
        if extra_data:
            context.update(extra_data)
        
        # Log estructurado
        getattr(self.logger, level.lower())(message, extra=context)
        
        # Guardar en stats para métricas
        if level.lower() == 'error':
            self.stats['errors'].append({
                'message': message,
                'timestamp': context['timestamp'],
                'data': extra_data
            })
        elif level.lower() == 'warning':
            self.stats['warnings'].append({
                'message': message,
                'timestamp': context['timestamp'],
                'data': extra_data
            })
    
    def info(self, message: str, **kwargs):
        """Log nivel INFO."""
        self._log_with_context('INFO', f"ℹ️  {message}", kwargs)
        
    def success(self, message: str, **kwargs):
        """Log para operaciones exitosas."""
        self._log_with_context('INFO', f"✅ {message}", kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log nivel WARNING."""
        self._log_with_context('WARNING', f"⚠️  {message}", kwargs)
        
    def error(self, message: str, **kwargs):
        """Log nivel ERROR."""
        self._log_with_context('ERROR', f"❌ {message}", kwargs)
        
    def debug(self, message: str, **kwargs):
        """Log nivel DEBUG."""
        self._log_with_context('DEBUG', f"🔍 {message}", kwargs)
        
    def login_attempt(self, attempt: int, max_attempts: int):
        """Log específico para intentos de login."""
        self.stats['login_attempts'] += 1
        self.info(f"Intento de login {attempt}/{max_attempts}", 
                 attempt=attempt, max_attempts=max_attempts)
        
    def login_success(self):
        """Log para login exitoso."""
        self.success("Login exitoso")
        
    def login_failed(self, error: str = None):
        """Log para login fallido."""
        self.error(f"Login fallido: {error}" if error else "Login fallido")
        
    def download_started(self, filename: str, date: str = None):
        """Log para inicio de descarga."""
        self.stats['downloads_attempted'] += 1
        self.info(f"Iniciando descarga: {filename}", 
                 filename=filename, date=date)
        
    def download_success(self, filename: str, size: int = None):
        """Log para descarga exitosa."""
        self.stats['downloads_successful'] += 1
        extra = {'filename': filename}
        if size:
            extra['file_size_bytes'] = size
        self.success(f"Descarga exitosa: {filename}", **extra)
        
    def download_failed(self, filename: str, error: str):
        """Log para descarga fallida."""
        self.error(f"Descarga fallida: {filename} - {error}", 
                  filename=filename, error=error)
        
    def timeout_error(self, operation: str, timeout_seconds: int):
        """Log para timeouts."""
        self.error(f"Timeout en {operation} después de {timeout_seconds}s", 
                  operation=operation, timeout=timeout_seconds)
        
    def form_interaction(self, action: str, element: str, value: str = None):
        """Log para interacciones con formularios."""
        extra = {'action': action, 'element': element}
        if value:
            extra['value'] = value
        self.debug(f"Formulario: {action} en {element}", **extra)
        
    def session_summary(self) -> Dict[str, Any]:
        """Genera resumen de la sesión."""
        self.stats['finished_at'] = datetime.now().isoformat()
        self.stats['duration_seconds'] = (
            datetime.fromisoformat(self.stats['finished_at']) - 
            datetime.fromisoformat(self.stats['started_at'])
        ).total_seconds()
        
        success_rate = 0
        if self.stats['downloads_attempted'] > 0:
            success_rate = (self.stats['downloads_successful'] / 
                          self.stats['downloads_attempted']) * 100
        
        self.stats['success_rate'] = round(success_rate, 2)
        
        # Log resumen
        self.info(f"Sesión completada - Éxito: {self.stats['downloads_successful']}/{self.stats['downloads_attempted']} ({success_rate:.1f}%)",
                 **self.stats)
        
        return self.stats
        
    def save_metrics(self, metrics_file: Path = None):
        """Guarda métricas en archivo JSON."""
        if not metrics_file:
            metrics_file = Path("logs/metrics.json")
            
        metrics_file.parent.mkdir(exist_ok=True)
        
        # Cargar métricas existentes
        metrics = []
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
            except:
                metrics = []
        
        # Añadir nuevas métricas
        metrics.append(self.session_summary())
        
        # Mantener solo últimos 1000 registros
        metrics = metrics[-1000:]
        
        # Guardar
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
            
        self.debug(f"Métricas guardadas en {metrics_file}")

def get_logger(module_name: str) -> ScraperLogger:
    """Factory function para obtener logger configurado."""
    logger = ScraperLogger(module_name)
    logger.setup_file_logging()
    return logger