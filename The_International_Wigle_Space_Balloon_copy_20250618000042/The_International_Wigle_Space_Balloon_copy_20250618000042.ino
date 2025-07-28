#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>
#include <WiFi.h>
#include <Wire.h>
#include <axp20x.h>
#include <TinyGPS++.h>
#include <stdlib.h>
#include <string.h>
#include <SSD1306Wire.h>

// ─── Pin Definitions ──────────────────────────────────────────────────────────
#define SCK_GPIO        5
#define MISO_GPIO       19
#define MOSI_GPIO       27
#define NSS_GPIO        18
#define RESET_GPIO      14    // T-Beam V1.0; use 23 on V2
#define DIO0_GPIO       26
#define DIO1_GPIO       33
#define DIO2_GPIO       32

#define GPS_BAUD_RATE   9600
#define GPS_RX_PIN      34
#define GPS_TX_PIN      12

#define I2C_SDA         21
#define I2C_SCL         22
#define AXP192_ADDRESS  0x34

// OLED Display
#define OLED_ADDRESS    0x3C
#define OLED_SDA        I2C_SDA
#define OLED_SCL        I2C_SCL

// ─── LoRaWAN OTAA Keys (replace with your values) ────────────────────────────
static const u1_t PROGMEM APPEUI[8]  = {0x45, 0x50, 0x93, 0x67, 0x00, 0xF9, 0x81, 0x60};
static const u1_t PROGMEM DEVEUI[8]  = {0x34, 0x31, 0x77, 0x19, 0xCB, 0xF9, 0x81, 0x60};
static const u1_t PROGMEM APPKEY[16] = {0x95, 0x5A, 0xE3, 0xE7, 0xF1, 0xC5, 0x8C, 0xB9,0xB4, 0xA8, 0xCF, 0x15, 0x47, 0xE4, 0x17, 0x7E};
void os_getArtEui(u1_t* buf){ memcpy_P(buf, APPEUI, 8); }
void os_getDevEui(u1_t* buf){ memcpy_P(buf, DEVEUI, 8); }
void os_getDevKey(u1_t* buf){ memcpy_P(buf, APPKEY, 16); }

// ─── Globals ─────────────────────────────────────────────────────────────────
TinyGPSPlus  gps;
AXP20X_Class axp;
SSD1306Wire  display(OLED_ADDRESS, OLED_SDA, OLED_SCL);
bool         axp192_found = false;
bool         lorawanJoined = false;

// Display state tracking
uint16_t lastNetworksCount = 0;
uint8_t lastSatellites = 0;
bool lastJoinStatus = false;
uint16_t lastScanCount = 0;

// One Wi‑Fi + GPS record (ASCII MAC) - EXACTLY like original
struct __attribute__((packed)) WifiNetwork {
  char     ssid[11];   // first 10 chars + '\0'
  char     mac[18];    // "AA:BB:CC:DD:EE:FF" + '\0'
  int8_t   rssi;
  uint8_t  channel;
  uint8_t  encryption;
  float    latitude;
  float    longitude;
  int16_t  altitude;   // meters
  uint8_t  sats;       // satellites
  uint8_t  hdop;       // HDOP×10
};

// Send queue backed by malloc (no PSRAM dependency) - EXACTLY like original
#define MAX_ENTRIES 2000
static WifiNetwork *networks;
static uint16_t     networksCount = 0;

// Circular buffer of last 500 seen MACs - EXACTLY like original
#define MAX_SEEN 500
static char         seenMACs[MAX_SEEN][18];
static uint16_t     seenCount = 0;
static uint16_t     seenHead  = 0;

// LMIC job & timing - EXACTLY like original
static osjob_t sendjob;
#define TX_INTERVAL_SEC 10

// LMIC pinmap - EXACTLY like original
const lmic_pinmap lmic_pins = {
  .nss  = NSS_GPIO,
  .rxtx = LMIC_UNUSED_PIN,
  .rst  = RESET_GPIO,
  .dio  = { DIO0_GPIO, DIO1_GPIO, DIO2_GPIO }
};

// Scan for AXP192 - EXACTLY like original
void scanI2Cdevice() {
  Wire.beginTransmission(AXP192_ADDRESS);
  if (Wire.endTransmission() == 0) axp192_found = true;
}

