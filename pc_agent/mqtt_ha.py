import json
import paho.mqtt.client as mqtt

class HomeAssistantMQTT:
    def __init__(self, config):
        # EUREKA : On cible bien le bloc "home_assistant" du JSON pour extraire les identifiants
        ha_config = config.get("home_assistant", config) 

        self.broker = ha_config.get("mqtt_broker_ip", "")
        self.port = ha_config.get("mqtt_port", 1883)
        self.user = ha_config.get("mqtt_user", "")
        self.password = ha_config.get("mqtt_password", "")
        
        self.device_id = "pc_monitor"
        self.device_name = "Moniteur PC"
        self.state_topic = f"{self.device_id}/state"
        self.availability_topic = f"{self.device_id}/availability"
        
        # TES DEUX CAPTEURS DISTINCTS
        self.sensors = {
            "cpu_percent": {"name": "CPU Utilisation", "unit": "%", "icon": "mdi:cpu-64-bit"},
            "ram_percent": {"name": "RAM Utilisation", "unit": "%", "icon": "mdi:memory"},
            "cpu_temp": {"name": "CPU Température", "unit": "°C", "icon": "mdi:thermometer"},
            "cpu_power": {"name": "CPU Puissance", "unit": "W", "icon": "mdi:lightning-bolt"},
            "gpu_percent": {"name": "GPU Utilisation", "unit": "%", "icon": "mdi:expansion-card"},
            "gpu_temp": {"name": "GPU Température", "unit": "°C", "icon": "mdi:thermometer"},
            "gpu_power": {"name": "GPU Puissance", "unit": "W", "icon": "mdi:lightning-bolt"},
            "total_power": {"name": "Puissance Totale Estimée", "unit": "W", "icon": "mdi:power-plug"},
            "cpu_fan_rpm": {"name": "Ventilateur CPU", "unit": "RPM", "icon": "mdi:fan"},
            "gpu_fan_rpm": {"name": "Ventilateur GPU", "unit": "RPM", "icon": "mdi:fan"},
            "uptime": {"name": "Temps d'activité", "unit": "", "icon": "mdi:clock-outline"}
        }

        self.client = mqtt.Client(client_id="pc_monitor_agent")
        
        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

        self.client.will_set(self.availability_topic, payload="offline", retain=True)
        self.client.on_connect = self._on_connect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.client.publish(self.availability_topic, payload="online", retain=True)
            self._publish_discovery()
            print("✅ MQTT Connecté/Reconnecté : Statut 'online' et Auto-Discovery envoyés !")
        else:
            print(f"❌ Échec de connexion MQTT, code de retour : {rc}")

    def connect(self):
        print(f"--- DEBUG MQTT : Tentative vers l'IP lue dans le config.json -> {self.broker}:{self.port} ---")
        
        if not self.broker or self.broker == "192.168.1.X":
            print("MQTT ignoré (adresse IP manquante ou par défaut).")
            return False
            
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start() 
            return True
        except Exception as e:
            print(f"Erreur d'initialisation MQTT : {e}")
            return False

    def _publish_discovery(self):
        for sensor_id, sensor_info in self.sensors.items():
            discovery_topic = f"homeassistant/sensor/{self.device_id}/{sensor_id}/config"
            
            payload = {
                "name": sensor_info["name"],
                "state_topic": self.state_topic,
                "availability_topic": self.availability_topic,
                "payload_available": "online",
                "payload_not_available": "offline",
                "icon": sensor_info["icon"],
                "value_template": f"{{{{ value_json.{sensor_id} }}}}",
                "unique_id": f"{self.device_id}_{sensor_id}",
                "device": {
                    "identifiers": [self.device_id],
                    "name": self.device_name,
                    "manufacturer": "Custom Python Agent"
                }
            }
            
            if sensor_info["unit"]:
                payload["unit_of_measurement"] = sensor_info["unit"]
                
            self.client.publish(discovery_topic, json.dumps(payload), retain=True)

    def publish_metrics(self, metrics_dict):
        try:
            self.client.publish(self.state_topic, json.dumps(metrics_dict))
        except Exception:
            pass

    def disconnect(self):
        """Ferme proprement la connexion avec Home Assistant"""
        try:
            self.client.publish(self.availability_topic, payload="offline", retain=True)
            self.client.loop_stop()
            self.client.disconnect()
            print("MQTT déconnecté proprement.")
        except Exception:
            pass