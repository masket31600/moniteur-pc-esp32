import psutil
import subprocess
import json
import urllib.request
import time

def get_lhm_data():
    """Récupère le JSON brut de LibreHardwareMonitor s'il est actif."""
    try:
        url = "http://localhost:8085/data.json"
        with urllib.request.urlopen(url, timeout=0.5) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None

def parse_lhm_sensors(node, dict_res, current_category=""):
    """Parcourt récursivement l'arbre de LHM pour extraire les sondes clés."""
    text = node.get("Text", "")
    val_str = node.get("Value", "")
    
    # Repérage basique pour savoir si on lit les ventilateurs du GPU ou du reste du PC
    if any(k in text.upper() for k in ["NVIDIA", "RADEON", "GPU"]):
        current_category = "GPU"
        
    # Extraction de la valeur numérique si elle existe
    if val_str:
        try:
            # Nettoyage d'origine (ex: "45.2 °C" -> 45.2, "25.3 W" -> 25.3)
            val_num = float(val_str.split()[0].replace(",", "."))
            
            # Repérage des capteurs par leur nom dans l'arbre
            if text == "CPU Package" and "W" in val_str:
                dict_res["cpu_power"] = round(val_num, 1)
            elif text == "CPU Package" and "°C" in val_str:
                dict_res["cpu_temp"] = round(val_num, 1)
            elif text == "GPU Power" and "W" in val_str:
                dict_res["gpu_power"] = round(val_num, 1)
            elif text == "GPU Core" and "°C" in val_str:
                dict_res["gpu_temp"] = round(val_num, 1)
                
            # Séparation propre des ventilateurs pour Home Assistant
            elif "Fan" in text and "RPM" in val_str:
                rpm_val = int(val_num)
                if current_category == "GPU":
                    if rpm_val > dict_res.get("gpu_fan_rpm", 0):
                        dict_res["gpu_fan_rpm"] = rpm_val
                else:
                    if rpm_val > dict_res.get("cpu_fan_rpm", 0):
                        dict_res["cpu_fan_rpm"] = rpm_val
        except Exception:
            pass

    # Descente dans les enfants de l'arbre JSON
    for child in node.get("Children", []):
        parse_lhm_sensors(child, dict_res, current_category)

def get_all_metrics():
    """Collecte l'intégralité des métriques (Natives + LibreHardwareMonitor)."""
    # Valeurs par défaut mises à jour avec cpu_fan et gpu_fan
    metrics = {
        "cpu_percent": round(psutil.cpu_percent(interval=None), 1),
        "ram_percent": round(psutil.virtual_memory().percent, 1),
        "cpu_temp": 0.0,
        "cpu_power": 0.0,
        "gpu_percent": 0.0,
        "gpu_temp": 0.0,
        "gpu_power": 0.0,
        "total_power": 0.0,
        "cpu_fan_rpm": 0,
        "gpu_fan_rpm": 0,
        "uptime": "0h 0m"
    }

    # 1. Calcul de l'Uptime (Temps d'activité du PC)
    uptime_seconds = time.time() - psutil.boot_time()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    metrics["uptime"] = f"{hours}h {minutes}m"

    # 2. Récupération des données via LibreHardwareMonitor
    lhm_json = get_lhm_data()
    if lhm_json:
        parse_lhm_sensors(lhm_json, metrics)
        
    # 3. Secours / Complément GPU via Nvidia-SMI
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        parts = output.strip().split(',')
        metrics["gpu_percent"] = float(parts[0].strip())
        if metrics["gpu_temp"] == 0.0:
            metrics["gpu_temp"] = float(parts[1].strip())
        if metrics["gpu_power"] == 0.0:
            metrics["gpu_power"] = float(parts[2].strip())
    except Exception:
        pass

    # 4. Calcul de la puissance totale estimée du PC
    if metrics["cpu_power"] > 0 or metrics["gpu_power"] > 0:
        metrics["total_power"] = round(metrics["cpu_power"] + metrics["gpu_power"] + 40.0, 1)

    return metrics

def format_for_esp32(metrics):
    """Trame immuable destinée à l'écran pour ne pas le surcharger."""
    return f"C:{metrics['cpu_percent']}|R:{metrics['ram_percent']}|G:{metrics['gpu_percent']}|Tc:{metrics['cpu_temp']}|Tg:{metrics['gpu_temp']}\n"