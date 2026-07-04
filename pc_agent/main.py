import json
import time
import socket
import serial
import serial.tools.list_ports
import os
import sys
import threading
import tkinter as tk
from tkinter import colorchooser

import pystray
from PIL import Image, ImageDraw

# Imports des modules locaux
import hardware
from mqtt_ha import HomeAssistantMQTT

# --- VARIABLES GLOBALES ---
# Ces variables permettent aux deux threads (Interface et Moteur) de communiquer entre eux
config_data = {}
config_path = ""
force_config_send = False
stop_event = threading.Event()

def load_config():
    global config_path
    # Détection du dossier selon si on est en script (.py) ou compilé (.exe)
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        
    config_path = os.path.join(application_path, 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur de lecture config.json : {e}")
        # Valeurs par défaut de secours si le fichier est introuvable
        return {"esp32": {"udp_port": 1234, "baud_rate": 115200}, "affichage": {"seuil_alerte": 80}}

def save_config(new_config):
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2)
        print("Configuration sauvegardée avec succès.")
    except Exception as e:
        print(f"Erreur de sauvegarde : {e}")

def get_esp_port():
    # Cherche automatiquement l'ESP32 branché en USB
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if any(keyword in p.description for keyword in ["USB", "Serial", "CH340", "JTAG", "UART"]):
            return p.device
    return None

# ==========================================
# THREAD 1 : LE MOTEUR (Domotique & Matériel)
# ==========================================
def monitoring_loop():
    global force_config_send
    
    print("Moteur démarré en arrière-plan. Pause de 15s...")
    time.sleep(15) # Le fameux délai de démarrage pour LibreHardwareMonitor
    print("Reprise du moteur. Lancement de la surveillance.")
    
    esp_config = config_data.get("esp32", {})
    ha_config = config_data.get("home_assistant", {})
    settings = config_data.get("settings", {"update_interval_seconds": 1.0})
    
    udp_port = esp_config.get("udp_port", 1234)
    baud_rate = esp_config.get("baud_rate", 115200)
    update_interval = settings.get("update_interval_seconds", 1.0)

    # Préparation socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Préparation MQTT
    mqtt_client = HomeAssistantMQTT(ha_config)
    mqtt_client.connect()

    # Variable pour maintenir la connexion série ouverte
    ser = None

    while not stop_event.is_set():
        try:
            esp_port = get_esp_port()
            
            # --- GESTION DE LA CONNEXION USB (Empêche le reset en boucle) ---
            if esp_port:
                if ser is None or ser.port != esp_port:
                    if ser:
                        ser.close()
                    try:
                        ser = serial.Serial(esp_port, baud_rate, timeout=1)
                        # Désactiver les signaux DTR/RTS empêche certains ESP32 de redémarrer à chaque connexion
                        ser.setDTR(False) 
                        ser.setRTS(False)
                        print(f"✅ Connecté à l'écran sur {esp_port}")
                        time.sleep(1) # Laisse le temps à l'ESP de se réveiller
                    except Exception as e:
                        print(f"Erreur d'ouverture du port série: {e}")
                        ser = None
            else:
                if ser:
                    ser.close()
                    ser = None
            
            # --- INTERCEPTION : L'utilisateur a changé les réglages ---
            if force_config_send:
                aff = config_data.get("affichage", {})
                esp = config_data.get("esp32", {})
                
                # Format de la trame : CONFIG:#CPU|#RAM|#GPU|#ALERTE|SEUIL\n
                trame_config = f"CONFIG:{aff.get('couleur_cpu', '#00FF00')}|{aff.get('couleur_ram', '#0000FF')}|{aff.get('couleur_gpu', '#800080')}|{aff.get('couleur_alerte', '#FF0000')}|{aff.get('seuil_alerte', 80)}\n"
                trame_wifi = f"WIFI:{esp.get('ssid', '')}|{esp.get('password', '')}\n"
                
                if ser and ser.is_open:
                    try:
                        ser.write(trame_config.encode('utf-8'))
                        time.sleep(0.1) # Petite pause pour laisser l'ESP souffler
                        ser.write(trame_wifi.encode('utf-8'))
                        print("Trames de config et Wi-Fi envoyées via USB")
                    except Exception as e: print(f"Erreur USB Config: {e}")
                else:
                    try:
                        sock.sendto(trame_config.encode('utf-8'), ('<broadcast>', udp_port))
                        sock.sendto(trame_wifi.encode('utf-8'), ('<broadcast>', udp_port))
                        print("Trames de config et Wi-Fi envoyées via UDP")
                    except Exception as e: print(f"Erreur UDP Config: {e}")
                
                force_config_send = False # Trame envoyée, on désactive l'alarme
                time.sleep(0.5)

            # --- ROUTINE CLASSIQUE (Lecture et Envoi des sondes) ---
            metrics_dict = hardware.get_all_metrics()
            mqtt_client.publish_metrics(metrics_dict)
            esp_trame = hardware.format_for_esp32(metrics_dict)

            if ser and ser.is_open:
                try:
                    ser.write(esp_trame.encode('utf-8'))
                except Exception: pass
            else:
                try:
                    sock.sendto(esp_trame.encode('utf-8'), ('<broadcast>', udp_port))
                except Exception: pass
                
            time.sleep(update_interval)
            
        except Exception as e:
            print(f"Erreur boucle principale : {e}")
            time.sleep(1)
            
    # Fermeture propre si on quitte l'appli
    if ser:
        ser.close()

