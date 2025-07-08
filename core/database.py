"""
Sistema de base de datos SQLite para tracking de procesos
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import threading

class ProcessDatabase:
    """Base de datos SQLite para tracking de procesos de scraping."""
    
    def __init__(self, db_path: str = "logs/scraping_processes.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Inicializa las tablas de la base de datos."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla de sesiones de ejecución
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'running',
                    total_modules INTEGER DEFAULT 0,
                    successful_modules INTEGER DEFAULT 0,
                    failed_modules INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de ejecución de módulos individuales
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS module_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    module_name TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'running',
                    attempts INTEGER DEFAULT 1,
                    downloads_attempted INTEGER DEFAULT 0,
                    downloads_successful INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    error_message TEXT,
                    output_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES execution_sessions (session_id)
                )
            """)
            
            # Tabla de archivos descargados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloaded_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    module_name TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    file_size_bytes INTEGER,
                    download_timestamp TIMESTAMP NOT NULL,
                    validation_status TEXT DEFAULT 'pending',
                    record_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES execution_sessions (session_id)
                )
            """)
            
            # Tabla de métricas de performance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES execution_sessions (session_id)
                )
            """)
            
            conn.commit()
            conn.close()
    
    def start_session(self, session_id: str) -> int:
        """Inicia una nueva sesión de ejecución."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO execution_sessions (session_id, started_at, status)
                VALUES (?, ?, 'running')
            """, (session_id, datetime.now()))
            
            session_db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return session_db_id
    
    def finish_session(self, session_id: str, status: str, notes: str = None):
        """Finaliza una sesión de ejecución."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calcular estadísticas de la sesión
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_modules,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM module_executions 
                WHERE session_id = ?
            """, (session_id,))
            
            stats = cursor.fetchone()
            total_modules, successful, failed = stats or (0, 0, 0)
            
            # Calcular duración
            cursor.execute("""
                SELECT started_at FROM execution_sessions WHERE session_id = ?
            """, (session_id,))
            
            start_time = cursor.fetchone()
            duration = None
            if start_time:
                start_dt = datetime.fromisoformat(start_time[0])
                duration = (datetime.now() - start_dt).total_seconds()
            
            # Actualizar sesión
            cursor.execute("""
                UPDATE execution_sessions 
                SET finished_at = ?, status = ?, total_modules = ?, 
                    successful_modules = ?, failed_modules = ?, 
                    duration_seconds = ?, notes = ?
                WHERE session_id = ?
            """, (datetime.now(), status, total_modules, successful, 
                  failed, duration, notes, session_id))
            
            conn.commit()
            conn.close()
    
    def start_module(self, session_id: str, module_name: str) -> int:
        """Inicia ejecución de un módulo."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO module_executions (session_id, module_name, started_at, status)
                VALUES (?, ?, ?, 'running')
            """, (session_id, module_name, datetime.now()))
            
            module_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return module_id
    
    def finish_module(self, session_id: str, module_name: str, status: str, 
                     attempts: int = 1, error_message: str = None, output_log: str = None):
        """Finaliza ejecución de un módulo."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calcular duración
            cursor.execute("""
                SELECT started_at FROM module_executions 
                WHERE session_id = ? AND module_name = ? 
                ORDER BY id DESC LIMIT 1
            """, (session_id, module_name))
            
            start_time = cursor.fetchone()
            duration = None
            if start_time:
                start_dt = datetime.fromisoformat(start_time[0])
                duration = (datetime.now() - start_dt).total_seconds()
            
            cursor.execute("""
                UPDATE module_executions 
                SET finished_at = ?, status = ?, attempts = ?, 
                    duration_seconds = ?, error_message = ?, output_log = ?
                WHERE session_id = ? AND module_name = ? 
                AND id = (SELECT MAX(id) FROM module_executions 
                         WHERE session_id = ? AND module_name = ?)
            """, (datetime.now(), status, attempts, duration, 
                  error_message, output_log, session_id, module_name, 
                  session_id, module_name))
            
            conn.commit()
            conn.close()
    
    def record_download(self, session_id: str, module_name: str, file_name: str, 
                       file_path: str = None, file_size: int = None):
        """Registra un archivo descargado."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO downloaded_files 
                (session_id, module_name, file_name, file_path, file_size_bytes, download_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, module_name, file_name, file_path, file_size, datetime.now()))
            
            conn.commit()
            conn.close()
    
    def get_recent_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene las sesiones más recientes."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM execution_sessions 
            ORDER BY started_at DESC 
            LIMIT ?
        """, (limit,))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return sessions
    
    def get_session_modules(self, session_id: str) -> List[Dict[str, Any]]:
        """Obtiene los módulos de una sesión específica."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM module_executions 
            WHERE session_id = ? 
            ORDER BY started_at
        """, (session_id,))
        
        modules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return modules
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """Obtiene resumen de un día específico."""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Estadísticas de sesiones del día
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_sessions,
                SUM(CASE WHEN status IN ('partial_success', 'failed') THEN 1 ELSE 0 END) as failed_sessions,
                AVG(duration_seconds) as avg_duration,
                SUM(total_modules) as total_modules,
                SUM(successful_modules) as successful_modules
            FROM execution_sessions 
            WHERE DATE(started_at) = ?
        """, (date,))
        
        session_stats = cursor.fetchone()
        
        # Módulos más problemáticos del día
        cursor.execute("""
            SELECT 
                module_name,
                COUNT(*) as executions,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures,
                AVG(duration_seconds) as avg_duration
            FROM module_executions 
            WHERE DATE(started_at) = ?
            GROUP BY module_name
            ORDER BY failures DESC, avg_duration DESC
        """, (date,))
        
        module_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'date': date,
            'sessions': {
                'total': session_stats[0] or 0,
                'successful': session_stats[1] or 0,
                'failed': session_stats[2] or 0,
                'avg_duration': session_stats[3] or 0,
            },
            'modules': {
                'total_executions': session_stats[4] or 0,
                'successful_executions': session_stats[5] or 0,
                'problematic_modules': [
                    {
                        'name': row[0],
                        'executions': row[1],
                        'failures': row[2],
                        'avg_duration': row[3] or 0
                    }
                    for row in module_stats
                ]
            }
        }
    
    def cleanup_old_records(self, days_to_keep: int = 30):
        """Limpia registros antiguos."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
            
            cursor.execute("""
                DELETE FROM downloaded_files 
                WHERE created_at < ?
            """, (cutoff_date,))
            
            cursor.execute("""
                DELETE FROM module_executions 
                WHERE created_at < ?
            """, (cutoff_date,))
            
            cursor.execute("""
                DELETE FROM execution_sessions 
                WHERE created_at < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count

# Instancia global
process_db = ProcessDatabase()