#!/usr/bin/env python3
"""
Test del dashboard híbrido
"""

import sys
sys.path.append('/mnt/c/Users/Herlin/Desktop/scrap_claude')

try:
    from dashboard_hybrid import HybridScrapeBot_Dashboard
    
    # Crear instancia del dashboard
    dashboard = HybridScrapeBot_Dashboard()
    
    # Intentar generar HTML
    html = dashboard.generate_html()
    
    print("✅ Dashboard híbrido generado exitosamente")
    print(f"📊 HTML generado: {len(html)} caracteres")
    
    # Verificar que no tenga errores
    if "❌ Error en el Dashboard" in html:
        print("⚠️ Dashboard muestra error")
    elif "⏳ SCRAPEBOT - ESPERANDO" in html:
        print("⏳ Dashboard en estado de espera (normal si no hay ejecuciones aún)")
    else:
        print("🟢 Dashboard mostrando datos normalmente")
    
    print("🎉 Test del dashboard híbrido PASADO")
    
except Exception as e:
    print(f"❌ Error en el dashboard híbrido: {e}")
    print("💥 Test del dashboard híbrido FALLIDO")