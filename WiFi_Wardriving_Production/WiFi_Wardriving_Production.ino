#define TINY_GSM_MODEM_SIM7000
#define TINY_GSM_RX_BUFFER 1024

#include <TinyGsmClient.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>
#include <WiFi.h>

// LilyGO T-SIM7000G Pinout
#define UART_BAUD   115200
#define PIN_TX      27
#define PIN_RX      26
#define PWR_PIN     4
#define LED_PIN     12
#define BAT_ADC     35
#define SOLAR_ADC   36

#define SerialMon Serial
#define SerialAT  Serial1

// Network Configuration
const char* apn_primary = "h2g2";
const char* apn_fallback = "fast.t-mobile.com";
const char gprsUser[] = "";
const char gprsPass[] = "";

// Server Configuration - PRODUCTION
const char server[] = "24.152.185.226";  // Your Ubuntu server IP
const int port = 5001;

// Scanning Configuration
const int SCAN_INTERVAL = 5;        // 5 seconds between scans
const int BATCH_SIZE = 45;               // Networks per batch
const int MAX_NETWORKS_CACHE = 500;     // Total networks to remember
const int STATUS_INTERVAL = 600000;     // 5 minutes between status reports
const int HEARTBEAT_INTERVAL = 150000;  // 2 minutes between heartbeats

// Global Objects
TinyGsm modem(SerialAT);
TinyGsmClient client(modem);
HttpClient http(client, server, port);

// Network Tracking (Simple Arrays)
String cachedMacs[200];
bool cachedHasGPS[200];  // Track if cached network had GPS when stored
int cacheCount = 0;
String networkBatch[10];
int batchCount = 0;

// Timing and Status
unsigned long lastScanTime = 0;
unsigned long lastHeartbeatTime = 0;
unsigned long lastStatusTime = 0;
unsigned long lastGPSTime = 0;
unsigned long bootTime = 0;
bool cellularConnected = false;
int reconnectAttempts = 0;

// Cached GPS data (updated every 30 seconds)
float cachedLat = 0.0;
float cachedLon = 0.0;
float cachedAlt = 0.0;
float cachedAccuracy = 0.0;
int cachedSatellites = 0;
bool hasValidGPS = false;
const unsigned long GPS_UPDATE_INTERVAL = 5000; // Update GPS every 30 seconds

void setup() {
  SerialMon.begin(115200);
  delay(3000);
  
  SerialMon.println("=== WiFi Wardriving System v1.0 ===");
  bootTime = millis();
  
  initializeHardware();
  initializeCellular();
  initializeWiFi();
  
  SerialMon.println("✅ System ready - starting wardriving");
  digitalWrite(LED_PIN, LOW); // LED off = ready
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check cellular connection
  if (!cellularConnected || !modem.isGprsConnected()) {
    reconnectCellular();
  }
  
  // WiFi scanning
  if (currentTime - lastScanTime >= SCAN_INTERVAL) {
    scanWiFiNetworks();
    lastScanTime = currentTime;
  }
  
  // Send data batch
  if (batchCount >= BATCH_SIZE && cellularConnected) {
    sendNetworkBatch();
  }
  
  // Update GPS cache periodically
  if (currentTime - lastGPSTime >= GPS_UPDATE_INTERVAL) {
    updateGPSCache();
    lastGPSTime = currentTime;
  }
  
  // Health heartbeat
  if (currentTime - lastHeartbeatTime >= HEARTBEAT_INTERVAL) {
    sendHeartbeat();
    lastHeartbeatTime = currentTime;
  }
  
  // Status report
  if (currentTime - lastStatusTime >= STATUS_INTERVAL) {
    printStatus();
    lastStatusTime = currentTime;
  }
  
  delay(2000);
}

void initializeHardware() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(BAT_ADC, INPUT);
  pinMode(SOLAR_ADC, INPUT);
  pinMode(PWR_PIN, OUTPUT);
  
  // Modem power cycle
  digitalWrite(LED_PIN, HIGH); // LED on = initializing
  digitalWrite(PWR_PIN, HIGH);
  delay(1000);
  digitalWrite(PWR_PIN, LOW);
  delay(1000);
  digitalWrite(PWR_PIN, HIGH);
  delay(3000);
  
  SerialMon.println("✅ Hardware initialized");
}

