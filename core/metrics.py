"""
Sistema de métricas y monitoreo de performance
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import threading
import os

@dataclass
class ModuleMetrics:
    """Métricas de un módulo específico."""
    module_name: str
    started_at: str
    finished_at: Optional[str] = None
    duration_seconds: float = 0.0
    status: str = "running"  # running, success, failed
    downloads_attempted: int = 0
    downloads_successful: int = 0
    downloads_failed: int = 0
    login_attempts: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    @property
    def success_rate(self) -> float:
        """Calcula tasa de éxito de descargas."""
        if self.downloads_attempted == 0:
            return 0.0
        return (self.downloads_successful / self.downloads_attempted) * 100
    
    def mark_completed(self, status: str = "success"):
        """Marca el módulo como completado."""
        self.finished_at = datetime.now().isoformat()
        self.status = status
        if self.started_at:
            start_time = datetime.fromisoformat(self.started_at)
            end_time = datetime.fromisoformat(self.finished_at)
            self.duration_seconds = (end_time - start_time).total_seconds()

@dataclass 
class SystemMetrics:
    """Métricas del sistema completo."""
    session_id: str
    started_at: str
    modules: List[ModuleMetrics]
    total_duration: float = 0.0
    system_status: str = "running"
    
    @property
    def total_modules(self) -> int:
        return len(self.modules)
    
    @property
    def successful_modules(self) -> int:
        return len([m for m in self.modules if m.status == "success"])
    
    @property
    def failed_modules(self) -> int:
        return len([m for m in self.modules if m.status == "failed"])
    
    @property
    def overall_success_rate(self) -> float:
        if self.total_modules == 0:
            return 0.0
        return (self.successful_modules / self.total_modules) * 100
    
    @property
    def total_downloads(self) -> int:
        return sum(m.downloads_attempted for m in self.modules)
    
    @property
    def successful_downloads(self) -> int:
        return sum(m.downloads_successful for m in self.modules)

class MetricsCollector:
    """Recolector y almacenador de métricas."""
    
    def __init__(self, metrics_file: Path = None):
        self.metrics_file = metrics_file or Path("logs/metrics.json")
        self.current_session: Optional[SystemMetrics] = None
        self.module_metrics: Dict[str, ModuleMetrics] = {}
        self._lock = threading.Lock()
        
        # Crear directorio si no existe
        self.metrics_file.parent.mkdir(exist_ok=True)
    
    def start_session(self, session_id: str = None) -> str:
        """Inicia una nueva sesión de métricas."""
        if not session_id:
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with self._lock:
            self.current_session = SystemMetrics(
                session_id=session_id,
                started_at=datetime.now().isoformat(),
                modules=[]
            )
            self.module_metrics.clear()
        
        return session_id
    
    def start_module(self, module_name: str) -> ModuleMetrics:
        """Inicia tracking de un módulo."""
        with self._lock:
            metrics = ModuleMetrics(
                module_name=module_name,
                started_at=datetime.now().isoformat()
            )
            self.module_metrics[module_name] = metrics
            
            if self.current_session:
                self.current_session.modules.append(metrics)
                
        return metrics
    
    def finish_module(self, module_name: str, status: str = "success"):
        """Finaliza tracking de un módulo."""
        with self._lock:
            if module_name in self.module_metrics:
                self.module_metrics[module_name].mark_completed(status)
    
    def record_download_attempt(self, module_name: str):
        """Registra intento de descarga."""
        with self._lock:
            if module_name in self.module_metrics:
                self.module_metrics[module_name].downloads_attempted += 1
    
    def record_download_success(self, module_name: str):
        """Registra descarga exitosa."""
        with self._lock:
            if module_name in self.module_metrics:
                self.module_metrics[module_name].downloads_successful += 1
    
    def record_download_failure(self, module_name: str):
        """Registra descarga fallida."""
        with self._lock:
            if module_name in self.module_metrics:
                self.module_metrics[module_name].downloads_failed += 1
    
    def record_login_attempt(self, module_name: str):
        """Registra intento de login."""
        with self._lock:
            if module_name in self.module_metrics:
                self.module_metrics[module_name].login_attempts += 1
    
    def record_error(self, module_name: str, error: str):
        """Registra error."""
        with self._lock:
            if module_name in self.module_metrics:
                self.module_metrics[module_name].errors.append(error)
    
    def record_warning(self, module_name: str, warning: str):
        """Registra warning."""
        with self._lock:
            if module_name in self.module_metrics:
                self.module_metrics[module_name].warnings.append(warning)
    
    def finish_session(self, status: str = "completed"):
        """Finaliza la sesión actual."""
        with self._lock:
            if not self.current_session:
                return
                
            # Calcular duración total
            start_time = datetime.fromisoformat(self.current_session.started_at)
            end_time = datetime.now()
            self.current_session.total_duration = (end_time - start_time).total_seconds()
            self.current_session.system_status = status
            
            # Guardar métricas
            self._save_session_metrics()
    
    def _save_session_metrics(self):
        """Guarda métricas de la sesión actual."""
        if not self.current_session:
            return
            
        # Cargar métricas existentes
        existing_metrics = []
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    existing_metrics = json.load(f)
            except:
                existing_metrics = []
        
        # Convertir a dict y añadir
        session_dict = asdict(self.current_session)
        existing_metrics.append(session_dict)
        
        # Mantener solo últimas 100 sesiones
        existing_metrics = existing_metrics[-100:]
        
        # Guardar
        with open(self.metrics_file, 'w') as f:
            json.dump(existing_metrics, f, indent=2)
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Obtiene métricas de la sesión actual."""
        return self.current_session
    
    def get_historical_metrics(self, days: int = 7) -> List[SystemMetrics]:
        """Obtiene métricas históricas."""
        if not self.metrics_file.exists():
            return []
            
        try:
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
            
            # Filtrar por fecha
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_metrics = []
            
            for session_data in data:
                session_date = datetime.fromisoformat(session_data['started_at'])
                if session_date >= cutoff_date:
                    # Reconstruir objetos ModuleMetrics
                    modules = [ModuleMetrics(**m) for m in session_data['modules']]
                    session_data['modules'] = modules
                    filtered_metrics.append(SystemMetrics(**session_data))
            
            return filtered_metrics
        except:
            return []
    
    def generate_summary_report(self, days: int = 7) -> Dict[str, Any]:
        """Genera reporte resumen."""
        historical = self.get_historical_metrics(days)
        
        if not historical:
            return {"error": "No hay datos históricos"}
        
        total_sessions = len(historical)
        successful_sessions = len([s for s in historical if s.overall_success_rate == 100])
        total_modules_run = sum(s.total_modules for s in historical)
        total_successful_modules = sum(s.successful_modules for s in historical)
        total_downloads = sum(s.total_downloads for s in historical)
        successful_downloads = sum(s.successful_downloads for s in historical)
        
        # Módulos con más fallos
        module_failures = {}
        for session in historical:
            for module in session.modules:
                if module.status == "failed":
                    module_failures[module.module_name] = module_failures.get(module.module_name, 0) + 1
        
        return {
            "period_days": days,
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "session_success_rate": (successful_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            "total_modules_run": total_modules_run,
            "total_successful_modules": total_successful_modules,
            "module_success_rate": (total_successful_modules / total_modules_run * 100) if total_modules_run > 0 else 0,
            "total_downloads": total_downloads,
            "successful_downloads": successful_downloads,
            "download_success_rate": (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0,
            "most_failing_modules": sorted(module_failures.items(), key=lambda x: x[1], reverse=True)[:5],
            "generated_at": datetime.now().isoformat()
        }

# Instancia global
metrics_collector = MetricsCollector()

def start_session(session_id: str = None) -> str:
    """Inicia nueva sesión de métricas."""
    return metrics_collector.start_session(session_id)

def start_module(module_name: str) -> ModuleMetrics:
    """Inicia tracking de módulo."""
    return metrics_collector.start_module(module_name)

def finish_module(module_name: str, status: str = "success"):
    """Finaliza tracking de módulo."""
    metrics_collector.finish_module(module_name, status)

def finish_session(status: str = "completed"):
    """Finaliza sesión actual."""
    metrics_collector.finish_session(status)