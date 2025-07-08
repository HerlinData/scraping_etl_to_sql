#!/usr/bin/env python3
"""
Script para ver y consultar la base de datos de procesos
"""
import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta

# Añadir el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import process_db

def view_recent_sessions(limit=10):
    """Muestra las sesiones más recientes."""
    sessions = process_db.get_recent_sessions(limit)
    
    if not sessions:
        print("📊 No hay sesiones registradas")
        return
    
    print(f"📋 Últimas {len(sessions)} sesiones:")
    print("-" * 80)
    print(f"{'Hora':<8} {'Estado':<15} {'Módulos':<10} {'Duración':<10} {'Notas'}")
    print("-" * 80)
    
    for session in sessions:
        started = session.get('started_at', '')
        status = session.get('status', 'unknown')
        total = session.get('total_modules', 0)
        successful = session.get('successful_modules', 0)
        duration = session.get('duration_seconds', 0)
        notes = session.get('notes', '')[:20] + '...' if session.get('notes', '') else ''
        
        try:
            time_str = datetime.fromisoformat(started).strftime('%H:%M') if started else 'N/A'
        except:
            time_str = 'N/A'
        
        status_emoji = {
            'success': '✅',
            'partial_success': '⚠️',
            'failed': '❌',
            'error': '💥',
            'running': '🔄'
        }.get(status, '⏳')
        
        print(f"{time_str:<8} {status_emoji} {status:<13} {successful}/{total:<8} {duration:.1f}s{'':<5} {notes}")

def view_session_details(session_id):
    """Muestra detalles de una sesión específica."""
    modules = process_db.get_session_modules(session_id)
    
    if not modules:
        print(f"❌ No se encontraron módulos para la sesión {session_id}")
        return
    
    print(f"📊 Detalles de la sesión: {session_id}")
    print("-" * 100)
    print(f"{'Módulo':<30} {'Estado':<12} {'Intentos':<8} {'Duración':<10} {'Error'}")
    print("-" * 100)
    
    for module in modules:
        name = module.get('module_name', 'N/A')
        status = module.get('status', 'unknown')
        attempts = module.get('attempts', 1)
        duration = module.get('duration_seconds', 0)
        error = module.get('error_message', '')[:30] + '...' if module.get('error_message') else ''
        
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'running': '🔄'
        }.get(status, '⏳')
        
        print(f"{name:<30} {status_emoji} {status:<10} {attempts:<8} {duration:.1f}s{'':<5} {error}")

def view_daily_summary(date=None):
    """Muestra resumen de un día específico."""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    summary = process_db.get_daily_summary(date)
    
    print(f"📊 Resumen del día: {date}")
    print("=" * 50)
    
    session_stats = summary['sessions']
    module_stats = summary['modules']
    
    print(f"📋 Sesiones:")
    print(f"   Total: {session_stats['total']}")
    print(f"   Exitosas: {session_stats['successful']}")
    print(f"   Fallidas: {session_stats['failed']}")
    print(f"   Duración promedio: {session_stats['avg_duration']:.1f} segundos")
    
    print(f"\n🔧 Módulos:")
    print(f"   Total ejecuciones: {module_stats['total_executions']}")
    print(f"   Ejecuciones exitosas: {module_stats['successful_executions']}")
    
    problematic = module_stats.get('problematic_modules', [])
    if problematic:
        print(f"\n⚠️ Módulos problemáticos:")
        for module in problematic[:5]:
            if module['failures'] > 0:
                print(f"   • {module['name']}: {module['failures']} fallos de {module['executions']} ejecuciones")

def cleanup_old_data(days):
    """Limpia datos antiguos."""
    print(f"🧹 Limpiando registros anteriores a {days} días...")
    deleted = process_db.cleanup_old_records(days)
    print(f"✅ Se eliminaron {deleted} registros antiguos")

def export_data(output_file):
    """Exporta datos a un archivo JSON."""
    import json
    
    print(f"📤 Exportando datos a {output_file}...")
    
    data = {
        'recent_sessions': process_db.get_recent_sessions(50),
        'daily_summary': process_db.get_daily_summary(),
        'export_timestamp': datetime.now().isoformat()
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Datos exportados a {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Visor de base de datos de procesos de scraping')
    parser.add_argument('--recent', type=int, default=10, help='Mostrar N sesiones recientes')
    parser.add_argument('--session', type=str, help='Mostrar detalles de una sesión específica')
    parser.add_argument('--daily', type=str, help='Mostrar resumen diario (YYYY-MM-DD)')
    parser.add_argument('--cleanup', type=int, help='Limpiar registros anteriores a N días')
    parser.add_argument('--export', type=str, help='Exportar datos a archivo JSON')
    
    args = parser.parse_args()
    
    try:
        if args.session:
            view_session_details(args.session)
        elif args.daily is not None:
            view_daily_summary(args.daily if args.daily else None)
        elif args.cleanup:
            cleanup_old_data(args.cleanup)
        elif args.export:
            export_data(args.export)
        else:
            view_recent_sessions(args.recent)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()