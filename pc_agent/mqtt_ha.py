import json
import paho.mqtt.client as mqtt

class HomeAssistantMQTT:
    def __init__(self, config):
        # Récupération des identifiants depuis le config.json
        self.broker = config.get("mqtt_broker_ip", "")
        self.port = config.get("mqtt_port", 1883)
        self.user = config.get("mqtt_user", "")
        self.password = config.get("mqtt_password", "")
        
        # Identité de l'appareil dans Home Assistant
        self.device_id = "pc_monitor"
        self.device_name = "Moniteur PC"
        self.state_topic = f"{self.device_id}/state"
        
        # Le catalogue des capteurs qui seront créés automatiquement
        self.sensors = {
            "cpu_percent": {"name": "CPU Utilisation", "unit": "%", "icon": "mdi:cpu-64-bit"},
            "ram_percent": {"name": "RAM Utilisation", "unit": "%", "icon": "mdi:memory"},
            "cpu_temp": {"name": "CPU Température", "unit": "°C", "icon": "mdi:thermometer"},
            "gpu_percent": {"name": "GPU Utilisation", "unit": "%", "icon": "mdi:expansion-card"},
            "gpu_temp": {"name": "GPU Température", "unit": "°C", "icon": "mdi:thermometer"}
        }

        self.client = mqtt.Client(client_id="pc_monitor_agent")
        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

    def connect(self):
        """Tente de se connecter au broker MQTT."""
        # Sécurité : Si l'utilisateur n'a pas rempli le config.json, on ignore l'étape HA
        if not self.broker or self.broker == "192.168.1.X":
            print("MQTT ignoré (adresse IP non configurée).")
            return False
            
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            self._publish_discovery()
            print("Connexion MQTT réussie et Auto-Discovery envoyé !")
            return True
        except Exception as e:
            print(f"Erreur de connexion MQTT : {e}")
            return False

    def _publish_discovery(self):
        """Envoie les trames de configuration pour créer les entités dans HA."""
        for sensor_id, sensor_info in self.sensors.items():
            # Le chemin (topic) officiel demandé par Home Assistant pour l'Auto-Discovery
            discovery_topic = f"homeassistant/sensor/{self.device_id}/{sensor_id}/config"
            
            payload = {
                "name": sensor_info["name"],
                "state_topic": self.state_topic,
                "unit_of_measurement": sensor_info["unit"],
                "icon": sensor_info["icon"],
                "value_template": f"{{{{ value_json.{sensor_id} }}}}",
                "unique_id": f"{self.device_id}_{sensor_id}",
                "device": {
                    "identifiers": [self.device_id],
                    "name": self.device_name,
                    "manufacturer": "Custom Python Agent"
                }
            }
            # retain=True permet à HA de recréer les capteurs même s'il redémarre
            self.client.publish(discovery_topic, json.dumps(payload), retain=True)

    def publish_metrics(self, metrics_dict):
        """Envoie les valeurs lues par hardware.py sur le réseau."""
        # On transforme le dictionnaire Python en texte JSON propre
        if self.client.is_connected():
            self.client.publish(self.state_topic, json.dumps(metrics_dict))