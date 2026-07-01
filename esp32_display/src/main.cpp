#include <WiFi.h>
#include <WiFiUdp.h>
#include <Preferences.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();
WiFiUDP udp;
Preferences preferences;

const int udpPort = 1234;

// Mémoire des états pour optimiser l'affichage
int lastCpu = -1, lastRam = -1, lastGpu = -1;
int lastTc = -1, lastTg = -1;

// Paramètres géométriques
const int centreX = 120;
const int centreY = 120;
const int angleDebut = 150; 
const int angleFin = 390;   

void dessinerJauge(int rayonExterne, int rayonInterne, int valeur, uint32_t couleurJauge, uint32_t couleurFond);
void analyserEtAfficher(String donneesBrutes);
void verifierConfigurationUSB(String commande);

void setup() {
  Serial.begin(115200);
  
  tft.init();
  tft.setRotation(0);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  
  // Dessin des 3 jauges vides au démarrage
  dessinerJauge(115, 103, 100, tft.color565(30, 30, 30), TFT_BLACK); // CPU (Exterieur)
  dessinerJauge(98, 86, 100, tft.color565(30, 30, 30), TFT_BLACK);  // GPU (Milieu)
  dessinerJauge(81, 69, 100, tft.color565(30, 30, 30), TFT_BLACK);  // RAM (Interieur)
  
  preferences.begin("wifi-config", false);
  String ssid = preferences.getString("ssid", "");
  String password = preferences.getString("password", "");
  
  if (ssid != "" && password != "") {
    WiFi.begin(ssid.c_str(), password.c_str());
    int timeout = 0;
    while (WiFi.status() != WL_CONNECTED && timeout < 20) { delay(500); timeout++; }
    if (WiFi.status() == WL_CONNECTED) { udp.begin(udpPort); }
  }
}

void loop() {
  if (Serial.available() > 0) {
    String message = Serial.readStringUntil('\n');
    message.trim();
    if (message.startsWith("WIFI:")) { verifierConfigurationUSB(message); } 
    else if (message.startsWith("C:")) { analyserEtAfficher(message); }
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    int packetSize = udp.parsePacket();
    if (packetSize) {
      char incomingPacket[255];
      int len = udp.read(incomingPacket, 255);
      if (len > 0) {
        incomingPacket[len] = 0;
        String messageUDP = String(incomingPacket);
        if (messageUDP.startsWith("C:")) { analyserEtAfficher(messageUDP); }
      }
    }
  }
}

void analyserEtAfficher(String donnees) {
  // Parsing de "C:45|R:60|G:80|Tc:55|Tg:65"
  int posC = donnees.indexOf("C:");
  int posR = donnees.indexOf("|R:");
  int posG = donnees.indexOf("|G:");
  int posTc = donnees.indexOf("|Tc:");
  int posTg = donnees.indexOf("|Tg:");

  if (posC != -1 && posR != -1 && posG != -1 && posTc != -1 && posTg != -1) {
    int cpu = donnees.substring(posC + 2, posR).toInt();
    int ram = donnees.substring(posR + 3, posG).toInt();
    int gpu = donnees.substring(posG + 3, posTc).toInt();
    int tc = donnees.substring(posTc + 4, posTg).toInt();
    int tg = donnees.substring(posTg + 4).toInt();

    uint32_t fond = tft.color565(30, 30, 30);

    // Mise à jour des arcs uniquement si changement
    if (cpu != lastCpu) { dessinerJauge(115, 103, cpu, TFT_BLUE, fond); lastCpu = cpu; }
    if (gpu != lastGpu) { dessinerJauge(98, 86, gpu, TFT_GREEN, fond); lastGpu = gpu; }
    if (ram != lastRam) { dessinerJauge(81, 69, ram, TFT_PURPLE, fond); lastRam = ram; }

    // Mise à jour du texte central si une donnée change
    if (tc != lastTc || tg != lastTg || cpu != lastCpu || gpu != lastGpu || ram != lastRam) {
      tft.fillRect(45, 80, 150, 70, TFT_BLACK); // Nettoyer la zone centrale
      
      char buf[30];
      sprintf(buf, "CPU: %d%% (%dC)", cpu, tc);
      tft.drawCentreString(buf, centreX, 85, 2);
      
      sprintf(buf, "GPU: %d%% (%dC)", gpu, tg);
      tft.drawCentreString(buf, centreX, 105, 2);
      
      sprintf(buf, "RAM: %d%%", ram);
      tft.drawCentreString(buf, centreX, 125, 2);
      
      lastTc = tc; lastTg = tg;
    }
  }
}

void dessinerJauge(int rayonExterne, int rayonInterne, int valeur, uint32_t couleurJauge, uint32_t couleurFond) {
  int angleValeur = map(valeur, 0, 100, angleDebut, angleFin);
  if (angleValeur > angleDebut) {
    tft.drawSmoothArc(centreX, centreY, rayonExterne, rayonInterne, angleDebut, angleValeur, couleurJauge, TFT_BLACK, true);
  }
  if (angleValeur < angleFin) {
    tft.drawSmoothArc(centreX, centreY, rayonExterne, rayonInterne, angleValeur, angleFin, couleurFond, TFT_BLACK, true);
  }
}

void verifierConfigurationUSB(String commande) {
  String donnees = commande.substring(5); 
  int idx = donnees.indexOf(';');
  if (idx != -1) {
    preferences.putString("ssid", donnees.substring(0, idx));
    preferences.putString("password", donnees.substring(idx + 1));
    ESP.restart();
  }
}