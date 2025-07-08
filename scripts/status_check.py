#!/usr/bin/env python3
"""
Script para verificar el estado del sistema de scraping
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Añadir el directorio padre al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.metrics import metrics_collector
from core.alerts import alert_manager

def check_system_health() -> dict:
    """Verifica el estado general del sistema."""
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'issues': [],
        'warnings': []
    }
    
    try:
        # Verificar métricas recientes
        recent_metrics = metrics_collector.get_historical_metrics(1)  # Último día
        
        if not recent_metrics:
            health['warnings'].append("No hay métricas de las últimas 24 horas")
        else:
            last_session = recent_metrics[-1]
            
            # Verificar si la última sesión fue exitosa
            if last_session.overall_success_rate < 50:
                health['issues'].append(f"Última sesión tuvo baja tasa de éxito: {last_session.overall_success_rate:.1f}%")
                health['status'] = 'degraded'
            
            # Verificar si hay módulos que fallan consistentemente
            failed_modules = [m for m in last_session.modules if m.status == 'failed']
            if failed_modules:
                health['warnings'].append(f"Módulos fallidos en última sesión: {[m.module_name for m in failed_modules]}")
        
        # Verificar archivos de log recientes
        log_dir = Path("logs")
        if log_dir.exists():
            today_log = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"
            if not today_log.exists():
                health['warnings'].append("No hay logs del día actual")
        else:
            health['issues'].append("Directorio de logs no existe")
            health['status'] = 'unhealthy'
        
        # Verificar configuración de alertas
        if not any([
            alert_manager.config['email']['enabled'],
            alert_manager.config['slack']['enabled'],
            alert_manager.config['webhook']['enabled']
        ]):
            health['warnings'].append("No hay sistemas de alertas habilitados")
        
        # Verificar archivos críticos
        critical_files = [
            Path(".env"),
            Path("config/settings.py"),
            Path("main.py")
        ]
        
        for file_path in critical_files:
            if not file_path.exists():
                health['issues'].append(f"Archivo crítico faltante: {file_path}")
                health['status'] = 'unhealthy'
    
    except Exception as e:
        health['issues'].append(f"Error verificando sistema: {str(e)}")
        health['status'] = 'unhealthy'
    
    return health

def generate_status_report(days: int = 7) -> dict:
    """Genera reporte de estado detallado."""
    try:
        summary = metrics_collector.generate_summary_report(days)
        health = check_system_health()
        
        return {
            'health_check': health,
            'performance_summary': summary,
            'alert_config': {
                'email_enabled': alert_manager.config['email']['enabled'],
                'slack_enabled': alert_manager.config['slack']['enabled'],
                'webhook_enabled': alert_manager.config['webhook']['enabled']
            }
        }
    except Exception as e:
        return {
            'error': f"Error generando reporte: {str(e)}",
            'timestamp': datetime.now().isoformat()
        }

def print_status_summary():
    """Imprime resumen de estado en consola."""
    health = check_system_health()
    
    # Emoji según estado
    status_emoji = {
        'healthy': '✅',
        'degraded': '⚠️',
        'unhealthy': '❌'
    }
    
    print(f"\n🤖 ScrapeBot - Estado del Sistema")
    print(f"{'='*50}")
    print(f"Estado: {status_emoji.get(health['status'], '❓')} {health['status'].upper()}")
    print(f"Verificado: {datetime.fromisoformat(health['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    
    if health['issues']:
        print(f"\n❌ Problemas críticos:")
        for issue in health['issues']:
            print(f"  • {issue}")
    
    if health['warnings']:
        print(f"\n⚠️ Advertencias:")
        for warning in health['warnings']:
            print(f"  • {warning}")
    
    if not health['issues'] and not health['warnings']:
        print(f"\n🎉 Sistema funcionando correctamente")
    
    # Mostrar métricas recientes si disponibles
    try:
        summary = metrics_collector.generate_summary_report(7)
        if summary and not summary.get('error'):
            print(f"\n📊 Últimos 7 días:")
            print(f"  • Sesiones exitosas: {summary['session_success_rate']:.1f}%")
            print(f"  • Módulos exitosos: {summary['module_success_rate']:.1f}%")
            print(f"  • Descargas exitosas: {summary['download_success_rate']:.1f}%")
    except:
        pass
    
    print()

def main():
    parser = argparse.ArgumentParser(description='Verificar estado del sistema de scraping')
    parser.add_argument('--json', action='store_true', help='Salida en formato JSON')
    parser.add_argument('--days', type=int, default=7, help='Días para reporte histórico')
    parser.add_argument('--health-only', action='store_true', help='Solo verificación de salud')
    
    args = parser.parse_args()
    
    try:
        if args.health_only:
            result = check_system_health()
        else:
            result = generate_status_report(args.days)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_status_summary()
            
        # Exit code según estado
        if args.health_only:
            sys.exit(0 if result['status'] == 'healthy' else 1)
        else:
            health_status = result.get('health_check', {}).get('status', 'unhealthy')
            sys.exit(0 if health_status == 'healthy' else 1)
            
    except Exception as e:
        if args.json:
            print(json.dumps({'error': str(e), 'timestamp': datetime.now().isoformat()}))
        else:
            print(f"❌ Error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()