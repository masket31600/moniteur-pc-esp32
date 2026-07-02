import psutil
import wmi
import subprocess

# Initialisation de l'interface WMI (pour la température CPU)
try:
    w = wmi.WMI(namespace=r"root\wmi")
except Exception as e:
    print(f"Attention: Impossible d'initialiser WMI ({e})")
    w = None

# Petit appel à vide obligatoire pour initialiser le calcul du CPU
psutil.cpu_percent(interval=0.1)

def get_all_metrics():
    """
    Récupère toutes les sondes et renvoie un dictionnaire propre.
    C'est ce dictionnaire qui sera envoyé à Home Assistant.
    """
    metrics = {
        "cpu_percent": 0.0,
        "ram_percent": 0.0,
        "cpu_temp": 0.0,
        "gpu_percent": 0.0,
        "gpu_temp": 0.0
    }

    # 1. Utilisation globale (CPU et RAM)
    metrics["cpu_percent"] = round(psutil.cpu_percent(interval=None), 1)
    metrics["ram_percent"] = round(psutil.virtual_memory().percent, 1)
    
    # 2. Température CPU via WMI
    if w:
        try:
            temperature_info = w.MSAcpi_ThermalZoneTemperature()
            if len(temperature_info) > 0:
                # Conversion des dixièmes de Kelvin en Celsius
                temp_c = (temperature_info[0].CurrentTemperature / 10.0) - 273.15
                metrics["cpu_temp"] = round(temp_c, 1)
        except Exception:
            pass 
        
    # 3. Carte Graphique (GPU) via l'outil natif Nvidia
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW # Empêche la console noire de clignoter
        )
        parts = output.strip().split(',')
        metrics["gpu_percent"] = float(parts[0].strip())
        metrics["gpu_temp"] = float(parts[1].strip())
    except Exception:
        pass # Si pas de carte Nvidia, les valeurs restent à 0.0

    return metrics

def format_for_esp32(metrics):
    """
    Transforme le dictionnaire en une chaîne de texte brute pour l'écran.
    Ex: C:45.0|R:60.0|G:80.0|Tc:55.0|Tg:65.0
    """
    return f"C:{metrics['cpu_percent']}|R:{metrics['ram_percent']}|G:{metrics['gpu_percent']}|Tc:{metrics['cpu_temp']}|Tg:{metrics['gpu_temp']}\n"