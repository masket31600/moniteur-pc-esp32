import json
import time
import socket
import serial
import serial.tools.list_ports
import os
import sys
time.sleep(15) # Attend 15 secondes au démarrage

# Import de nos propres modules
import hardware
from mqtt_ha import HomeAssistantMQTT

def load_config():
    """Charge le fichier config.json situé à côté du script/exe."""
    # Cette astuce permet de trouver le config.json même une fois compilé en .exe
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        
    config_path = os.path.join(application_path, 'config.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur: Impossible de lire config.json ({e}).")
        # Valeurs de secours pour ne pas faire planter le programme
        return {"esp32": {"udp_port": 1234, "baud_rate": 115200}}

def get_esp_port():
    """Cherche dynamiquement si l'ESP32 est branché en USB."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if any(keyword in p.description for keyword in ["USB", "Serial", "CH340", "JTAG", "UART"]):
            return p.device
    return None

def main():
    print("=== Démarrage de l'Agent Moniteur PC ===")
    
    # 1. Chargement de la configuration
    config = load_config()
    esp_config = config.get("esp32", {})
    ha_config = config.get("home_assistant", {})
    settings = config.get("settings", {"update_interval_seconds": 1.0})
    
    udp_port = esp_config.get("udp_port", 1234)
    baud_rate = esp_config.get("baud_rate", 115200)
    update_interval = settings.get("update_interval_seconds", 1.0)

    # 2. Préparation du réseau UDP (pour l'ESP32 en Wi-Fi)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # 3. Initialisation de la connexion Home Assistant (MQTT)
    mqtt_client = HomeAssistantMQTT(ha_config)
    mqtt_client.connect()

    print(f"\nBoucle de surveillance active (Mise à jour : {update_interval}s).")
    print("Appuyez sur Ctrl+C pour quitter.")

    # 4. Boucle principale de fonctionnement
    while True:
        try:
            # A. Récupération des données via notre moteur matériel
            metrics_dict = hardware.get_all_metrics()
            
            # B. Envoi vers Home Assistant (Si connecté)
            mqtt_client.publish_metrics(metrics_dict)
            
            # C. Formatage et envoi vers l'écran ESP32
            esp_trame = hardware.format_for_esp32(metrics_dict)
            esp_port = get_esp_port()

            if esp_port:
                # Mode Câble USB
                try:
                    with serial.Serial(esp_port, baud_rate, timeout=1) as ser:
                        ser.write(esp_trame.encode('utf-8'))
                except Exception:
                    pass
            else:
                # Mode Wi-Fi (UDP Local)
                try:
                    sock.sendto(esp_trame.encode('utf-8'), ('<broadcast>', udp_port))
                except Exception:
                    pass
                    
            # Pause avant la prochaine lecture
            time.sleep(update_interval)
            
        except Exception as e:
            print(f"Erreur mineure dans la boucle : {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt du moniteur.")