# ==========================================
# THREAD 2 : L'INTERFACE (Systray & Tkinter)
# ==========================================
def show_interface():
    global config_data, force_config_send
    
    # Création de la fenêtre
    root = tk.Tk()
    root.title("Configuration de l'Écran")
    root.geometry("340x480")
    root.eval('tk::PlaceWindow . center') # Centre la fenêtre à l'écran
    root.configure(bg="#f0f0f0")
    
    # Met la fenêtre au premier plan à l'ouverture
    root.attributes('-topmost', True)
    root.update()
    root.attributes('-topmost', False)

    aff = config_data.get("affichage", {})
    esp = config_data.get("esp32", {})
    
    # Variables Tkinter pour stocker les choix
    c_cpu = tk.StringVar(value=aff.get("couleur_cpu", "#00FF00"))
    c_ram = tk.StringVar(value=aff.get("couleur_ram", "#0000FF"))
    c_gpu = tk.StringVar(value=aff.get("couleur_gpu", "#800080"))
    c_alert = tk.StringVar(value=aff.get("couleur_alerte", "#FF0000"))
    s_alert = tk.IntVar(value=aff.get("seuil_alerte", 80))
    
    v_ssid = tk.StringVar(value=esp.get("ssid", ""))
    v_mdp = tk.StringVar(value=esp.get("password", ""))

    def pick_color(var, btn):
        color = colorchooser.askcolor(initialcolor=var.get(), title="Choisir une couleur", parent=root)[1]
        if color:
            var.set(color)
            btn.config(bg=color)

    tk.Label(root, text="Couleurs des jauges", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)

    # Fonction utilitaire pour générer les boutons de couleur proprement
    def make_color_row(label_text, var):
        frame = tk.Frame(root, bg="#f0f0f0")
        frame.pack(pady=3)
        tk.Label(frame, text=label_text, width=15, anchor="w", bg="#f0f0f0").pack(side="left")
        btn = tk.Button(frame, bg=var.get(), width=10, relief="solid", borderwidth=1)
        btn.config(command=lambda: pick_color(var, btn))
        btn.pack(side="left")

    make_color_row("Couleur CPU :", c_cpu)
    make_color_row("Couleur RAM :", c_ram)
    make_color_row("Couleur GPU :", c_gpu)
    make_color_row("Couleur Alerte :", c_alert)

    tk.Label(root, text="Seuil d'Alerte (%)", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=(15, 5))
    slider = tk.Scale(root, from_=50, to=100, orient="horizontal", variable=s_alert, bg="#f0f0f0", length=200)
    slider.pack()

    tk.Label(root, text="Réseau Wi-Fi de l'écran", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=(15, 5))
    
    frame_ssid = tk.Frame(root, bg="#f0f0f0")
    frame_ssid.pack(pady=2)
    tk.Label(frame_ssid, text="SSID :", width=12, anchor="w", bg="#f0f0f0").pack(side="left")
    tk.Entry(frame_ssid, textvariable=v_ssid, width=20).pack(side="left")

    frame_mdp = tk.Frame(root, bg="#f0f0f0")
    frame_mdp.pack(pady=2)
    tk.Label(frame_mdp, text="Mot de passe :", width=12, anchor="w", bg="#f0f0f0").pack(side="left")
    tk.Entry(frame_mdp, textvariable=v_mdp, show="*", width=20).pack(side="left")

    def on_save():
        global config_data, force_config_send
        # Mise à jour du dictionnaire en mémoire
        config_data.setdefault("affichage", {})
        config_data["affichage"]["couleur_cpu"] = c_cpu.get()
        config_data["affichage"]["couleur_ram"] = c_ram.get()
        config_data["affichage"]["couleur_gpu"] = c_gpu.get()
        config_data["affichage"]["couleur_alerte"] = c_alert.get()
        config_data["affichage"]["seuil_alerte"] = s_alert.get()
        
        config_data.setdefault("esp32", {})
        config_data["esp32"]["ssid"] = v_ssid.get().strip()
        config_data["esp32"]["password"] = v_mdp.get().strip()
        
        save_config(config_data)
        force_config_send = True # Déclenche l'envoi à l'ESP32 dans le thread Moteur
        root.destroy()

    tk.Button(root, text="Sauvegarder et Appliquer", command=on_save, bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(pady=20)
    
    # Lancement de la boucle Tkinter dans ce thread séparé
    root.mainloop()

def open_config_window(icon, item):
    # On lance l'interface dans un processus à part pour ne pas bloquer le systray
    t = threading.Thread(target=show_interface, daemon=True)
    t.start()

def quit_app(icon, item):
    stop_event.set() # Stoppe la boucle du moteur
    icon.stop()      # Stoppe l'icône systray

def create_icon_image():
    # Génère un petit rond vert dynamiquement pour l'icône de la barre des tâches (évite de fournir un .ico)
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((8, 8, 56, 56), fill=(0, 200, 0)) # Un beau cercle vert
    return image

# ==========================================
# POINT D'ENTRÉE PRINCIPAL
# ==========================================
if __name__ == "__main__":
    config_data = load_config()

    # 1. On lance le moteur matériel dans un thread séparé (en arrière-plan)
    # Le paramètre daemon=True permet de tuer ce thread proprement à la fermeture de l'app
    motor_thread = threading.Thread(target=monitoring_loop, daemon=True)
    motor_thread.start()

    # 2. Le thread principal est dédié au maintien de l'icône système
    menu = pystray.Menu(
        pystray.MenuItem('Configuration', open_config_window),
        pystray.MenuItem('Quitter', quit_app)
    )
    
    icon = pystray.Icon("MoniteurPC", create_icon_image(), "Moniteur PC Agent", menu)
    
    try:
        icon.run() # Cette ligne bloque le script et garde l'application ouverte
    except KeyboardInterrupt:
        quit_app(icon, None)