void initializeCellular() {
  SerialMon.println("📶 Initializing cellular...");
  
  SerialAT.begin(UART_BAUD, SERIAL_8N1, PIN_RX, PIN_TX);
  delay(3000);
  
  // Test modem communication
  if (!modem.testAT(10000L)) {
    SerialMon.println("❌ Modem not responding");
    return;
  }
  
  SerialMon.printf("📋 IMEI: %s\n", modem.getIMEI().c_str());
  
  // Wait for network registration
  SerialMon.println("📡 Waiting for network...");
  if (!modem.waitForNetwork(60000L)) {
    SerialMon.println("❌ Network registration failed");
    return;
  }
  
  SerialMon.printf("🏢 Operator: %s\n", modem.getOperator().c_str());
  
  // Connect GPRS with primary APN
  SerialMon.printf("🌐 Connecting GPRS (APN: %s)...\n", apn_primary);
  if (modem.gprsConnect(apn_primary, gprsUser, gprsPass)) {
    cellularConnected = true;
    SerialMon.printf("✅ Connected - IP: %s\n", modem.getLocalIP().c_str());
  } else {
    // Try fallback APN
    SerialMon.printf("🔄 Trying fallback APN: %s\n", apn_fallback);
    if (modem.gprsConnect(apn_fallback, gprsUser, gprsPass)) {
      cellularConnected = true;
      SerialMon.printf("✅ Connected - IP: %s\n", modem.getLocalIP().c_str());
    } else {
      SerialMon.println("❌ GPRS connection failed");
    }
  }
  
  // Initialize GPS
  if (cellularConnected) {
    modem.sendAT("+CGPIO=0,48,1,1");
    modem.waitResponse(3000);
    modem.enableGPS();
    SerialMon.println("🛰️ GPS enabled");
  }
}

void reconnectCellular() {
  if (reconnectAttempts > 3) {
    SerialMon.println("🔄 Max reconnect attempts - restarting");
    ESP.restart();
  }
  
  reconnectAttempts++;
  cellularConnected = false;
  
  SerialMon.printf("🔄 Reconnecting cellular (attempt %d)...\n", reconnectAttempts);
  
  if (!modem.isNetworkConnected()) {
    if (!modem.waitForNetwork(30000L)) {
      SerialMon.println("❌ Network registration failed");
      return;
    }
  }
  
  if (!modem.isGprsConnected()) {
    if (modem.gprsConnect(apn_primary, gprsUser, gprsPass)) {
      cellularConnected = true;
      reconnectAttempts = 0;
      SerialMon.println("✅ Cellular reconnected");
    }
  } else {
    cellularConnected = true;
    reconnectAttempts = 0;
  }
}

void initializeWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  SerialMon.println("📶 WiFi configured for scanning");
}

