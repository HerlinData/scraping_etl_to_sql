#!/usr/bin/env python3
"""
Dashboard Híbrido de ScrapeBot - Estado General + Historial + Errores por Módulo
"""

import sqlite3
import json
import webbrowser
import threading
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import socket

class HybridScrapeBot_Dashboard:
    def __init__(self):
        self.db_path = Path("logs/scraping_processes.db")
        self.start_time = datetime.now()
        
    def get_database_data(self):
        """Obtener datos de la base de datos SQLite"""
        try:
            if not self.db_path.exists():
                return {
                    'sessions': [],
                    'module_errors': [],
                    'error': None,
                    'message': 'Base de datos no existe aún - esperando primera ejecución'
                }
                
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Verificar si las tablas existen
            cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='execution_sessions'
            """)
            
            if not cursor.fetchone():
                conn.close()
                return {
                    'sessions': [],
                    'module_errors': [],
                    'error': None,
                    'message': 'Tablas no creadas aún - esperando primera ejecución'
                }
            
            # Obtener sesiones de hoy
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT started_at, status, total_modules, successful_modules, duration_seconds
                FROM execution_sessions 
                WHERE DATE(started_at) = ? 
                ORDER BY started_at DESC
            """, (today,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'started_at': row[0],
                    'status': row[1],
                    'total_modules': row[2] or 0,
                    'successful_modules': row[3] or 0,
                    'duration_seconds': row[4] or 0
                })
            
            # Obtener errores por módulo de hoy
            cursor.execute("""
                SELECT m.session_id, m.module_name, m.status, m.error_message, s.started_at
                FROM module_executions m
                JOIN execution_sessions s ON m.session_id = s.session_id
                WHERE DATE(s.started_at) = ? AND m.status = 'failed'
                ORDER BY s.started_at DESC
            """, (today,))
            
            module_errors = []
            for row in cursor.fetchall():
                module_errors.append({
                    'session_id': row[0],
                    'module_name': row[1],
                    'status': row[2],
                    'error_message': row[3] or 'Error sin descripción',
                    'session_time': row[4]
                })
            
            conn.close()
            
            return {
                'sessions': sessions,
                'module_errors': module_errors,
                'error': None,
                'message': None
            }
            
        except Exception as e:
            return {
                'sessions': [],
                'module_errors': [],
                'error': f'Error accediendo a la base de datos: {e}'
            }

    def get_system_status(self, sessions):
        """Determinar el estado general del sistema"""
        if not sessions:
            return "⚫", "SISTEMA INACTIVO"
            
        # Revisar últimas 3 sesiones para determinar estado
        recent_sessions = sessions[:3]
        
        failed_count = len([s for s in recent_sessions if s['status'] == 'failed'])
        partial_count = len([s for s in recent_sessions if s['status'] == 'partial_success'])
        
        if failed_count >= 2:
            return "🔴", "SISTEMA CON PROBLEMAS CRÍTICOS"
        elif failed_count >= 1 or partial_count >= 2:
            return "🟡", "SISTEMA CON FALLOS MENORES"
        else:
            return "🟢", "SISTEMA OPERATIVO - TODO BIEN"

    def get_next_execution_time(self):
        """Calcular próxima ejecución basada en horarios 10:50-18:50"""
        now = datetime.now()
        execution_hours = [10, 11, 12, 13, 14, 15, 16, 17, 18]
        
        for hour in execution_hours:
            next_time = now.replace(hour=hour, minute=50, second=0, microsecond=0)
            if next_time > now:
                minutes_until = int((next_time - now).total_seconds() / 60)
                return next_time.strftime('%H:%M'), minutes_until
        
        # Si ya pasó la última ejecución del día
        return "FINALIZADO (día)", 0

    def format_session_history(self, sessions):
        """Formatear historial de sesiones del día"""
        execution_hours = [10, 11, 12, 13, 14, 15, 16, 17, 18]
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Crear diccionario de sesiones por hora
        sessions_by_hour = {}
        for session in sessions:
            try:
                session_time = datetime.fromisoformat(session['started_at'])
                hour = session_time.hour
                if hour in execution_hours:
                    sessions_by_hour[hour] = session
            except:
                continue
        
        # Generar historial visual
        history_items = []
        stats = {'exitosas': 0, 'con_fallos': 0, 'criticas': 0, 'pendientes': 0}
        
        for hour in execution_hours:
            time_str = f"{hour:02d}:50"
            if hour in sessions_by_hour:
                session = sessions_by_hour[hour]
                if session['status'] == 'success':
                    emoji = "🟢"
                    stats['exitosas'] += 1
                elif session['status'] == 'partial_success':
                    emoji = "🟡"
                    stats['con_fallos'] += 1
                else:
                    emoji = "🔴"
                    stats['criticas'] += 1
            else:
                # Verificar si ya pasó la hora
                current_time = datetime.now()
                session_time = current_time.replace(hour=hour, minute=50, second=0)
                if session_time < current_time:
                    emoji = "❓"  # Perdida
                    stats['criticas'] += 1
                else:
                    emoji = "⏳"  # Pendiente
                    stats['pendientes'] += 1
            
            history_items.append(f"{time_str} {emoji}")
        
        return " | ".join(history_items), stats

    def format_module_errors(self, module_errors, sessions):
        """Formatear errores detallados por módulo"""
        if not module_errors:
            return ""
        
        # Agrupar errores por sesión
        errors_by_session = {}
        for error in module_errors:
            session_id = error['session_id']
            if session_id not in errors_by_session:
                errors_by_session[session_id] = {
                    'time': error['session_time'],
                    'modules': []
                }
            errors_by_session[session_id]['modules'].append(error)
        
        # Crear output formateado
        error_details = []
        
        for session_id, data in errors_by_session.items():
            try:
                session_time = datetime.fromisoformat(data['time'])
                time_str = session_time.strftime('%H:%M')
                
                # Contar módulos fallidos
                failed_modules = len(data['modules'])
                
                # Determinar emoji basado en cantidad de fallos
                if failed_modules >= 3:
                    emoji = "🔴"
                else:
                    emoji = "🟡"
                
                # Crear lista de módulos fallidos
                failed_list = []
                for module in data['modules']:
                    module_name = module['module_name'].replace('scrapers.salesys.', '')
                    error_msg = module['error_message'][:50] + "..." if len(module['error_message']) > 50 else module['error_message']
                    failed_list.append(f"❌ {module_name} - {error_msg}")
                
                error_details.append(f"""
                {emoji} {time_str} - {failed_modules} MÓDULO{'S' if failed_modules > 1 else ''} FALLÓ{'ARON' if failed_modules > 1 else ''}:
                   {chr(10).join(['   ' + module for module in failed_list])}
                """.strip())
                
            except Exception as e:
                continue
        
        return "\n\n".join(error_details)

    def get_current_modules_status(self, sessions, module_errors):
        """Obtener estado actual de cada módulo"""
        modules = [
            'rga', 'estado_agente_v2', 'ocupacion_activaciones', 
            'nomina', 'ea_corte', 'delivery_cortes', 'activaciones_cortes'
        ]
        
        # Obtener última sesión exitosa
        last_session = sessions[0] if sessions else None
        if not last_session:
            return [(module, "❓", "No ejecutado", "Sin datos") for module in modules]
        
        # Crear diccionario de errores por módulo
        module_error_dict = {}
        for error in module_errors:
            module_name = error['module_name'].replace('scrapers.salesys.', '')
            if module_name not in module_error_dict:
                module_error_dict[module_name] = []
            module_error_dict[module_name].append(error)
        
        # Generar estado de cada módulo
        module_status = []
        last_time = datetime.fromisoformat(last_session['started_at']).strftime('%H:%M')
        
        for module in modules:
            if module in module_error_dict:
                # Verificar si se recuperó en la última ejecución
                latest_error = max(module_error_dict[module], key=lambda x: x['session_time'])
                latest_error_time = datetime.fromisoformat(latest_error['session_time'])
                last_session_time = datetime.fromisoformat(last_session['started_at'])
                
                if last_session_time > latest_error_time and last_session['status'] in ['success', 'partial_success']:
                    status = "✅"
                    note = f"Recuperado (era ❌ {latest_error_time.strftime('%H:%M')})"
                else:
                    status = "❌"
                    note = f"Error: {latest_error['error_message'][:30]}..."
            else:
                status = "✅"
                note = "Sin errores"
            
            module_status.append((module, status, f"Ejecutado {last_time}", note))
        
        return module_status

    def generate_html(self):
        """Generar HTML del dashboard"""
        db_data = self.get_database_data()
        
        if db_data.get('error'):
            return self.generate_error_html(db_data['error'])
        
        # Si no hay error pero tampoco datos, mostrar estado de espera
        if db_data.get('message') and not db_data['sessions']:
            return self.generate_waiting_html(db_data['message'])
        
        sessions = db_data['sessions']
        module_errors = db_data['module_errors']
        
        # Calcular métricas principales
        status_emoji, status_text = self.get_system_status(sessions)
        uptime = datetime.now() - self.start_time
        uptime_str = f"{int(uptime.total_seconds() // 3600)}h {int((uptime.total_seconds() % 3600) // 60)}m"
        
        next_exec, minutes_until = self.get_next_execution_time()
        next_exec_str = f"{next_exec}" + (f" (en {minutes_until} min)" if minutes_until > 0 else "")
        
        last_exec = sessions[0]['started_at'] if sessions else "Nunca"
        if last_exec != "Nunca":
            try:
                last_exec = datetime.fromisoformat(last_exec).strftime('%H:%M')
                last_exec += f" {status_emoji.split()[0] if ' ' in status_emoji else status_emoji}"
            except:
                pass
        
        # Generar historial
        history_str, stats = self.format_session_history(sessions)
        
        # Generar errores detallados
        error_details = self.format_module_errors(module_errors, sessions)
        
        # Estado de módulos
        modules_status = self.get_current_modules_status(sessions, module_errors)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ScrapeBot - Dashboard Híbrido</title>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    margin: 20px;
                    background: #1e1e1e;
                    color: #ffffff;
                    line-height: 1.4;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 8px;
                    border: 2px solid #4a4a4a;
                    margin-bottom: 20px;
                    text-align: center;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .status-green {{ color: #4ade80; }}
                .status-yellow {{ color: #fbbf24; }}
                .status-red {{ color: #f87171; }}
                .status-gray {{ color: #9ca3af; }}
                
                .section {{
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #4a4a4a;
                    margin-bottom: 20px;
                }}
                .section-title {{
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 15px;
                    color: #60a5fa;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 15px;
                }}
                .info-item {{
                    background: #1a1a1a;
                    padding: 10px;
                    border-radius: 4px;
                }}
                .history-line {{
                    font-size: 16px;
                    text-align: center;
                    padding: 15px;
                    background: #1a1a1a;
                    border-radius: 4px;
                    margin: 10px 0;
                }}
                .stats-line {{
                    text-align: center;
                    margin-top: 10px;
                    font-size: 14px;
                }}
                .error-details {{
                    background: #2d1b1b;
                    border: 1px solid #7f1d1d;
                    padding: 15px;
                    border-radius: 4px;
                    white-space: pre-line;
                    font-size: 13px;
                }}
                .modules-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                .modules-table td {{
                    padding: 8px 12px;
                    border-bottom: 1px solid #4a4a4a;
                }}
                .modules-table tr:nth-child(even) {{
                    background: #1a1a1a;
                }}
                .footer {{
                    text-align: center;
                    color: #9ca3af;
                    font-size: 12px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header Principal -->
                <div class="header {status_text.split()[-1].lower()}">
                    {status_emoji} SCRAPEBOT - {status_text}
                </div>
                
                <!-- Información General -->
                <div class="section">
                    <div class="info-grid">
                        <div class="info-item">
                            <strong>ESTADO GENERAL:</strong> {status_emoji} {status_text.split(' - ')[-1] if ' - ' in status_text else status_text}
                        </div>
                        <div class="info-item">
                            <strong>UPTIME:</strong> {uptime_str}
                        </div>
                        <div class="info-item">
                            <strong>Última ejecución:</strong> {last_exec}
                        </div>
                        <div class="info-item">
                            <strong>Próxima:</strong> {next_exec_str}
                        </div>
                    </div>
                </div>
                
                <!-- Historial del Día -->
                <div class="section">
                    <div class="section-title">📊 HISTORIAL DE HOY - {datetime.now().strftime('%d DE %B %Y').upper()}</div>
                    <div class="history-line">
                        {history_str}
                    </div>
                    <div class="stats-line">
                        ✅ {stats['exitosas']} exitosas &nbsp;&nbsp; 
                        🟡 {stats['con_fallos']} con fallos &nbsp;&nbsp; 
                        🔴 {stats['criticas']} críticas &nbsp;&nbsp; 
                        ⏳ {stats['pendientes']} pendientes
                        {f" &nbsp;&nbsp; 📊 Efectividad: {int((stats['exitosas'] / (stats['exitosas'] + stats['con_fallos'] + stats['criticas']) * 100))}%" if (stats['exitosas'] + stats['con_fallos'] + stats['criticas']) > 0 else ""}
                    </div>
                </div>
                
                {f'''
                <!-- Detalles de Errores -->
                <div class="section">
                    <div class="section-title">⚠️ DETALLES DE ERRORES POR EJECUCIÓN</div>
                    <div class="error-details">
{error_details}
                    </div>
                </div>
                ''' if error_details else ''}
                
                <!-- Estado de Módulos -->
                <div class="section">
                    <div class="section-title">📋 ESTADO ACTUAL DE MÓDULOS</div>
                    <table class="modules-table">
                        {''.join([f'''
                        <tr>
                            <td>{status} {module}</td>
                            <td>{execution}</td>
                            <td>{note}</td>
                        </tr>
                        ''' for module, status, execution, note in modules_status])}
                    </table>
                </div>
                
                <div class="footer">
                    🔄 Auto-refresh cada 30 segundos &nbsp;&nbsp;&nbsp;&nbsp; 🕐 Última actualización: {datetime.now().strftime('%H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

    def generate_error_html(self, error_message):
        """Generar HTML de error"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ScrapeBot - Error</title>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    margin: 40px;
                    background: #1e1e1e;
                    color: #ffffff;
                    text-align: center;
                }}
                .error {{
                    background: #2d1b1b;
                    border: 2px solid #7f1d1d;
                    padding: 40px;
                    border-radius: 8px;
                    display: inline-block;
                }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Error en el Dashboard</h2>
                <p>{error_message}</p>
                <p><em>Reintentando en 30 segundos...</em></p>
            </div>
        </body>
        </html>
        """

    def generate_waiting_html(self, message):
        """Generar HTML de estado de espera"""
        next_exec, minutes_until = self.get_next_execution_time()
        next_exec_str = f"{next_exec}" + (f" (en {minutes_until} min)" if minutes_until > 0 else "")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ScrapeBot - Esperando Datos</title>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    margin: 40px;
                    background: #1e1e1e;
                    color: #ffffff;
                    text-align: center;
                }}
                .waiting {{
                    background: #2d2d2d;
                    border: 2px solid #4a4a4a;
                    padding: 40px;
                    border-radius: 8px;
                    display: inline-block;
                    max-width: 600px;
                }}
                .status {{
                    font-size: 24px;
                    margin-bottom: 20px;
                    color: #60a5fa;
                }}
                .info {{
                    margin: 15px 0;
                    font-size: 16px;
                }}
                .next-exec {{
                    background: #1a1a1a;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="waiting">
                <div class="status">⏳ SCRAPEBOT - ESPERANDO PRIMERA EJECUCIÓN</div>
                <div class="info">{message}</div>
                
                <div class="next-exec">
                    <strong>Próxima ejecución programada:</strong><br>
                    {next_exec_str}
                </div>
                
                <div class="info">
                    <strong>Horarios de ejecución:</strong><br>
                    10:50 | 11:50 | 12:50 | 13:50 | 14:50 | 15:50 | 16:50 | 17:50 | 18:50
                </div>
                
                <div class="info">
                    <em>El dashboard se actualizará automáticamente cuando comience la primera ejecución</em>
                </div>
                
                <div style="margin-top: 30px; font-size: 12px; color: #9ca3af;">
                    🔄 Auto-refresh cada 30 segundos &nbsp;&nbsp; 🕐 {datetime.now().strftime('%H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            dashboard = HybridScrapeBot_Dashboard()
            html = dashboard.generate_html()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suprimir logs del servidor

def find_available_port(start_port=8080):
    """Encontrar puerto disponible"""
    for port in range(start_port, start_port + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def run_server():
    """Ejecutar servidor del dashboard"""
    port = find_available_port()
    if not port:
        print("❌ No se pudo encontrar un puerto disponible")
        return
    
    print("🚀 Iniciando ScrapeBot Dashboard Híbrido...")
    print("📊 Dashboard operacional con estado general + historial + errores")
    print(f"🔗 URL: http://localhost:{port}")
    print("--------------------------------------------------")
    
    server = HTTPServer(('localhost', port), DashboardHandler)
    
    # Abrir navegador automáticamente
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{port}')
        print("🌐 Abriendo navegador automáticamente...")
        print(f"🌐 ScrapeBot Dashboard Híbrido iniciado en http://localhost:{port}")
        print("📊 Dashboard con historial de ejecuciones y detalles de errores")
        print("⏹️  Presiona Ctrl+C para detener")
        print("----------------------------------------")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo dashboard...")
        server.shutdown()

if __name__ == "__main__":
    run_server()