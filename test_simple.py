import pandas as pd
from datetime import datetime

# Simular el contenido del archivo shared_timestamp.txt
fecha_hora = "2025-07-08 12:00:00"
fechacompleta = pd.to_datetime(fecha_hora)
fecha = fechacompleta.date()

print(f"Fecha procesada: {fecha}")
print(f"Tipo de fecha: {type(fecha)}")
print("Test básico exitoso")