void scanWiFiNetworks() {
  digitalWrite(LED_PIN, HIGH); // LED on during scan
  
  int networkCount = WiFi.scanNetworks();
  
  digitalWrite(LED_PIN, LOW); // LED off after scan
  
  if (networkCount <= 0) return;
  
  int newNetworks = 0;
  for (int i = 0; i < networkCount && i < 8; i++) { // Limit scan processing
    String mac = WiFi.BSSIDstr(i);
    
    // Check if we've seen this network before WITH GPS
    bool shouldSend = true;
    bool hasCurrentGPS = hasValidGPS && cachedLat != 0.0 && cachedLon != 0.0;
    
    for (int j = 0; j < cacheCount; j++) {
      if (cachedMacs[j] == mac && cachedHasGPS[j]) {
        // Only skip if we've seen it WITH GPS before
        shouldSend = false;
        break;
      }
    }
    
    if (shouldSend) {  // Always send networks we haven't seen with GPS
      // Only add to cache if we have GPS (so networks without GPS can be sent again)
      if (hasCurrentGPS) {
        bool isNewCacheEntry = true;
        
        // Check if it's already in cache (update existing entry)
        for (int k = 0; k < cacheCount; k++) {
          if (cachedMacs[k] == mac) {
            cachedHasGPS[k] = true;  // Mark as having GPS now
            isNewCacheEntry = false;
            break;
          }
        }
        
        // Add new entry if not found
        if (isNewCacheEntry) {
          if (cacheCount < MAX_NETWORKS_CACHE) {
            cachedMacs[cacheCount] = mac;
            cachedHasGPS[cacheCount] = true;
            cacheCount++;
          } else {
            // Cache is full, replace oldest (simple FIFO)
            for (int k = 0; k < MAX_NETWORKS_CACHE - 1; k++) {
              cachedMacs[k] = cachedMacs[k + 1];
              cachedHasGPS[k] = cachedHasGPS[k + 1];
            }
            cachedMacs[MAX_NETWORKS_CACHE - 1] = mac;
            cachedHasGPS[MAX_NETWORKS_CACHE - 1] = true;
          }
        }
      }
      
      // Add to batch for transmission
      if (batchCount < 10) {
        DynamicJsonDocument doc(600); // Increased size for GPS data
        doc["mac"] = mac;
        doc["ssid"] = WiFi.SSID(i);
        doc["rssi"] = WiFi.RSSI(i);
        doc["channel"] = WiFi.channel(i);
        doc["auth_mode"] = getAuthMode(WiFi.encryptionType(i));
        // Remove first_seen - let server set timestamp
        
        // Add cached GPS coordinates if available
        if (hasCurrentGPS) {
          doc["latitude"] = cachedLat;
          doc["longitude"] = cachedLon;
          doc["altitude"] = cachedAlt;
          doc["accuracy"] = cachedAccuracy;
        }
        
        String jsonString;
        serializeJson(doc, jsonString);
        networkBatch[batchCount] = jsonString;
        batchCount++;
        newNetworks++;
        
        if (hasCurrentGPS) {
          SerialMon.printf("📍 Queued: %s (%.6f, %.6f)\n", 
                           WiFi.SSID(i).c_str(), cachedLat, cachedLon);
        } else {
          SerialMon.printf("📡 Queued: %s (no GPS - can resend later)\n", WiFi.SSID(i).c_str());
        }
      }
    }
  }
  
  if (newNetworks > 0) {
    SerialMon.printf("📡 Found %d new networks (batch: %d, cache: %d)\n", 
                     newNetworks, batchCount, cacheCount);
  }
}

void sendNetworkBatch() {
  if (!cellularConnected || batchCount == 0) return;
  
  SerialMon.printf("📤 Sending %d networks...\n", batchCount);
  
  // Create batch JSON
  String payload = "{\"networks\":[";
  for (int i = 0; i < batchCount; i++) {
    payload += networkBatch[i];
    if (i < batchCount - 1) payload += ",";
  }
  payload += "]}";
  
  // Send HTTP request
  http.beginRequest();
  http.post("/api/wigle_data_batch");
  http.sendHeader("Content-Type", "application/json");
  http.sendHeader("Content-Length", payload.length());
  http.beginBody();
  http.print(payload);
  http.endRequest();
  
  int statusCode = http.responseStatusCode();
  
  if (statusCode == 200 || statusCode == 201) {
    SerialMon.println("✅ Batch sent successfully");
    batchCount = 0; // Clear batch
  } else {
    SerialMon.printf("❌ Send failed (HTTP %d)\n", statusCode);
  }
}

