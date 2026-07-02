# Agent Moniteur PC  - Home Assistant & ESP32

Un agent léger et invisible développé en Python pour Windows. Il surveille en temps réel les métriques matérielles et énergétiques du PC, puis les diffuse simultanément vers un écran ESP32 et vers Home Assistant via MQTT (avec Auto-Discovery).

## 🚀 Fonctionnalités
* **100% Invisible :** Conçu pour tourner en tâche de fond au démarrage de Windows (sans console).
* **Double Diffusion :** * Envoi d'une trame légère vers un ESP32 (détection automatique du mode USB / Série ou Wi-Fi / UDP).
  * Envoi des données complètes vers Home Assistant via MQTT.
* **Auto-Discovery MQTT :** Les capteurs s'ajoutent et se configurent automatiquement dans Home Assistant avec leurs unités et icônes.
* **Métriques avancées :** Températures, puissance électrique (Watts), charge CPU/GPU/RAM, vitesse des ventilateurs et temps d'activité.

---

## 🛠️ Prérequis : LibreHardwareMonitor

Pour contourner les sécurités de Windows et lire précisément les sondes de la carte mère (Watts, °C, RPM), cet agent s'appuie sur le serveur web local de *LibreHardwareMonitor*.

1. Téléchargez la dernière *Release* (.zip) sur [le GitHub officiel de LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases).
2. Extrayez le dossier où vous le souhaitez.
3. Faites un clic droit sur `LibreHardwareMonitor.exe` et choisissez **Exécuter en tant qu'administrateur** (Indispensable pour lire le CPU).
4. Dans le logiciel, allez dans le menu **Options** et configurez ceci :
   * Cochez `Run On Windows Startup`.
   * Cochez `Minimize To Tray`.
   * Dans `Remote Web Server`, laissez le port sur **8085** et cliquez sur **Run**.

---

## ⚙️ Configuration

Le projet utilise un fichier de configuration sécurisé pour éviter de stocker les mots de passe dans le code source.

1. Localisez le fichier `config.example.json` à la racine du projet.
2. Faites-en une copie et renommez-la en **`config.json`**.
3. Remplissez vos véritables informations à l'intérieur :

```json
{
  "esp32": {
    "udp_port": 1234,
    "baud_rate": 115200
  },
  "home_assistant": {
    "mqtt_broker_ip": "192.168.X.X",
    "mqtt_port": 1883,
    "mqtt_user": "votre_utilisateur",
    "mqtt_password": "votre_mot_de_passe"
  },
  "settings": {
    "update_interval_seconds": 1.0
  }
}
