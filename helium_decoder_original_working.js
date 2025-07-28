// Helium Cloud Function / Payload Decoder - ORIGINAL WORKING VERSION (WiFi Only)
function Decoder(bytes, port) {
  const out = {};

  if (port === 1) {
    // ─── Wi-Fi record (from T-Beam LoRaWAN) ──────────────────────────────
    let i = 0;
    
    // SSID (11 bytes, null-terminated)
    const ssidBytes = bytes.slice(i, i + 11);
    out.ssid = String.fromCharCode(...ssidBytes).replace(/\0.*$/, '');
    i += 11;

    // MAC (18 bytes ASCII) - "AA:BB:CC:DD:EE:FF"
    const macBytes = bytes.slice(i, i + 18);
    out.mac = String.fromCharCode(...macBytes).replace(/\0.*$/, '');
    i += 18;

    // RSSI (signed byte)
    out.rssi = (bytes[i] & 0x80) ? bytes[i] - 0x100 : bytes[i];
    i += 1;

    // Channel & Encryption
    out.channel    = bytes[i++];
    out.encryption = bytes[i++];

    // Latitude & Longitude (float32, little-endian)
    out.latitude  = new DataView(new Uint8Array(bytes.slice(i, i + 4)).buffer).getFloat32(0, true);
    i += 4;
    out.longitude = new DataView(new Uint8Array(bytes.slice(i, i + 4)).buffer).getFloat32(0, true);
    i += 4;

    // Altitude (int16, little-endian)
    out.altitude = bytes[i] | (bytes[i + 1] << 8);
    i += 2;

    // Satellites & HDOP
    out.sats = bytes[i++];
    out.hdop = bytes[i++];
  }

  return out;
}