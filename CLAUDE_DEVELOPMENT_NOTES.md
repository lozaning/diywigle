# Claude Development Notes - WiFi Wardriving System

## Project Overview
This is a **DIY WiFi Wardriving System** with Flask web app and ESP32 devices for defensive security research.

## Current Status & Issues

### ⚠️ ACTIVE ISSUE - Graph Not Showing for Unauthenticated Users
**Problem**: Network Discovery Trends graph shows data when logged in, but appears empty for unauthenticated users despite being configured to show default data.

**Expected Behavior**: Graph should show "new networks every 5 minutes for last hour" by default for ALL users.

**Debugging Added**: Added console logging to identify the issue. When you restart development:
1. Open browser dev tools (F12) → Console tab
2. Visit the index page while logged out
3. Look for debug messages starting with "🔧 DEBUG:"
4. This will show if HTML elements exist, if default times are set, if API calls work, etc.

**Location of Issue**: Lines 1441-1445 in `enhanced_app_production.py`

## Recent Major Changes

### 1. Privacy & Security Implementation ✅
- **Index page**: Unauthenticated users see banner, stats, trends graph only
- **Hidden from public**: Map, device health table, network list  
- **All other pages**: Require login (`@login_required` decorator)
- **API protection**: Sensitive endpoints protected, data collection endpoints remain public
- **Device compatibility**: ESP32 devices can still send data without authentication

### 2. Timezone Localization ✅  
- **All timestamps**: Now display in user's local timezone
- **Implementation**: JavaScript utilities convert UTC to local time on page load
- **Locations**: Device tables, network lists, charts, heartbeat history
- **No database changes**: Still stores UTC, only display is localized

### 3. Network Discovery Trends Graph ✅
- **Location**: Index page, between stats and map
- **Features**: 
  - Toggle: Cumulative vs Per-Period view
  - Time scales: 5min, 10min, 30min, 1hr intervals
  - Date/time range pickers with preset buttons (Last Hour, 6h, 24h, All Data)
- **Default settings**: Period view, 5 minutes, last hour range
- **API**: `/api/network_stats` (public endpoint)

### 4. GPS Satellites Chart ✅
- **Location**: Device detail pages (`/device/<mac>`)
- **Purpose**: Shows GPS satellite count over time for both cellular and LoRaWAN devices  
- **Scaling**: Dynamic (no fixed max, accommodates up to 42+ satellites)

### 5. Map Pagination Sync ✅
- **Issue Fixed**: Map and table now show same networks per page
- **Implementation**: `/api/network_locations` accepts page parameter
- **Navigation**: Pagination buttons update both table and map

## Architecture

### Web Application (Flask)
- **File**: `enhanced_app_production.py`
- **Database**: SQLite (`wigle_data.db`)
- **Port**: 5001
- **Auth**: username `Admin`, password `Wigler`

### Hardware Devices  
- **LilyGO T-SIM7000G**: Cellular-enabled scanner
- **T-Beam**: LoRaWAN scanner for Helium network
- **Data flow**: Devices → HTTP API → Database → Web dashboard

### Key API Endpoints

**Public (No auth required):**
- `/api/wigle_data_batch` - Device data submission
- `/api/heartbeat` - Device health updates  
- `/payload` - LoRaWAN webhook
- `/api/network_stats` - Trends graph data
- `/status` - System monitoring

**Protected (Login required):**
- `/api/network_locations` - Map coordinate data
- `/api/clear_database` - Admin functions
- All management endpoints

## Current Configuration

### Default Graph Settings
- **View**: "Networks Per Period" (selected)
- **Time Scale**: "5 Minutes" (selected)  
- **Time Range**: Last hour (auto-populated in datetime inputs)

### Authentication States
- **Logged out**: See banner, stats, trends graph, login button
- **Logged in**: See everything + map, network list, device details, admin functions

## File Structure
```
enhanced_app_production.py - Main Flask application
wigle_data.db - SQLite database (auto-created)
CLAUDE.md - Project instructions for Claude
```

## Next Steps When Resuming

1. **Fix the graph display issue**:
   - Check console debugging output
   - Verify API call is working: `GET /api/network_stats?view_type=period&time_scale=5&start_time=...&end_time=...`
   - Ensure chart.js is loading properly
   - Check if Chart.js initialization is happening

2. **Test deployment readiness**:
   - Verify all authentication works correctly
   - Test device data collection still works
   - Confirm no sensitive data leaks to unauthenticated users

3. **Remove debugging code** once issue is resolved:
   - Clean up console.log statements added for troubleshooting

## Known Working Features
- ✅ Data collection from ESP32 devices
- ✅ LoRaWAN integration via Helium webhook  
- ✅ Device health monitoring with charts
- ✅ GPS satellite tracking
- ✅ Timezone localization  
- ✅ Authentication system
- ✅ WiGLE.net integration
- ✅ CSV export functionality
- ✅ Map with network locations (for authenticated users)
- ✅ Responsive design

## Development Environment
- **Python Flask** application
- **SQLite** database
- **Chart.js** for visualizations
- **Leaflet.js** for mapping
- **Bootstrap-like** custom CSS styling

---
*Notes generated during development session on 2025-07-28*