// Check seen list - EXACTLY like original
bool isSeenMAC(const char *mac) {
  for (uint16_t i = 0; i < seenCount; i++) {
    if (strcmp(seenMACs[i], mac) == 0) return true;
  }
  return false;
}

// Record new MAC - EXACTLY like original
void recordSeenMAC(const char *mac) {
  strncpy(seenMACs[seenHead], mac, sizeof(seenMACs[seenHead]) - 1);
  seenMACs[seenHead][17] = '\0';
  seenHead = (seenHead + 1) % MAX_SEEN;
  if (seenCount < MAX_SEEN) seenCount++;
}

// Update OLED display with current status
void updateDisplay() {
  display.clear();
  display.setFont(ArialMT_Plain_10);
  
  // Title
  display.setTextAlignment(TEXT_ALIGN_CENTER);
  display.drawString(64, 0, "T-Beam WiFi Scanner");
  
  // LoRa Status
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  display.drawString(0, 12, "LoRa: " + String(lorawanJoined ? "JOINED" : "JOINING"));
  
  // GPS Satellites
  uint8_t sats = gps.satellites.value();
  display.drawString(0, 22, "GPS Sats: " + String(sats));
  
  // Networks in queue
  display.drawString(0, 32, "Queue: " + String(networksCount));
  
  // Last scan count
  display.drawString(0, 42, "Last Scan: " + String(lastScanCount));
  
  // Battery voltage
  float batteryVoltage = 0.0;
  if (axp192_found) {
    batteryVoltage = axp.getBattVoltage();
  }
  display.drawString(0, 52, "Batt: " + String(batteryVoltage, 2) + "V");
  
  display.display();
}

// Check if display needs updating
void checkDisplayUpdate() {
  uint8_t currentSats = gps.satellites.value();
  bool needsUpdate = false;
  
  if (lastNetworksCount != networksCount) {
    lastNetworksCount = networksCount;
    needsUpdate = true;
  }
  
  if (lastSatellites != currentSats) {
    lastSatellites = currentSats;
    needsUpdate = true;
  }
  
  if (lastJoinStatus != lorawanJoined) {
    lastJoinStatus = lorawanJoined;
    needsUpdate = true;
  }
  
  if (needsUpdate) {
    updateDisplay();
  }
}

// Process async scan results - MODIFIED to work without GPS requirement
void processScanResults(int n) {
  lastScanCount = n;
  // Get GPS data if available - initialize to zero
  float lat = 0.0, lng = 0.0;
  int16_t alt = 0;
  uint8_t sats = 0;
  uint8_t hdop = 0;
  
  if (gps.location.isValid()) {
    lat = gps.location.lat();
    lng = gps.location.lng();
    alt = gps.altitude.meters();
    sats = gps.satellites.value();
    hdop = gps.hdop.value() / 10;
    Serial.printf("GPS: %.6f, %.6f (%d sats)\n", lat, lng, sats);
  } else {
    Serial.println("GPS: No fix, using zeros");
  }

  for (int i = 0; i < n; i++) {
    String ssidStr   = WiFi.SSID(i);
    String bssidStr  = WiFi.BSSIDstr(i);
    char macBuf[18]; bssidStr.toCharArray(macBuf, sizeof(macBuf));
    if (isSeenMAC(macBuf)) continue;
    recordSeenMAC(macBuf);
    if (networksCount < MAX_ENTRIES) {
      WifiNetwork &e = networks[networksCount++];
      strncpy(e.ssid, ssidStr.c_str(), sizeof(e.ssid) - 1);
      e.ssid[10] = '\0';
      strncpy(e.mac, macBuf, sizeof(e.mac) - 1);
      e.mac[17] = '\0';
      e.rssi       = WiFi.RSSI(i);
      e.channel    = WiFi.channel(i);
      e.encryption = WiFi.encryptionType(i);
      e.latitude   = lat;
      e.longitude  = lng;
      e.altitude   = alt;
      e.sats       = sats;
      e.hdop       = hdop;
      Serial.printf("Added: %s (%s)\n", e.ssid, e.mac);
    }
  }
  Serial.printf("Networks queued: %d\n", networksCount);
  
  // Update display after processing scan
  checkDisplayUpdate();
}

