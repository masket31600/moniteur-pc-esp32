#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiUdp.h>

TFT_eSPI tft = TFT_eSPI();
Preferences preferences;
WiFiUDP udp;

// Configuration des angles stricts (0 étant en bas, 60 à 300 fait l'ouverture vers le haut)
const int START_ANGLE = 60; 
const int END_ANGLE = 300;

// Mémoires d'angles
int last_angle_cpu = START_ANGLE;
int last_angle_ram = START_ANGLE;
int last_angle_gpu = START_ANGLE;

// Mémoires des températures
int last_tc = -1;
int last_tg = -1;

// Timeout et Statut
unsigned long lastDataTime = 0;
bool statusScreenActive = false;
const unsigned long TIMEOUT_MS = 3000; // 3 secondes sans données déclenche l'écran de statut

// Réseau
String ssid = "";
String password = "";
unsigned int localUdpPort = 1234;
char incomingPacket[255]; 

// Couleurs (Variables dynamiques pour correspondre au PC)
uint16_t color_cpu = TFT_GREEN;
uint16_t color_ram = TFT_BLUE;
uint16_t color_gpu = TFT_MAGENTA;
uint16_t color_alerte = TFT_RED;
int seuil_alerte = 80;

// Convertisseur Hex vers RGB565 pour lire la configuration du PC
uint16_t hexToRGB565(String hex) {
    long rgb = strtol(hex.substring(1).c_str(), NULL, 16);
    return tft.color565((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF);
}

// Fonction pour dessiner la légende
void drawLegend() {
    tft.setTextDatum(MC_DATUM); // Centrage parfait
    
    tft.setTextColor(color_gpu, TFT_BLACK);
    tft.drawString("GPU", 120, 180, 2);    

    tft.setTextColor(color_ram, TFT_BLACK);
    tft.drawString("RAM", 120, 200, 2);
    
    tft.setTextColor(color_cpu, TFT_BLACK);
    tft.drawString("CPU", 120, 220, 2);
}

// Fonction pour dessiner l'écran de statut/déconnexion
void drawStatusScreen() {
    statusScreenActive = true;
    tft.fillScreen(TFT_BLACK);
    tft.setTextDatum(MC_DATUM);
    
    // 1. Statut Wi-Fi
    if (WiFi.status() == WL_CONNECTED) {
        tft.setTextColor(TFT_GREEN, TFT_BLACK);
        tft.drawString("WiFi = OK", 120, 90, 2);
    } else {
        tft.setTextColor(TFT_RED, TFT_BLACK);
        tft.drawString("WiFi = Fail", 120, 90, 2);
    }
    
    // 2. Statut PC (L'exécutable est éteint)
    tft.setTextColor(TFT_ORANGE, TFT_BLACK);
    tft.drawString("PC Agent = Inactive", 120, 120, 2);
    
    // 3. Statut Monitoring
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString("Monitoring = Standby", 120, 150, 2);
}

// Fonction de connexion Wi-Fi avec affichage
void connectWiFi() {
    if (ssid == "" || ssid.length() == 0) {
        tft.setTextColor(TFT_ORANGE, TFT_BLACK);
        tft.drawCentreString("Wi-Fi Not Configured", 120, 110, 2);
        delay(2000);
        return;
    }
    
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawCentreString("Connecting Wi-Fi...", 120, 110, 2);
    
    WiFi.begin(ssid.c_str(), password.c_str());
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 15) {
        delay(500);
        attempts++;
    }
    
    tft.fillScreen(TFT_BLACK);
    if (WiFi.status() == WL_CONNECTED) {
        udp.begin(localUdpPort);
        tft.setTextColor(TFT_GREEN, TFT_BLACK);
        tft.drawCentreString("Wi-Fi Connected!", 120, 110, 2);
    } else {
        tft.setTextColor(TFT_RED, TFT_BLACK);
        tft.drawCentreString("Wi-Fi Failed", 120, 110, 2);
    }
    delay(1500);
}

// Fonction de dessin avec BORDS RONDS sans artefacts et avec Alerte !
void drawGauge(int r, int thickness, int val, int &last_angle, uint16_t base_color, bool check_alert) {
    int target_angle = map(constrain(val, 0, 100), 0, 100, START_ANGLE, END_ANGLE);
    if (target_angle == last_angle) return; 
    
    // Si la valeur dépasse le seuil, on passe la jauge en rouge
    uint16_t active_color = (check_alert && val >= seuil_alerte) ? color_alerte : base_color;
    
    int erase_r_out = r + 2;
    int erase_r_in = r - thickness - 2;
    
    // GESTION DE L'EFFACEMENT LARGE
    if (target_angle < last_angle) {
        int erase_start = target_angle - 12;
        if (target_angle <= START_ANGLE) erase_start = START_ANGLE - 12; 
        else if (erase_start < START_ANGLE) erase_start = START_ANGLE; 
        
        tft.drawSmoothArc(120, 120, erase_r_out, erase_r_in, erase_start, last_angle + 12, TFT_BLACK, TFT_BLACK, false);
    } else {
        int erase_start = last_angle - 12;
        if (last_angle <= START_ANGLE) erase_start = START_ANGLE - 12;
        else if (erase_start < START_ANGLE) erase_start = START_ANGLE;
        
        tft.drawSmoothArc(120, 120, erase_r_out, erase_r_in, erase_start, last_angle + 12, TFT_BLACK, TFT_BLACK, false);
    }
    
    // DESSIN NOUVELLE JAUGE
    if (target_angle > START_ANGLE) {
        tft.drawSmoothArc(120, 120, r, r - thickness, START_ANGLE, target_angle, active_color, TFT_BLACK, true);
    }
    last_angle = target_angle;
}

