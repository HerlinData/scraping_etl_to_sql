#!/usr/bin/env python3
"""
Test simple para verificar que el dashboard no tenga errores de NoneType
"""

import sys
sys.path.append('/mnt/c/Users/Herlin/Desktop/scrap_claude')

try:
    from dashboard import ScrapeBot_Dashboard
    
    # Crear instancia del dashboard
    dashboard = ScrapeBot_Dashboard()
    
    # Intentar generar HTML
    html = dashboard.generate_html()
    
    print("✅ Dashboard generado exitosamente")
    print(f"📊 HTML generado: {len(html)} caracteres")
    print("🎉 Test del dashboard PASADO")
    
except Exception as e:
    print(f"❌ Error en el dashboard: {e}")
    print("💥 Test del dashboard FALLIDO")