// Send one record LIFO or heartbeat - Enhanced with join status check
void do_send(osjob_t* j) {
  Serial.printf("*** do_send() called at %lu ***\n", os_getTime());
  
  Serial.printf("LMIC.opmode: 0x%02X (", LMIC.opmode);
  if (LMIC.opmode & OP_TXRXPEND) Serial.print("TXRXPEND ");
  if (LMIC.opmode & OP_JOINING) Serial.print("JOINING ");
  Serial.println(")");
  
  if (LMIC.opmode & OP_TXRXPEND) {
    Serial.println("TX/RX pending, skipping transmission");
    os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_SEC), do_send);
    return;
  }
  
  Serial.printf("Join Status: %s, Networks queued: %d\n", 
                lorawanJoined ? "JOINED" : "NOT_JOINED", networksCount);
  Serial.printf("LMIC devaddr: 0x%08X\n", LMIC.devaddr);
  
  // Check if we need to start joining
  if (!lorawanJoined && !(LMIC.opmode & OP_JOINING)) {
    Serial.println("*** NOT JOINED AND NOT JOINING - STARTING JOIN PROCESS ***");
    LMIC_startJoining();
    Serial.println("   LMIC_startJoining() called");
  }
  
  if (lorawanJoined && networksCount > 0) {
    WifiNetwork &e = networks[--networksCount];
    Serial.printf("*** ATTEMPTING TO SEND NETWORK DATA ***\n");
    Serial.printf("   Payload size: %d bytes\n", sizeof(e));
    
    // VERBOSE PAYLOAD DEBUGGING
    Serial.printf("*** DETAILED PAYLOAD STRUCTURE ***\n");
    Serial.printf("   SSID: '%s' (length: %d)\n", e.ssid, strlen(e.ssid));
    Serial.printf("   MAC: '%s' (length: %d)\n", e.mac, strlen(e.mac));
    Serial.printf("   RSSI: %d dBm\n", e.rssi);
    Serial.printf("   Channel: %d\n", e.channel);
    Serial.printf("   Encryption: %d\n", e.encryption);
    Serial.printf("   Latitude: %.8f (raw bytes: ", e.latitude);
    uint8_t* lat_bytes = (uint8_t*)&e.latitude;
    for(int i = 0; i < 4; i++) Serial.printf("%02X ", lat_bytes[i]);
    Serial.printf(")\n");
    Serial.printf("   Longitude: %.8f (raw bytes: ", e.longitude);
    uint8_t* lon_bytes = (uint8_t*)&e.longitude;
    for(int i = 0; i < 4; i++) Serial.printf("%02X ", lon_bytes[i]);
    Serial.printf(")\n");
    Serial.printf("   Altitude: %d meters\n", e.altitude);
    Serial.printf("   Satellites: %d\n", e.sats);
    Serial.printf("   HDOP: %d (hdop*10)\n", e.hdop);
    
    // HEX DUMP OF ENTIRE PAYLOAD
    Serial.printf("*** COMPLETE PAYLOAD HEX DUMP ***\n");
    uint8_t* payload_bytes = (uint8_t*)&e;
    Serial.printf("   Offset  Hex                              ASCII\n");
    for(int i = 0; i < sizeof(e); i += 16) {
      Serial.printf("   %04X:   ", i);
      // Hex bytes
      for(int j = 0; j < 16 && (i + j) < sizeof(e); j++) {
        Serial.printf("%02X ", payload_bytes[i + j]);
      }
      // Padding for alignment
      for(int j = (sizeof(e) - i < 16) ? sizeof(e) - i : 16; j < 16; j++) {
        Serial.printf("   ");
      }
      Serial.printf("  ");
      // ASCII representation
      for(int j = 0; j < 16 && (i + j) < sizeof(e); j++) {
        char c = payload_bytes[i + j];
        Serial.printf("%c", (c >= 32 && c <= 126) ? c : '.');
      }
      Serial.printf("\n");
    }
    Serial.printf("*** END HEX DUMP ***\n");
    
    LMIC_setTxData2(1, (xref2u1_t)&e, sizeof(e), 0);
    Serial.printf("   LMIC_setTxData2() called with port=1, size=%d\n", sizeof(e));
    Serial.printf("Sending network: %s (%s) Lat: %.6f Lon: %.6f\n", 
                  e.ssid, e.mac, e.latitude, e.longitude);
  } else if (!lorawanJoined) {
    Serial.println("Not joined to Helium yet, waiting...");
  } else {
    Serial.println("No networks to send");
  }
  
  Serial.printf("Scheduling next do_send() in %d seconds\n", TX_INTERVAL_SEC);
  os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_SEC), do_send);
  Serial.println("*** do_send() complete ***\n");
}