// Le cerveau de l'écran (traite les lignes recues en USB ou Wi-Fi)
void processData(String data) {
    data.trim();
    if (data.length() == 0) return;
    
    // Signe de vie reçu, on réinitialise le chronomètre
    lastDataTime = millis();
    
    // Si on était sur l'écran de statut, on remet l'affichage des jauges
    if (statusScreenActive) {
        statusScreenActive = false;
        tft.fillScreen(TFT_BLACK);
        drawLegend();
        last_angle_cpu = START_ANGLE;
        last_angle_ram = START_ANGLE;
        last_angle_gpu = START_ANGLE;
        last_tc = -1;
        last_tg = -1;
    }
    
    // --- Configuration Wi-Fi ---
    if (data.startsWith("WIFI:")) {
        int sep = data.indexOf("|");
        if (sep != -1) {
            ssid = data.substring(5, sep);
            password = data.substring(sep + 1);
            preferences.putString("ssid", ssid);
            preferences.putString("pwd", password);
            
            tft.fillScreen(TFT_BLACK);
            WiFi.disconnect();
            connectWiFi();
            
            tft.fillScreen(TFT_BLACK);
            drawLegend();
            last_angle_cpu = START_ANGLE; last_angle_ram = START_ANGLE; last_angle_gpu = START_ANGLE;
        }
        return;
    }
    
    // --- Configuration Couleurs & Seuils ---
    if (data.startsWith("CONFIG:")) {
        int p1 = data.indexOf("|");
        int p2 = data.indexOf("|", p1 + 1);
        int p3 = data.indexOf("|", p2 + 1);
        int p4 = data.indexOf("|", p3 + 1);
        
        if (p1 != -1 && p2 != -1 && p3 != -1 && p4 != -1) {
            color_cpu = hexToRGB565(data.substring(7, p1));
            color_ram = hexToRGB565(data.substring(p1 + 1, p2));
            color_gpu = hexToRGB565(data.substring(p2 + 1, p3));
            color_alerte = hexToRGB565(data.substring(p3 + 1, p4));
            seuil_alerte = data.substring(p4 + 1).toInt();
            
            preferences.putUShort("color_cpu", color_cpu);
            preferences.putUShort("color_ram", color_ram);
            preferences.putUShort("color_gpu", color_gpu);
            preferences.putUShort("color_alert", color_alerte);
            preferences.putInt("alert_thresh", seuil_alerte);
            
            tft.fillScreen(TFT_BLACK);
            drawLegend();
            last_angle_cpu = START_ANGLE; last_angle_ram = START_ANGLE; last_angle_gpu = START_ANGLE;
            last_tc = -1; last_tg = -1;
        }
        return;
    }
    
    // --- Données Capteurs ---
    if (data.indexOf("C:") == -1 || data.indexOf("Tc:") == -1) return;

    int cpu = data.substring(data.indexOf("C:")+2, data.indexOf("|", data.indexOf("C:"))).toInt();
    int ram = data.substring(data.indexOf("R:")+2, data.indexOf("|", data.indexOf("R:"))).toInt();
    int gpu = data.substring(data.indexOf("G:")+2, data.indexOf("|", data.indexOf("G:"))).toInt();
    int tc = data.substring(data.indexOf("Tc:")+3, data.indexOf("|", data.indexOf("Tc:"))).toInt();
    int tg = data.substring(data.indexOf("Tg:")+3).toInt();

    drawGauge(115, 15, cpu, last_angle_cpu, color_cpu, true);
    drawGauge(95,  15, ram, last_angle_ram, color_ram, false);
    drawGauge(75,  15, gpu, last_angle_gpu, color_gpu, true);
    
    if (tc != last_tc || tg != last_tg) {
        tft.setTextDatum(MC_DATUM);
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
        tft.setTextPadding(80); 
        
        tft.drawString("CPU " + String(tc) + "C", 120, 95, 2);
        tft.drawString("GPU " + String(tg) + "C", 120, 115, 2);
        
        last_tc = tc;
        last_tg = tg;
        tft.setTextPadding(0); 
    }
}

void setup() {
    Serial.begin(115200);
    tft.init();
    tft.setRotation(0);
    tft.fillScreen(TFT_BLACK);
    
    preferences.begin("moniteur", false);
    color_cpu = preferences.getUShort("color_cpu", TFT_GREEN);
    color_ram = preferences.getUShort("color_ram", TFT_BLUE);
    color_gpu = preferences.getUShort("color_gpu", TFT_MAGENTA);
    color_alerte = preferences.getUShort("color_alert", TFT_RED);
    seuil_alerte = preferences.getInt("alert_thresh", 80);
    ssid = preferences.getString("ssid", "");
    password = preferences.getString("pwd", "");

    connectWiFi();
    
    // --- CORRECTION ICI ---
    // On dessine l'interface de base dès le démarrage
    tft.fillScreen(TFT_BLACK);
    drawLegend();
    
    // On donne 3 secondes à l'ESP pour recevoir la première trame du PC.
    // Si rien n'arrive, la fonction loop() déclenchera l'écran "PC = Inactive".
    lastDataTime = millis(); 
    statusScreenActive = false;
}

void loop() {
    // Écoute sur le port USB
    if (Serial.available()) {
        String data = Serial.readStringUntil('\n');
        processData(data);
    }

    // Écoute sur le Wi-Fi (UDP)
    int packetSize = udp.parsePacket();
    if (packetSize) {
        int len = udp.read(incomingPacket, 255);
        if (len > 0) incomingPacket[len] = 0;
        processData(String(incomingPacket));
    }
    
    // Gestion du Timeout : Si rien reçu depuis > 3 secondes, on affiche l'écran de statut
    if (millis() - lastDataTime > TIMEOUT_MS) {
        if (!statusScreenActive) {
            drawStatusScreen();
        }
    }
}