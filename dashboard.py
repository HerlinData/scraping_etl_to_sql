#!/usr/bin/env python3
"""
Dashboard Principal del Sistema de Scraping
- Monitoreo en tiempo real
- Base de datos SQLite integrada
- Sin dependencias problemáticas
"""
import json
import http.server
import socketserver
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

class ScrapeBot_Dashboard:
    """Dashboard principal del sistema de scraping."""
    
    def __init__(self, port: int = 8081):
        self.port = port
        
    def get_system_status(self):
        """Obtiene estado básico del sistema."""
        status = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'files_ok': True,
            'logs_exist': False,
            'env_exists': False,
            'metrics_exist': False,
            'database_exist': False
        }
        
        # Verificar archivos críticos
        critical_files = ['.env', 'main.py', 'config/settings.py']
        for file_path in critical_files:
            if not Path(file_path).exists():
                status['files_ok'] = False
                break
        
        # Verificar logs
        status['logs_exist'] = Path('logs').exists()
        status['env_exists'] = Path('.env').exists()
        status['metrics_exist'] = Path('logs/metrics.json').exists()
        status['database_exist'] = Path('logs/scraping_processes.db').exists()
        
        return status
    
    def get_database_summary(self):
        """Obtiene resumen de la base de datos."""
        try:
            # Importar aquí para evitar errores si no existe
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from core.database import process_db
            
            # Obtener resumen del día actual
            daily_summary = process_db.get_daily_summary()
            recent_sessions = process_db.get_recent_sessions(10)
            
            return {
                'daily_summary': daily_summary,
                'recent_sessions': recent_sessions
            }
        except Exception as e:
            return {
                'error': f"Error accediendo a BD: {str(e)}",
                'daily_summary': None,
                'recent_sessions': []
            }
        
    def generate_html(self) -> str:
        """Genera HTML del dashboard."""
        status = self.get_system_status()
        
        # Obtener datos de la base de datos
        db_data = self.get_database_summary()
        daily_summary = db_data.get('daily_summary')
        recent_sessions = db_data.get('recent_sessions', [])
        
        # Leer métricas si existen
        metrics_summary = "No hay datos disponibles"
        if daily_summary and not db_data.get('error'):
            session_stats = daily_summary['sessions']
            metrics_summary = f"Hoy: {session_stats['successful']}/{session_stats['total']} sesiones exitosas"
        elif status['metrics_exist']:
            try:
                with open('logs/metrics.json', 'r') as f:
                    metrics_data = json.load(f)
                    if metrics_data:
                        recent = metrics_data[-5:]  # Últimas 5 sesiones
                        successful = len([s for s in recent if s.get('system_status') == 'success'])
                        metrics_summary = f"Últimas 5 sesiones: {successful}/5 exitosas"
            except:
                metrics_summary = "Error leyendo métricas"
        
        # Estado general
        overall_status = "🟢 SALUDABLE" if status['files_ok'] else "🔴 PROBLEMAS"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>NoMeQuejoBot</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .card {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .status-ok {{ color: green; font-weight: bold; }}
                .status-error {{ color: red; font-weight: bold; }}
                .metric {{ margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; }}
                .timestamp {{ font-size: 12px; color: #666; text-align: center; }}
                h1 {{ text-align: center; color: #333; }}
                h2 {{ color: #444; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                .file-check {{ margin: 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 NoMeQuejoBot</h1>
                <p class="timestamp">Última actualización: {status['timestamp']}</p>
                
                <div class="card">
                    <h2>📊 Estado General</h2>
                    <div class="metric">
                        <strong>Estado del Sistema:</strong> 
                        <span class="{'status-ok' if status['files_ok'] else 'status-error'}">{overall_status}</span>
                    </div>
                    <div class="metric">
                        <strong>Métricas:</strong> {metrics_summary}
                    </div>
                </div>
                
                <div class="card">
                    <h2>🔧 Verificación de Archivos</h2>
                    <div class="file-check">
                        {'✅' if status['env_exists'] else '❌'} 
                        <strong>.env</strong> - Archivo de configuración
                    </div>
                    <div class="file-check">
                        {'✅' if Path('main.py').exists() else '❌'} 
                        <strong>main.py</strong> - Script principal
                    </div>
                    <div class="file-check">
                        {'✅' if Path('config/settings.py').exists() else '❌'} 
                        <strong>config/settings.py</strong> - Configuración del sistema
                    </div>
                    <div class="file-check">
                        {'✅' if status['logs_exist'] else '❌'} 
                        <strong>logs/</strong> - Directorio de logs
                    </div>
                    <div class="file-check">
                        {'✅' if status['database_exist'] else '❌'} 
                        <strong>scraping_processes.db</strong> - Base de datos de procesos
                    </div>
                </div>
        """
        
        # Mostrar datos de la base de datos si están disponibles
        if daily_summary and not db_data.get('error'):
            session_stats = daily_summary['sessions']
            module_stats = daily_summary['modules']
            
            html += f"""
                <div class="card">
                    <h2>📊 Resumen del Día</h2>
                    <div class="metric">
                        <strong>Sesiones:</strong> {session_stats['total']} ejecutadas, {session_stats['successful']} exitosas
                    </div>
                    <div class="metric">
                        <strong>Módulos:</strong> {module_stats['successful_executions']}/{module_stats['total_executions']} exitosos
                    </div>
                    <div class="metric">
                        <strong>Duración promedio:</strong> {session_stats['avg_duration']:.1f} segundos
                    </div>
                </div>
            """
            
            # Mostrar módulos problemáticos si existen
            problematic = module_stats.get('problematic_modules', [])
            if problematic:
                html += """
                    <div class="card">
                        <h2>⚠️ Módulos con Fallos Hoy</h2>
                """
                for module in problematic[:5]:  # Top 5
                    if module['failures'] > 0:
                        html += f"""
                            <div class="metric">
                                <strong>{module['name']}:</strong> {module['failures']} fallos de {module['executions']} ejecuciones
                            </div>
                        """
                html += "</div>"
        
        # Mostrar sesiones recientes de la BD
        if recent_sessions:
            html += """
                <div class="card">
                    <h2>📋 Últimas Sesiones</h2>
                    <table>
                        <tr>
                            <th>Hora</th>
                            <th>Estado</th>
                            <th>Módulos</th>
                            <th>Duración</th>
                        </tr>
            """
            
            for session in recent_sessions[:10]:  # Últimas 10
                started_at = session.get('started_at', '')
                status_session = session.get('status', 'unknown')
                total_modules = session.get('total_modules', 0)
                successful_modules = session.get('successful_modules', 0)
                duration = session.get('duration_seconds', 0)
                
                status_emoji = {
                    'success': '✅',
                    'partial_success': '⚠️',
                    'failed': '❌',
                    'error': '💥',
                    'running': '🔄'
                }.get(status_session, '⏳')
                
                try:
                    time_str = datetime.fromisoformat(started_at).strftime('%H:%M') if started_at else 'N/A'
                except:
                    time_str = 'N/A'
                
                html += f"""
                    <tr>
                        <td>{time_str}</td>
                        <td>{status_emoji} {status_session}</td>
                        <td>{successful_modules}/{total_modules}</td>
                        <td>{duration:.1f}s</td>
                    </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        # Información de uso
        html += f"""
                <div class="card">
                    <h2>ℹ️ Información del Sistema</h2>
                    <div class="metric">
                        <strong>🔄 Auto-refresh:</strong> Esta página se actualiza cada 30 segundos
                    </div>
                    <div class="metric">
                        <strong>🚀 Para ejecutar scrapers:</strong> <code>python main.py</code>
                    </div>
                    <div class="metric">
                        <strong>⏰ Horarios programados:</strong> 10:50, 11:50, 12:50... hasta 18:50 (cada hora)
                    </div>
                    <div class="metric">
                        <strong>⚙️ Configuración:</strong> Editar archivo <code>.env</code>
                    </div>
                    <div class="metric">
                        <strong>📊 Ver métricas en consola:</strong> <code>python utils/db_viewer.py</code>
                    </div>
                    <div class="metric">
                        <strong>🗄️ Base de datos:</strong> <code>logs/scraping_processes.db</code>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🎯 Acciones Rápidas</h2>
                    <div class="metric">
                        <button onclick="location.reload()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            🔄 Actualizar Dashboard
                        </button>
                    </div>
                </div>
                
            </div>
        </body>
        </html>
        """
        
        return html
    
    def start_server(self):
        """Inicia el servidor web."""
        class DashboardHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                dashboard = ScrapeBot_Dashboard()
                self.wfile.write(dashboard.generate_html().encode('utf-8'))
            
            def log_message(self, format, *args):
                return  # Silenciar logs del servidor
        
        try:
            with socketserver.TCPServer(("", self.port), DashboardHandler) as httpd:
                print(f"🌐 NoMeQuejoBot Dashboard iniciado en http://localhost:{self.port}")
                print("📊 Dashboard con base de datos SQLite integrada")
                print("⏹️  Presiona Ctrl+C para detener")
                httpd.serve_forever()
        except OSError as e:
            if "10048" in str(e) or "Address already in use" in str(e):
                print(f"❌ Puerto {self.port} ya está en uso")
                print("🔄 Intentando con puerto alternativo...")
                
                # Probar puertos alternativos
                for new_port in [8081, 8082, 8083, 8084, 8085]:
                    try:
                        print(f"🔍 Probando puerto {new_port}...")
                        with socketserver.TCPServer(("", new_port), DashboardHandler) as httpd:
                            self.port = new_port
                            print(f"✅ Dashboard iniciado en http://localhost:{new_port}")
                            print("⏹️  Presiona Ctrl+C para detener")
                            
                            # Abrir navegador con nuevo puerto
                            try:
                                webbrowser.open(f"http://localhost:{new_port}")
                            except:
                                pass
                                
                            httpd.serve_forever()
                            return
                    except OSError:
                        continue
                
                print("❌ No se pudo encontrar un puerto disponible")
                print("💡 Cierra otros procesos que usen puertos 8081-8085")
            else:
                print(f"❌ Error iniciando servidor: {e}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")

def main():
    print("🚀 Iniciando NoMeQuejoBot Dashboard...")
    print("📊 Dashboard principal con tracking completo")
    print("🔗 URL: http://localhost:8081")
    print("-" * 50)
    
    dashboard = ScrapeBot_Dashboard(8081)
    
    # Intentar abrir navegador
    try:
        webbrowser.open("http://localhost:8081")
        print("🌐 Abriendo navegador automáticamente...")
    except:
        print("🌐 Abre manualmente: http://localhost:8081")
    
    try:
        dashboard.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard detenido")

if __name__ == "__main__":
    main()