// LMIC events - VERY VERBOSE debugging
void onEvent(ev_t ev) {
  Serial.printf("[%lu] LoRaWAN Event %d: ", os_getTime(), ev);
  
  switch(ev) {
    case EV_SCAN_TIMEOUT:
      Serial.println("EV_SCAN_TIMEOUT - Channel scan timeout");
      break;
    case EV_BEACON_FOUND:
      Serial.println("EV_BEACON_FOUND - Gateway beacon detected");
      break;
    case EV_BEACON_MISSED:
      Serial.println("EV_BEACON_MISSED - Gateway beacon missed");
      break;
    case EV_BEACON_TRACKED:
      Serial.println("EV_BEACON_TRACKED - Beacon tracking started");
      break;
    case EV_JOINING:
      Serial.println("EV_JOINING - *** ATTEMPTING TO JOIN HELIUM NETWORK ***");
      Serial.printf("   Frequency: %.1f MHz\n", LMIC.freq / 1000000.0);
      Serial.printf("   Data Rate: %d\n", LMIC.datarate);
      Serial.printf("   TX Power: %d dBm\n", LMIC.txpow);
      Serial.printf("   Sequence: %d\n", LMIC.seqnoUp);
      lorawanJoined = false;
      break;
    case EV_JOINED:
      Serial.println("EV_JOINED - *** SUCCESSFULLY JOINED HELIUM NETWORK! ***");
      {
        u4_t netid = 0;
        devaddr_t devaddr = 0;
        u1_t nwkKey[16];
        u1_t artKey[16];
        LMIC_getSessionKeys(&netid, &devaddr, nwkKey, artKey);
        Serial.printf("   Device Address: 0x%08X\n", devaddr);
        Serial.printf("   Network ID: 0x%08X\n", netid);
        Serial.printf("   Frequency: %.1f MHz\n", LMIC.freq / 1000000.0);
        Serial.printf("   Data Rate: %d\n", LMIC.datarate);
      }
      lorawanJoined = true;
      LMIC_setLinkCheckMode(0);
      checkDisplayUpdate();  // Update display when join status changes
      break;
    case EV_JOIN_FAILED:
      Serial.println("EV_JOIN_FAILED - *** JOIN ATTEMPT FAILED ***");
      Serial.printf("   Last frequency tried: %.1f MHz\n", LMIC.freq / 1000000.0);
      Serial.printf("   Will retry in %d seconds\n", TX_INTERVAL_SEC);
      lorawanJoined = false;
      break;
    case EV_REJOIN_FAILED:
      Serial.println("EV_REJOIN_FAILED - Rejoin attempt failed");
      lorawanJoined = false;
      break;
    case EV_TXCOMPLETE:
      Serial.println("EV_TXCOMPLETE - Transmission complete");
      Serial.printf("   Frame counter: %d\n", LMIC.seqnoUp);
      Serial.printf("   Frequency: %.1f MHz\n", LMIC.freq / 1000000.0);
      if (LMIC.txrxFlags & TXRX_ACK) {
        Serial.println("   *** RECEIVED ACK FROM GATEWAY ***");
      } else {
        Serial.println("   No ACK received");
      }
      if (LMIC.dataLen) {
        Serial.printf("   *** RECEIVED %d BYTES DOWNLINK: ", LMIC.dataLen);
        for (int i = 0; i < LMIC.dataLen; i++) {
          Serial.printf("%02X ", LMIC.frame[LMIC.dataBeg + i]);
        }
        Serial.println();
      }
      break;
    case EV_LOST_TSYNC:
      Serial.println("EV_LOST_TSYNC - Time sync lost");
      break;
    case EV_RESET:
      Serial.println("EV_RESET - *** LMIC STACK RESET ***");
      lorawanJoined = false;
      break;
    case EV_RXCOMPLETE:
      Serial.println("EV_RXCOMPLETE - Receive window complete");
      break;
    case EV_LINK_DEAD:
      Serial.println("EV_LINK_DEAD - *** LINK CONFIRMED DEAD ***");
      lorawanJoined = false;
      break;
    case EV_LINK_ALIVE:
      Serial.println("EV_LINK_ALIVE - Link confirmed alive");
      break;
    case EV_TXSTART:
      Serial.println("EV_TXSTART - *** STARTING TRANSMISSION ***");
      Serial.printf("   Payload size: %d bytes\n", LMIC.pendTxLen);
      Serial.printf("   Frequency: %.1f MHz\n", LMIC.freq / 1000000.0);
      Serial.printf("   Data Rate: %d\n", LMIC.datarate);
      Serial.printf("   TX Power: %d dBm\n", LMIC.txpow);
      Serial.printf("   Frame counter: %d\n", LMIC.seqnoUp);
      break;
    case EV_TXCANCELED:
      Serial.println("EV_TXCANCELED - Transmission cancelled");
      break;
    case EV_RXSTART:
      Serial.println("EV_RXSTART - Starting receive window");
      break;
    case EV_JOIN_TXCOMPLETE:
      Serial.println("EV_JOIN_TXCOMPLETE - *** JOIN REQUEST TRANSMITTED ***");
      Serial.printf("   Waiting for Join Accept response...\n");
      Serial.printf("   Frequency used: %.1f MHz\n", LMIC.freq / 1000000.0);
      break;
    default:
      Serial.printf("UNKNOWN_EVENT_%d", ev);
      if (ev == 20) {
        Serial.println(" - *** THIS IS EV_JOINED! NETWORK JOINED SUCCESSFULLY! ***");
        lorawanJoined = true;
        LMIC_setLinkCheckMode(0);
        Serial.printf("   Join status updated to: %s\n", lorawanJoined ? "JOINED" : "NOT_JOINED");
        Serial.printf("   Device should now send data on next do_send() call\n");
      } else {
        Serial.println();
      }
      break;
  }
  
  // Always show current LMIC state
  Serial.printf("   LMIC State: opmode=0x%02X, seqnoUp=%d, freq=%.1fMHz\n", 
                LMIC.opmode, LMIC.seqnoUp, LMIC.freq / 1000000.0);
}

