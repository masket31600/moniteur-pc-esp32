# 🖥️ Moniteur Matériel PC sur Écran Rond (ESP32-C3 & GC9A01)

Ce projet permet de transformer un écran rond LCD (pilote GC9A01) connecté à un microcontrôleur ESP32-C3 en un tableau de bord physique et esthétique pour surveiller les performances de votre PC en temps réel.

Il affiche 3 jauges circulaires concentriques ainsi que les températures clés.

## 📊 Métriques Surveillées
* **Couronne Extérieure (Bleue) :** Utilisation du CPU (%) & Température CPU (°C)
* **Couronne Intermédiaire (Verte) :** Utilisation du GPU (%) & Température GPU (°C)
* **Couronne Intérieure (Violette) :** Utilisation de la mémoire RAM (%)

---

## 🛠️ Architecture du Projet

Le projet est divisé en deux parties distinctes :

1.  📁 **`pc_agent/` (Python) :** Un script léger qui tourne en tâche de fond sur le PC Windows. Il récolte les données matérielles et les diffuse.
2.  📁 **`esp32_display/` (C++ / PlatformIO) :** Le code du microcontrôleur qui écoute le réseau ou le port série, décode les informations et gère l'affichage graphique lissé.

### 🔌 Modes de Connexion (Hybride)
Le système est **Plug & Play** et bascule automatiquement selon la situation :
* **Prioritaire (Câble USB) :** Si l'ESP32 est branché directement sur le PC, les données sont envoyées instantanément via la liaison Série (UART).
* **Repli (Wi-Fi UDP) :** Si l'ESP32 est alimenté sur secteur ailleurs dans la pièce, le script PC diffuse les données en *Broadcast UDP* sur le réseau local. L'écran attrape les paquets sans avoir besoin de figer son adresse IP.

---

## 📐 Câblage Matériel (Brochage SPI)

Connectez l'écran rond **GC9A01** à l'**ESP32-C3** selon le schéma suivant :

| Écran GC9A01 | ESP32-C3 | Rôle / Description |
| :--- | :--- | :--- |
| **VCC** | 3.3V | Alimentation positive |
| **GND** | GND | Masse |
| **SCL** | GPIO 4 | Horloge SPI (SCK) |
| **SDA** | GPIO 5 | Données SPI (MOSI) |
| **RES** | GPIO 2 | Réinitialisation (Reset) |
| **DC** | GPIO 3 | Sélection Data / Commande |
| **CS** | GPIO 7 | Sélection du composant (Chip Select) |
| **BLK** | 3.3V | Rétroéclairage (Allumé en permanence) |

---

## 🚀 Installation et Démarrage

### 1. Configuration de l'ESP32-C3
Le projet utilise **PlatformIO** dans VS Code. La configuration de l'écran est entièrement gérée via les drapeaux de compilation (`build_flags`) dans le fichier `platformio.ini`, ce qui évite de modifier manuellement la bibliothèque `TFT_eSPI`.

1.  Ouvrez le dossier `esp32_display` dans VS Code avec PlatformIO.
2.  Connectez votre ESP32 en USB.
3.  Cliquez sur la flèche **Téléverser (➔)** en bas de VS Code pour compiler et flasher l'appareil.

*Note : Au premier démarrage, l'écran affichera "Configurez via USB" si aucun Wi-Fi n'est enregistré.*

### 2. Lancement de l'Agent PC (Windows)
L'agent requiert Python 3.12+ et l'accès aux sondes Windows (WMI) ainsi qu'aux outils Nvidia (`nvidia-smi`).

1.  Ouvrez votre terminal dans le dossier `pc_agent`.
2.  Installez les dépendances nécessaires :
    ```bash
    python -m pip install psutil pyserial wmi
    ```
3.  Lancez le moniteur :
    ```bash
    python monitor.py
    ```

---

## 📝 Format de la Trame Réseau (Protocole)
Les données sont transmises une fois par seconde sous forme d'une chaîne de caractères brute textuelle standardisée :
`C:CPU_UTIL|R:RAM_UTIL|G:GPU_UTIL|Tc:CPU_TEMP|Tg:GPU_TEMP`

*Exemple de trame réelle envoyée :* `C:12.5|R:45.8|G:8.0|Tc:49.0|Tg:38.0`

---
## 📄 Licence
Projet personnel - Créé pour le monitoring matériel personnalisé.
# moniteur-pc-esp32