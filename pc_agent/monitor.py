import psutil
import serial
import serial.tools.list_ports
import socket
import time
import wmi
import subprocess

# --- Configuration ---
UDP_PORT = 1234
BAUD_RATE = 115200
UPDATE_INTERVAL = 1.0

# Initialisation de l'interface WMI pour la température CPU
try:
    w = wmi.WMI(namespace=r"root\wmi")
except Exception as e:
    print(f"Attention: Impossible d'initialiser WMI pour la température CPU ({e})")
    w = None

def get_esp_port():
    """Cherche dynamiquement si l'ESP32 est branché en USB."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if any(keyword in p.description for keyword in ["USB", "Serial", "CH340", "JTAG", "UART"]):
            return p.device
    return None

def get_system_metrics():
    # 1. Utilisation globale (CPU et RAM)
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    
    # 2. Température CPU via WMI
    temp_cpu = 0.0
    if w:
        try:
            temperature_info = w.MSAcpi_ThermalZoneTemperature()
            if len(temperature_info) > 0:
                temp_cpu = (temperature_info[0].CurrentTemperature / 10.0) - 273.15
        except Exception:
            temp_cpu = 0.0 
        
    # 3. Carte Graphique (GPU : Charge et Température) via l'outil natif Nvidia
    gpu_usage = 0.0
    temp_gpu = 0.0
    try:
        # Appel direct au pilote Nvidia (fonctionne sur 99% des PC équipés Nvidia)
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW # Empêche la console noire de clignoter
        )
        parts = output.strip().split(',')
        gpu_usage = float(parts[0].strip())
        temp_gpu = float(parts[1].strip())
    except Exception:
        pass # Si pas de carte Nvidia ou erreur, les valeurs restent à 0.0
    
    # Formatage de la trame de données finale
    return f"C:{cpu:.1f}|R:{ram:.1f}|G:{gpu_usage:.1f}|Tc:{temp_cpu:.1f}|Tg:{temp_gpu:.1f}\n"

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print("Démarrage du moniteur 3 axes (CPU/GPU/RAM)...")
    psutil.cpu_percent(interval=0.1)

    while True:
        metrics = get_system_metrics()
        esp_port = get_esp_port()

        if esp_port:
            try:
                with serial.Serial(esp_port, BAUD_RATE, timeout=1) as ser:
                    ser.write(metrics.encode('utf-8'))
                    print(f"[USB] Trame envoyée : {metrics.strip()}")
            except Exception:
                pass
        else:
            try:
                sock.sendto(metrics.encode('utf-8'), ('<broadcast>', UDP_PORT))
                print(f"[UDP] Trame diffusée : {metrics.strip()}")
            except Exception:
                pass

        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt du moniteur.")