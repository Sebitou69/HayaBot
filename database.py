import json
import os

DB_FILE = '/app/data/personajes.json'

def inicializar_db():
    if not os.path.exists(os.path.dirname(DB_FILE)):
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({"ocupados": {}, "deseados": {}, "actividad": {}}, f, indent=4)

def cargar_datos():
    inicializar_db()
    with open(DB_FILE, 'r') as f:
        try:
            datos = json.load(f)
        except:
            datos = {"ocupados": {}, "deseados": {}, "actividad": {}}
    
    for key in ["ocupados", "deseados", "actividad"]:
        if not isinstance(datos.get(key), dict):
            datos[key] = {}
    return datos

def guardar_datos(datos):
    with open(DB_FILE, 'w') as f:
        json.dump(datos, f, indent=4)
#init