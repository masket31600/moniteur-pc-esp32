Moniteur PC - ESP32-C3 & GC9A01 🚀

Un moniteur de performances PC élégant et autonome basé sur un écran LCD rond (GC9A01) et un microcontrôleur ESP32-C3. Il affiche en temps réel la charge du CPU, de la RAM et du GPU sous forme de jauges circulaires fluides, ainsi que les températures au centre.

✨ Fonctionnalités

Affichage Fluide : Jauges avec anti-aliasing sans aucun scintillement (flickering).

Double Connectivité : Fonctionne via USB (Série) ou sans fil via Wi-Fi (UDP).

Interface Windows Discrète : Un agent Python tourne dans la zone de notification (Systray) de Windows.

Configuration Dynamique : Modifiez les couleurs des jauges, le réseau Wi-Fi et les seuils d'alerte directement depuis l'interface Windows (sauvegardé dans la mémoire de l'ESP32).

Alerte Thermique/Charge : Les jauges virent au rouge si un seuil défini est dépassé.

Écran de Veille Automatique : Affiche l'état de la connexion (Wi-Fi, Agent PC, Monitoring) si le PC est éteint.

Intégration Home Assistant (MQTT) : Remonte automatiquement les statistiques de votre PC dans votre domotique via MQTT (Auto-Discovery).

🛠️ Matériel & Câblage (ESP32-C3)

Un microcontrôleur ESP32-C3 (DevKitM-1 ou similaire).

Un écran TFT LCD Rond GC9A01 (1.28 pouces, SPI).

Câbles Dupont.

Voici le câblage exact à respecter pour ce projet :

| Écran GC9A01 | ESP32-C3 |
| ------------ | -------- |
| VCC          | 3V3      |
| GND          | GND      |
| RST          | GPIO 0   |
| CS           | GPIO 1   |
| DC           | GPIO 10  |
| SDA (MOSI)   | GPIO 3   |
| SCL (SCLK)   | GPIO 4   |


🚀 Installation Rapide (Prêt à l'emploi)

Vous ne voulez pas compiler le code vous-même ? Des fichiers prêts à l'emploi sont disponibles dans la section Releases du projet !

1. Flasher l'ESP32 (Le firmware .bin)

Téléchargez le fichier firmware.bin depuis les Releases.

Branchez votre ESP32-C3 en USB.

Utilisez un outil comme ESP Web Tools (depuis un navigateur Chrome/Edge) ou l'outil de flash d'Espressif pour envoyer le .bin sur la carte à l'adresse 0x00000.

2. Lancer l'Agent PC (L'exécutable .exe)

L'agent utilise LibreHardwareMonitor pour lire les capteurs de votre PC.

Téléchargez et lancez LibreHardwareMonitor. Allez dans Options et cochez Run on Windows Startup et Start Minimized.

Téléchargez l'archive de l'agent PC depuis les Releases et extrayez-la dans un dossier.

Lancez MoniteurPC.exe.

Une icône verte apparaîtra dans votre barre des tâches (en bas à droite). Faites un clic droit > Configuration pour choisir vos couleurs et entrer vos identifiants Wi-Fi !

(Astuce : Placez un raccourci de MoniteurPC.exe dans votre dossier de démarrage Windows shell:startup pour qu'il se lance tout seul !)

💻 Installation Avancée (Compilation depuis les sources)

Si vous souhaitez modifier le code ou compiler vous-même le projet :

1. Côté ESP32 (Firmware C++)

Ouvrez le dossier esp32_display avec VS Code + PlatformIO.

Le fichier platformio.ini est déjà configuré avec les bonnes broches (build_flags) et la bibliothèque TFT_eSPI.

Cliquez sur l'icône de fourmi puis sur Upload pour compiler et flasher l'ESP32.

2. Côté PC (Agent Python)

Assurez-vous d'avoir Python 3.x installé.

Ouvrez un terminal dans le dossier pc_agent.

Installez les dépendances : pip install -r requirements.txt.

Testez le script avec : python main.py.

Pour générer vous-même l'exécutable Windows sans console (.exe), lancez la commande suivante :

pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --add-data "config.json;." main.py


Réalisé avec passion.