void updateGPSCache() {
  if (!cellularConnected) return; // Don't try GPS if cellular isn't working
  
  float lat, lon, speed, alt, accuracy;
  int vsat, usat, year, month, day, hour, minute, second;
  bool hasGPS = modem.getGPS(&lat, &lon, &speed, &alt, &vsat, &usat, &accuracy, &year, &month, &day, &hour, &minute, &second);
  
  if (hasGPS && lat != 0.0 && lon != 0.0) {
    cachedLat = lat;
    cachedLon = lon;
    cachedAlt = alt;
    cachedAccuracy = accuracy;
    cachedSatellites = vsat;
    hasValidGPS = true;
    SerialMon.printf("📍 GPS Cache Updated: %.6f, %.6f (±%.0fm, %d sats)\n", lat, lon, accuracy, vsat);
  } else {
    hasValidGPS = false;
    cachedSatellites = vsat; // Still cache satellite count for status
    SerialMon.printf("📍 GPS Update Failed (%d/%d sats)\n", vsat, usat);
  }
}

void sendHeartbeat() {
  if (!cellularConnected) return;
  
  DynamicJsonDocument doc(512);
  doc["type"] = "heartbeat";
  doc["device_mac"] = WiFi.macAddress();
  doc["battery_voltage"] = readBatteryVoltage();
  doc["solar_voltage"] = readSolarVoltage();
  doc["uptime_ms"] = millis() - bootTime;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["signal_quality"] = modem.getSignalQuality();
  doc["networks_cached"] = cacheCount;
  doc["networks_pending"] = batchCount;
  
  // Use cached GPS data
  doc["gps_active"] = hasValidGPS;
  if (cachedSatellites > 0) {
    doc["gps_satellites"] = cachedSatellites;
  }
  
  String payload;
  serializeJson(doc, payload);
  
  http.beginRequest();
  http.post("/api/heartbeat");
  http.sendHeader("Content-Type", "application/json");
  http.sendHeader("Content-Length", payload.length());
  http.beginBody();
  http.print(payload);
  http.endRequest();
  
  int statusCode = http.responseStatusCode();
  SerialMon.printf("💓 Heartbeat sent (HTTP %d)\n", statusCode);
}

void printStatus() {
  SerialMon.println("\n=== STATUS ===");
  SerialMon.printf("Uptime: %.1f min\n", (millis() - bootTime) / 60000.0);
  SerialMon.printf("Battery: %.2fV\n", readBatteryVoltage());
  SerialMon.printf("Signal: %d\n", modem.getSignalQuality());
  SerialMon.printf("Networks: %d cached, %d pending\n", cacheCount, batchCount);
  SerialMon.printf("Memory: %d bytes free\n", ESP.getFreeHeap());
  SerialMon.printf("Cellular: %s\n", cellularConnected ? "Connected" : "Disconnected");
  
  // Add cached GPS status
  if (hasValidGPS) {
    SerialMon.printf("GPS: %.6f, %.6f (±%.0fm, %d sats)\n", cachedLat, cachedLon, cachedAccuracy, cachedSatellites);
  } else {
    SerialMon.printf("GPS: No fix (%d sats visible)\n", cachedSatellites);
  }
  
  SerialMon.println("==============\n");
}

String getAuthMode(wifi_auth_mode_t encryptionType) {
  switch (encryptionType) {
    case WIFI_AUTH_OPEN: return "open";
    case WIFI_AUTH_WEP: return "wep";
    case WIFI_AUTH_WPA_PSK: return "wpa";
    case WIFI_AUTH_WPA2_PSK: return "wpa2";
    case WIFI_AUTH_WPA_WPA2_PSK: return "wpa/wpa2";
    case WIFI_AUTH_WPA2_ENTERPRISE: return "wpa2_enterprise";
    case WIFI_AUTH_WPA3_PSK: return "wpa3";
    case WIFI_AUTH_WPA2_WPA3_PSK: return "wpa2/wpa3";
    case WIFI_AUTH_WAPI_PSK: return "wapi";
    default: return "unknown";
  }
}

float readBatteryVoltage() {
  uint32_t sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(BAT_ADC);
  }
  uint16_t avg = sum / 10;
  return ((float)avg / 4095.0) * 2.0 * 3.3 * (1100 / 1000.0);
}

float readSolarVoltage() {
  uint32_t sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(SOLAR_ADC);
  }
  uint16_t avg = sum / 10;
  return ((float)avg / 4095.0) * 2.0 * 3.3 * (1100 / 1000.0);
}