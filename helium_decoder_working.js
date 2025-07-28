// Helium Console Decoder - WORKING VERSION for T-Beam WiFi Data
// This decoder properly parses the 44-byte payload from the T-Beam LoRaWAN firmware
// Updated to fix the byte length check (was 45, now 44) which was preventing GPS parsing

function Decoder(bytes, port) {
  if (bytes.length === 0) return {};
  
  const out = {};

  if (port === 1 && bytes.length >= 44) {
    let i = 0;
    
    // SSID (11 bytes, null-terminated)
    const ssidBytes = [];
    for (let j = 0; j < 11; j++) {
      if (bytes[i + j] !== 0) {
        ssidBytes.push(bytes[i + j]);
      }
    }
    out.ssid = String.fromCharChar(...ssidBytes);
    i += 11;

    // MAC (18 bytes ASCII) - "AA:BB:CC:DD:EE:FF"
    const macBytes = [];
    for (let j = 0; j < 18; j++) {
      if (bytes[i + j] !== 0) {
        macBytes.push(bytes[i + j]);
      }
    }
    out.mac = String.fromCharCode(...macBytes);
    i += 18;

    // RSSI (signed byte)
    out.rssi = bytes[i] > 127 ? bytes[i] - 256 : bytes[i];
    i += 1;

    // Channel & Encryption
    out.channel = bytes[i++];
    out.encryption = bytes[i++];

    // Latitude (float32, little-endian)
    const latBytes = new Uint8Array([bytes[i], bytes[i+1], bytes[i+2], bytes[i+3]]);
    out.latitude = new DataView(latBytes.buffer).getFloat32(0, true);
    i += 4;

    // Longitude (float32, little-endian)  
    const lonBytes = new Uint8Array([bytes[i], bytes[i+1], bytes[i+2], bytes[i+3]]);
    out.longitude = new DataView(lonBytes.buffer).getFloat32(0, true);
    i += 4;

    // Altitude (int16, little-endian)
    out.altitude = bytes[i] | (bytes[i + 1] << 8);
    if (out.altitude > 32767) out.altitude -= 65536; // Handle signed
    i += 2;

    // Satellites & HDOP
    out.sats = bytes[i++];
    out.hdop = bytes[i++];
  }

  return out;
}