// Setup - EXACTLY like original
void setup() {
  Serial.begin(115200);
  Serial.println("=== T-Beam Continuous Wi-Fi LIFO Mapper ===");

  // Allocate network queue - EXACTLY like original
  networks = (WifiNetwork*)malloc(MAX_ENTRIES * sizeof(WifiNetwork));
  if (!networks) {
    Serial.println("❌ malloc failed, cannot proceed");
    while (1);
  }

  // I2C + AXP - EXACTLY like original
  Wire.begin(I2C_SDA, I2C_SCL);
  scanI2Cdevice();
  if (axp192_found && axp.begin(Wire, AXP192_ADDRESS)) {
    axp.setPowerOutPut(AXP202_LDO3,  AXP202_ON);
    axp.setPowerOutPut(AXP202_DCDC3, AXP202_ON);
    axp.adc1Enable(AXP202_BATT_VOL_ADC1, true);
    axp.setLDO3Voltage(3300);
    axp.setDCDC1Voltage(3300);
    Serial.println("AXP192 configured");
  }

  // OLED Display
  display.init();
  display.flipScreenVertically();
  display.clear();
  display.setFont(ArialMT_Plain_10);
  display.setTextAlignment(TEXT_ALIGN_CENTER);
  display.drawString(64, 20, "T-Beam Starting...");
  display.display();

  // GPS - EXACTLY like original
  Serial1.begin(GPS_BAUD_RATE, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  // Wi-Fi scan - EXACTLY like original
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(); delay(100);
  WiFi.scanNetworks(true);

  // LoRaWAN - EXACTLY like original with verbose logging
  Serial.println("*** INITIALIZING LORAWAN STACK ***");
  Serial.println("   About to call os_init()...");
  Serial.flush(); // Force output before potential hang
  
  os_init(); 
  Serial.println("   os_init() complete");
  Serial.flush();
  
  Serial.println("   About to call LMIC_reset()...");
  Serial.flush();
  
  LMIC_reset();
  Serial.println("   LMIC_reset() complete");
  Serial.flush();
  
  // Configure for US915 (Helium) - THIS IS CRITICAL!
  Serial.println("   Configuring for US915 band plan (Helium)...");
  LMIC_selectSubBand(1); // Use sub-band 1 (channels 8-15) for Helium
  Serial.println("   Sub-band 1 selected for Helium compatibility");
  
  // Disable link check validation (not needed for OTAA)
  LMIC_setLinkCheckMode(0);
  Serial.println("   Link check mode disabled");
  
  // Set clock error percentage for more robust reception
  LMIC_setClockError(MAX_CLOCK_ERROR * 1 / 100);
  Serial.println("   Clock error tolerance set");
  
  Serial.println("   Checking LMIC state after reset...");
  Serial.printf("   LMIC.opmode: 0x%02X\n", LMIC.opmode);
  Serial.flush();
  
  Serial.println("*** PRINTING DEVICE CREDENTIALS ***");
  Serial.print("   AppEUI: ");
  for (int i = 7; i >= 0; i--) Serial.printf("%02X", APPEUI[i]);
  Serial.println();
  Serial.print("   DevEUI: ");
  for (int i = 7; i >= 0; i--) Serial.printf("%02X", DEVEUI[i]);
  Serial.println();
  Serial.print("   AppKey: ");
  for (int i = 0; i < 16; i++) Serial.printf("%02X", APPKEY[i]);
  Serial.println();
  Serial.flush();
  
  Serial.println("   About to start join process...");
  Serial.flush();
  
  Serial.println("*** STARTING LORAWAN JOIN PROCESS ***");
  do_send(&sendjob);
  Serial.println("   do_send() called successfully");
  Serial.flush();
  
  Serial.println("Setup complete, starting operation...");
  
  // Initial display update
  updateDisplay();
}

// GPS debugging variables
unsigned long lastGPSDebug = 0;
#define GPS_DEBUG_INTERVAL 5000  // Print GPS status every 5 seconds

// Main loop - EXACTLY like original + GPS debugging
void loop() {
  bool newGPSData = false;
  while (Serial1.available()) {
    if (gps.encode(Serial1.read())) {
      newGPSData = true;
    }
  }
  
  // GPS debugging every 5 seconds
  unsigned long now = millis();
  if (now - lastGPSDebug > GPS_DEBUG_INTERVAL) {
    lastGPSDebug = now;
    Serial.println("=== GPS STATUS ===");
    Serial.printf("GPS chars processed: %lu\n", gps.charsProcessed());
    Serial.printf("Valid sentences: %lu\n", gps.sentencesWithFix());
    Serial.printf("Failed checksum: %lu\n", gps.failedChecksum());
    Serial.printf("Satellites in view: %d\n", gps.satellites.value());
    Serial.printf("Location valid: %s\n", gps.location.isValid() ? "YES" : "NO");
    if (gps.location.isValid()) {
      Serial.printf("Lat/Lng: %.6f, %.6f\n", gps.location.lat(), gps.location.lng());
      Serial.printf("Altitude: %.2f m\n", gps.altitude.meters());
      Serial.printf("HDOP: %.2f\n", gps.hdop.hdop());
    }
    Serial.printf("Date valid: %s\n", gps.date.isValid() ? "YES" : "NO");
    Serial.printf("Time valid: %s\n", gps.time.isValid() ? "YES" : "NO");
    if (newGPSData) {
      Serial.println("*** NEW GPS DATA RECEIVED THIS CYCLE ***");
    }
    Serial.println("=================");
  }
  
  // Check for display updates based on GPS changes
  checkDisplayUpdate();
  
  os_runloop_once();
  int n = WiFi.scanComplete();
  if (n >= 0) {
    processScanResults(n);
    WiFi.scanDelete();
    WiFi.scanNetworks(true);
  }
}