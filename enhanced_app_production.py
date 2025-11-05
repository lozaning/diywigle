from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from functools import wraps
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wigle_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Use environment variable for SECRET_KEY in production, fallback to development key
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')

db = SQLAlchemy(app)

class WigleData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(17), nullable=False)
    ssid = db.Column(db.String(32), nullable=False)
    auth_mode = db.Column(db.String(20), nullable=False)
    first_seen = db.Column(db.DateTime, nullable=False)
    channel = db.Column(db.Integer, nullable=False)
    rssi = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    altitude = db.Column(db.Float, nullable=True)
    accuracy = db.Column(db.Float, nullable=True)
    uploaded_to_wigle = db.Column(db.Boolean, default=False, nullable=False)
    device_source = db.Column(db.String(50), nullable=True)  # Name of device that reported this network

class Heartbeat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(17), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    battery = db.Column(db.Float, nullable=False)
    solar_voltage = db.Column(db.Float, nullable=True)
    signal_quality = db.Column(db.Integer, nullable=True)
    free_heap = db.Column(db.Integer, nullable=True)
    networks_cached = db.Column(db.Integer, nullable=True)
    gps_active = db.Column(db.Boolean, nullable=True)
    gps_satellites = db.Column(db.Integer, nullable=True)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(17), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=True)
    first_seen = db.Column(db.DateTime, nullable=False)
    last_seen = db.Column(db.DateTime, nullable=False)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_wigle_api_key():
    """Get WiGLE API key from settings"""
    setting = Settings.query.filter_by(key='wigle_api_key').first()
    return setting.value if setting else None

def set_wigle_api_key(api_key):
    """Set WiGLE API key in settings"""
    setting = Settings.query.filter_by(key='wigle_api_key').first()
    if setting:
        setting.value = api_key
    else:
        setting = Settings(key='wigle_api_key', value=api_key)
        db.session.add(setting)
    db.session.commit()

# Device Detail Page Template
DEVICE_DETAIL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Device Details - {{ device.name or mac }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .btn {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            border: none;
            cursor: pointer;
            margin-right: 10px;
            margin-bottom: 10px;
            display: inline-block;
        }
        .btn:hover {
            background: #5a6fd8;
        }
        .btn-success {
            background: #27ae60;
        }
        .btn-success:hover {
            background: #229954;
        }
        .stats-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 1.1em;
            margin-top: 10px;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .chart-container h3 {
            margin-top: 0;
            color: #333;
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }
        table {
            width: 100%;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .health-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .health-good { background-color: #27ae60; }
        .health-warning { background-color: #f39c12; }
        .health-critical { background-color: #e74c3c; }
        .name-edit {
            display: inline-block;
            margin-left: 10px;
        }
        .name-input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📱 {{ device.name if device.name else mac }}</h1>
        <p>Device Details and Health Monitoring</p>
        {% if device.name != mac %}
        <p><code>{{ mac }}</code></p>
        {% endif %}
    </div>

    <div class="controls">
        <a href="/" class="btn">← Back to Dashboard</a>
        {% if session.get('logged_in') %}
            <button onclick="showNameEdit()" class="btn btn-success">✏️ Edit Name</button>
        {% endif %}
        <div class="name-edit" id="nameEdit" style="display: none;">
            <input type="text" id="deviceName" class="name-input" value="{{ device.name or '' }}" placeholder="Enter device name">
            <button onclick="saveName()" class="btn btn-success">Save</button>
            <button onclick="hideNameEdit()" class="btn">Cancel</button>
        </div>
    </div>

    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number">{{ "%.2f"|format(latest_hb.battery or 0) }}V</div>
            <div class="stat-label">Current Battery</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ latest_hb.signal_quality or 'N/A' }}</div>
            <div class="stat-label">Signal Quality</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ latest_hb.networks_cached or 0 }}</div>
            <div class="stat-label">Networks Cached</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ heartbeats_raw|length }}</div>
            <div class="stat-label">Total Heartbeats</div>
        </div>
    </div>

    <div class="chart-grid">
        <div class="chart-container">
            <h3>📊 Battery Voltage History</h3>
            <canvas id="batteryChart" width="400" height="200"></canvas>
        </div>
        <div class="chart-container">
            <h3>📶 Signal Quality History</h3>
            <canvas id="signalChart" width="400" height="200"></canvas>
        </div>
        <div class="chart-container">
            <h3>🌞 Solar Voltage History</h3>
            <canvas id="solarChart" width="400" height="200"></canvas>
        </div>
        <div class="chart-container">
            <h3>💾 Memory Usage History</h3>
            <canvas id="memoryChart" width="400" height="200"></canvas>
        </div>
        <div class="chart-container">
            <h3>🛰️ GPS Satellites History</h3>
            <canvas id="gpsChart" width="400" height="200"></canvas>
        </div>
    </div>

    <h2>📋 Heartbeat History</h2>
    <table>
        <thead>
            <tr>
                <th>Status</th>
                <th>Timestamp</th>
                <th>Battery</th>
                <th>Solar</th>
                <th>Signal</th>
                <th>GPS</th>
                <th>Memory</th>
                <th>Networks</th>
            </tr>
        </thead>
        <tbody>
            {% for hb in heartbeats_raw %}
            <tr>
                <td>
                    {% set battery_level = hb.battery or 0 %}
                    {% if battery_level > 3.7 %}
                        <span class="health-indicator health-good"></span>Good
                    {% elif battery_level > 3.4 %}
                        <span class="health-indicator health-warning"></span>Warning
                    {% else %}
                        <span class="health-indicator health-critical"></span>Critical
                    {% endif %}
                </td>
                <td><span class="utc-timestamp" data-utc="{{ hb.timestamp.isoformat() }}">{{ hb.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</span></td>
                <td>{{ "%.2f"|format(hb.battery or 0) }}V</td>
                <td>{{ "%.2f"|format(hb.solar_voltage or 0) }}V</td>
                <td>{{ hb.signal_quality or 'N/A' }}</td>
                <td>
                    {% if hb.gps_active %}
                        ✅ {{ hb.gps_satellites or 0 }} sats
                    {% else %}
                        ❌ No fix
                    {% endif %}
                </td>
                <td>{{ (hb.free_heap or 0) // 1024 }}KB free</td>
                <td>{{ hb.networks_cached or 0 }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        // Timezone conversion utilities
        function formatLocalDateTime(utcDateString) {
            if (!utcDateString) return 'N/A';
            const date = new Date(utcDateString + (utcDateString.includes('Z') ? '' : 'Z'));
            return date.toLocaleString();
        }
        
        function formatLocalDateTimeShort(utcDateString) {
            if (!utcDateString) return 'N/A';
            const date = new Date(utcDateString + (utcDateString.includes('Z') ? '' : 'Z'));
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        }

        // Prepare data for charts
        const heartbeats = {{ heartbeats | tojson }};
        const timestamps = heartbeats.map(h => new Date(h.timestamp).toLocaleString([], {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})).reverse();
        const batteryData = heartbeats.map(h => h.battery || 0).reverse();
        const signalData = heartbeats.map(h => h.signal_quality || 0).reverse();
        const solarData = heartbeats.map(h => h.solar_voltage || 0).reverse();
        const memoryData = heartbeats.map(h => (h.free_heap || 0) / 1024).reverse();
        const gpsData = heartbeats.map(h => h.gps_satellites || 0).reverse();

        // Battery Chart
        new Chart(document.getElementById('batteryChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Battery Voltage (V)',
                    data: batteryData,
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 3.0,
                        max: 4.2
                    }
                }
            }
        });

        // Signal Chart
        new Chart(document.getElementById('signalChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Signal Quality',
                    data: signalData,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 31
                    }
                }
            }
        });

        // Solar Chart
        new Chart(document.getElementById('solarChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Solar Voltage (V)',
                    data: solarData,
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Memory Chart
        new Chart(document.getElementById('memoryChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Free Memory (KB)',
                    data: memoryData,
                    borderColor: '#9b59b6',
                    backgroundColor: 'rgba(155, 89, 182, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // GPS Satellites Chart
        new Chart(document.getElementById('gpsChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'GPS Satellites',
                    data: gpsData,
                    borderColor: '#e67e22',
                    backgroundColor: 'rgba(230, 126, 34, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });

        // Name editing functions
        function showNameEdit() {
            document.getElementById('nameEdit').style.display = 'inline-block';
        }

        function hideNameEdit() {
            document.getElementById('nameEdit').style.display = 'none';
        }

        function saveName() {
            const name = document.getElementById('deviceName').value;
            fetch('/api/device/{{ mac }}/name', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: name })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    alert('Error saving name: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error saving name: ' + error);
            });
        }
        
        // Function to convert all UTC timestamps to local time
        function convertTimestampsToLocal() {
            document.querySelectorAll('.utc-timestamp').forEach(function(element) {
                const utcTime = element.getAttribute('data-utc');
                if (utcTime) {
                    element.textContent = formatLocalDateTimeShort(utcTime);
                }
            });
        }
        
        // Convert timestamps after page load
        convertTimestampsToLocal();
    </script>
</body>
</html>
'''

# Settings Page Template
SETTINGS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Settings - WiFi Wardriving</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .settings-section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .settings-section h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: bold;
        }
        input[type="text"], input[type="password"], textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
            font-size: 16px;
        }
        input[type="text"]:focus, input[type="password"]:focus, textarea:focus {
            border-color: #667eea;
            outline: none;
        }
        .btn {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            border: none;
            cursor: pointer;
            margin-right: 10px;
            margin-bottom: 10px;
            display: inline-block;
        }
        .btn:hover {
            background: #5a6fd8;
        }
        .btn-success {
            background: #27ae60;
        }
        .btn-success:hover {
            background: #229954;
        }
        .btn-danger {
            background: #e74c3c;
        }
        .btn-danger:hover {
            background: #c0392b;
        }
        .help-text {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-good { background-color: #27ae60; }
        .status-bad { background-color: #e74c3c; }
        .wigle-status {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚙️ Settings</h1>
        <p>WiFi Wardriving System Configuration</p>
    </div>

    <div class="controls">
        <a href="/" class="btn">← Back to Dashboard</a>
    </div>

    <div class="settings-section">
        <h2>📤 WiGLE Integration</h2>
        
        <div class="wigle-status">
            {% if wigle_api_key %}
                <span class="status-indicator status-good"></span>
                <strong>Status:</strong> API Key configured
            {% else %}
                <span class="status-indicator status-bad"></span>
                <strong>Status:</strong> No API Key configured
            {% endif %}
        </div>

        <form id="wigleForm">
            <div class="form-group">
                <label for="apiKey">WiGLE API Key:</label>
                <input type="password" id="apiKey" name="apiKey" value="{{ wigle_api_key or '' }}" placeholder="Enter your WiGLE API key">
                <div class="help-text">
                    Get your API key from <a href="https://wigle.net/account" target="_blank">wigle.net/account</a>
                </div>
            </div>
            
            <button type="button" onclick="saveWigleSettings()" class="btn btn-success">💾 Save API Key</button>
            <button type="button" onclick="testWigleConnection()" class="btn">🔍 Test Connection</button>
            {% if wigle_api_key %}
            <button type="button" onclick="clearWigleSettings()" class="btn btn-danger">🗑️ Clear API Key</button>
            {% endif %}
        </form>

        <div id="wigleTestResult" style="margin-top: 20px;"></div>
    </div>

    <div class="settings-section">
        <h2>📊 Upload Statistics</h2>
        <div>
            <strong>Networks pending upload:</strong> {{ pending_networks }}<br>
            <strong>Networks already uploaded:</strong> {{ uploaded_networks }}<br>
            <strong>Total networks:</strong> {{ total_networks }}
        </div>
        
        {% if wigle_api_key and pending_networks > 0 %}
        <div style="margin-top: 20px;">
            <button onclick="uploadPendingNetworks()" class="btn btn-success">📤 Upload {{ pending_networks }} Networks to WiGLE</button>
        </div>
        {% endif %}
    </div>

    <div class="settings-section">
        <h2>🔧 System Information</h2>
        <div>
            <strong>Database:</strong> {{ db_info.name }}<br>
            <strong>Total devices:</strong> {{ db_info.devices }}<br>
            <strong>Total heartbeats:</strong> {{ db_info.heartbeats }}<br>
            <strong>Server uptime:</strong> <span id="uptime">{{ uptime }}</span>
        </div>
    </div>

    <script>
        function saveWigleSettings() {
            const apiKey = document.getElementById('apiKey').value;
            
            fetch('/api/settings/wigle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_key: apiKey })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('WiGLE API key saved successfully!');
                    location.reload();
                } else {
                    alert('Error saving API key: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error saving API key: ' + error);
            });
        }

        function testWigleConnection() {
            const apiKey = document.getElementById('apiKey').value;
            
            if (!apiKey) {
                alert('Please enter an API key first');
                return;
            }

            document.getElementById('wigleTestResult').innerHTML = '🔍 Testing connection...';
            
            fetch('/api/test_wigle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_key: apiKey })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('wigleTestResult').innerHTML = 
                        '<div style="color: #27ae60;">✅ Connection successful! User: ' + data.user + '</div>';
                } else {
                    document.getElementById('wigleTestResult').innerHTML = 
                        '<div style="color: #e74c3c;">❌ Connection failed: ' + data.message + '</div>';
                }
            })
            .catch(error => {
                document.getElementById('wigleTestResult').innerHTML = 
                    '<div style="color: #e74c3c;">❌ Error testing connection: ' + error + '</div>';
            });
        }

        function clearWigleSettings() {
            if (confirm('Are you sure you want to clear the WiGLE API key?')) {
                fetch('/api/settings/wigle', {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('WiGLE API key cleared!');
                        location.reload();
                    } else {
                        alert('Error clearing API key: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('Error clearing API key: ' + error);
                });
            }
        }

        function uploadPendingNetworks() {
            if (confirm('Upload all pending networks to WiGLE? This may take a few minutes.')) {
                fetch('/api/upload_to_wigle', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert(`Successfully uploaded ${data.count} networks to WiGLE!`);
                        location.reload();
                    } else {
                        alert('Error uploading to WiGLE: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('Error uploading to WiGLE: ' + error);
                });
            }
        }
    </script>
</body>
</html>
'''

# Enhanced HTML template with map and login
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>WiFi Wardriving System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .stats-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 1.1em;
            margin-top: 10px;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .btn {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            border: none;
            cursor: pointer;
            margin-right: 10px;
            margin-bottom: 10px;
            display: inline-block;
        }
        .btn:hover {
            background: #5a6fd8;
        }
        .btn-danger {
            background: #e74c3c;
        }
        .btn-danger:hover {
            background: #c0392b;
        }
        #map {
            height: 500px;
            width: 100%;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        table {
            width: 100%;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .health-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .health-good { background-color: #27ae60; }
        .health-warning { background-color: #f39c12; }
        .health-critical { background-color: #e74c3c; }
        .section-title {
            color: #333;
            margin: 30px 0 15px 0;
            font-size: 1.5em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 WiFi Wardriving System</h1>
        <p>Real-time network discovery and mapping platform</p>
    </div>

    <div class="controls">
        {% if session.get('logged_in') %}
            <a href="/csv" class="btn">📥 Download CSV</a>
            <a href="/settings" class="btn">⚙️ Settings</a>
            <button onclick="uploadToWigle()" class="btn">📤 Upload to WiGLE</button>
            <button onclick="clearDatabase()" class="btn btn-danger">🗑️ Clear Database</button>
            <a href="/logout" class="btn">🚪 Logout</a>
        {% else %}
            <a href="/csv" class="btn">📥 Download CSV</a>
            <a href="/login" class="btn">🔐 Admin Login</a>
        {% endif %}
        <button onclick="location.reload()" class="btn">🔄 Refresh</button>
    </div>

    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number">{{ total_networks }}</div>
            <div class="stat-label">Total Networks</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ unique_networks }}</div>
            <div class="stat-label">Unique Networks</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ active_devices }}</div>
            <div class="stat-label">Active Devices</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ networks_with_gps }}</div>
            <div class="stat-label">GPS Located</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ uploaded_networks }}</div>
            <div class="stat-label">Uploaded to WiGLE</div>
        </div>
    </div>

    <h2 class="section-title">📈 Network Discovery Trends</h2>
    <div style="background: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; align-items: end; margin-bottom: 15px;">
            <div>
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">View:</label>
                <select id="viewType" onchange="updateNetworksChart()" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    <option value="cumulative">Cumulative Total</option>
                    <option value="period" selected>Networks Per Period</option>
                </select>
            </div>
            
            <div>
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Time Scale:</label>
                <select id="timeScale" onchange="updateNetworksChart()" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    <option value="5" selected>5 Minutes</option>
                    <option value="10">10 Minutes</option>
                    <option value="30">30 Minutes</option>
                    <option value="60">1 Hour</option>
                </select>
            </div>
            
            <div>
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Start Time:</label>
                <input type="datetime-local" id="startTime" onchange="updateNetworksChart()" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
            </div>
            
            <div>
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">End Time:</label>
                <input type="datetime-local" id="endTime" onchange="updateNetworksChart()" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
            </div>
        </div>
        
        <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <button onclick="updateNetworksChart()" class="btn" style="font-size: 14px; padding: 8px 16px;">🔄 Refresh</button>
            <button onclick="setTimeRange('all')" class="btn" style="font-size: 14px; padding: 8px 16px; background: #95a5a6;">📊 All Data</button>
            <button onclick="setTimeRange('24h')" class="btn" style="font-size: 14px; padding: 8px 16px; background: #34495e;">📅 Last 24h</button>
            <button onclick="setTimeRange('6h')" class="btn" style="font-size: 14px; padding: 8px 16px; background: #2c3e50;">🕕 Last 6h</button>
            <button onclick="setTimeRange('1h')" class="btn" style="font-size: 14px; padding: 8px 16px; background: #16a085;">🕐 Last Hour</button>
        </div>
        
        <div style="height: 400px;">
            <canvas id="networksChart"></canvas>
        </div>
    </div>

    {% if session.get('logged_in') %}
    <h2 class="section-title">🗺️ Network Map</h2>
    <div id="map"></div>

    <h2 class="section-title">📡 Device Health Status</h2>
    <table>
        <thead>
            <tr>
                <th>Status</th>
                <th>Name</th>
                <th>Device MAC</th>
                <th>Last Heartbeat</th>
                <th>Battery</th>
                <th>Solar</th>
                <th>Signal</th>
                <th>GPS</th>
                <th>Networks Cached</th>
            </tr>
        </thead>
        <tbody>
            {% for data in device_data %}
            {% set hb = data.heartbeat %}
            {% set device = data.device %}
            <tr>
                <td>
                    {% set battery_level = hb.battery or 0 %}
                    {% if battery_level > 3.7 %}
                        <span class="health-indicator health-good"></span>Good
                    {% elif battery_level > 3.4 %}
                        <span class="health-indicator health-warning"></span>Warning
                    {% else %}
                        <span class="health-indicator health-critical"></span>Critical
                    {% endif %}
                </td>
                <td>
                    <a href="/device/{{ hb.mac }}" style="text-decoration: none; color: #667eea;">
                        {{ device.name if device and device.name else hb.mac }}
                    </a>
                </td>
                <td><code><a href="/device/{{ hb.mac }}" style="text-decoration: none; color: #667eea;">{{ hb.mac }}</a></code></td>
                <td><span class="utc-timestamp" data-utc="{{ hb.timestamp.isoformat() }}">{{ hb.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</span></td>
                <td>{{ "%.2f"|format(hb.battery or 0) }}V</td>
                <td>{{ "%.2f"|format(hb.solar_voltage or 0) }}V</td>
                <td>{{ hb.signal_quality or 'N/A' }}</td>
                <td>
                    {% if hb.gps_active %}
                        ✅ {{ hb.gps_satellites or 0 }} sats
                    {% else %}
                        ❌ No fix
                    {% endif %}
                </td>
                <td>{{ hb.networks_cached or 0 }}</td>
            </tr>
            {% else %}
            <tr><td colspan="9" style="text-align: center; color: #666;">No devices connected yet</td></tr>
            {% endfor %}
        </tbody>
    </table>

    <h2 class="section-title">📋 Recent Networks</h2>
<table>
    <thead>
        <tr>
            <th>SSID</th>
            <th>MAC Address</th>
            <th>Security</th>
            <th>Channel</th>
            <th>Signal</th>
            <th>Location</th>
            <th>First Seen</th>
            <th>Device Source</th>
            <th>WiGLE Status</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for net in recent_networks %}
        <tr>
            <td><strong>{{ net.ssid or '(Hidden)' }}</strong></td>
            <td><code>{{ net.mac }}</code></td>
            <td>{{ net.auth_mode }}</td>
            <td>{{ net.channel }}</td>
            <td>{{ net.rssi }} dBm</td>
            <td>
                {% if net.latitude and net.longitude %}
                    {{ "%.4f"|format(net.latitude) }}, {{ "%.4f"|format(net.longitude) }}
                    {% if net.accuracy %}
                        <br><small>±{{ "%.0f"|format(net.accuracy) }}m</small>
                    {% endif %}
                {% else %}
                    <span style="color: #999;">No GPS</span>
                {% endif %}
            </td>
            <td><span class="utc-timestamp" data-utc="{{ net.first_seen.isoformat() }}">{{ net.first_seen.strftime('%m/%d %H:%M') }}</span></td>
            <td>
                {% if net.device_source %}
                    <a href="/device/{{ device_source_to_mac.get(net.device_source, net.device_source) }}" style="color: #667eea;">
                        {{ device_name_map.get(device_source_to_mac.get(net.device_source, net.device_source), net.device_source) }}
                    </a>
                {% else %}
                    <span style="color: #999;">Unknown</span>
                {% endif %}
            </td>
            <td>
                {% if net.uploaded_to_wigle %}
                    <span style="color: #27ae60;">✅ Uploaded</span>
                {% else %}
                    <span style="color: #e74c3c;">❌ Pending</span>
                {% endif %}
            </td>
            <td>
                {% if session.get('logged_in') %}
                    <button onclick="deleteNetwork('{{ net.id }}')" class="btn btn-danger" style="font-size: 12px; padding: 6px 10px;">🗑️ Delete</button>
                {% endif %}
            </td>
        </tr>
        {% else %}
        <tr><td colspan="10" style="text-align: center; color: #666;">No networks discovered yet</td></tr>
        {% endfor %}
    </tbody>
</table>

    <!-- Pagination Controls -->
    <div class="pagination-container" style="text-align: center; margin: 20px 0;">
        {% if has_prev %}
            <a href="?page={{ prev_num }}" class="btn" onclick="return navigateAndUpdateMap({{ prev_num }})">&laquo; Previous</a>
        {% endif %}
        
        {% if total_pages > 1 %}
            <span style="margin: 0 20px;">Page {{ current_page }} of {{ total_pages }}</span>
        {% endif %}
        
        {% if has_next %}
            <a href="?page={{ next_num }}" class="btn" onclick="return navigateAndUpdateMap({{ next_num }})">Next &raquo;</a>
        {% endif %}
    </div>
    {% endif %}

    <script>
        // Timezone conversion utilities
        function formatLocalDateTime(utcDateString) {
            if (!utcDateString) return 'N/A';
            const date = new Date(utcDateString + (utcDateString.includes('Z') ? '' : 'Z'));
            return date.toLocaleString();
        }
        
        function formatLocalDate(utcDateString) {
            if (!utcDateString) return 'N/A';
            const date = new Date(utcDateString + (utcDateString.includes('Z') ? '' : 'Z'));
            return date.toLocaleDateString();
        }
        
        function formatLocalTime(utcDateString) {
            if (!utcDateString) return 'N/A';
            const date = new Date(utcDateString + (utcDateString.includes('Z') ? '' : 'Z'));
            return date.toLocaleTimeString();
        }
        
        function formatLocalDateTimeShort(utcDateString) {
            if (!utcDateString) return 'N/A';
            const date = new Date(utcDateString + (utcDateString.includes('Z') ? '' : 'Z'));
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        }

        // Networks chart variable
        var networksChart = null;

        // Initialize map
        var map = L.map('map').setView([44.9778, -93.2650], 10); // Minneapolis area
        var markersLayer = L.layerGroup().addTo(map);
        var infoControl = null;
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Function to load and display network locations
        function loadNetworkLocations(page) {
            // Clear existing markers and info
            markersLayer.clearLayers();
            if (infoControl) {
                map.removeControl(infoControl);
                infoControl = null;
            }
            
            fetch(`/api/network_locations?page=${page}`)
                .then(response => response.json())
                .then(networks => {
                    if (networks.length > 0) {
                        var bounds = [];
                        
                        networks.forEach(function(network) {
                            if (network.latitude && network.longitude) {
                                var marker = L.marker([network.latitude, network.longitude])
                                    .bindPopup(`
                                        <strong>${network.ssid || '(Hidden)'}</strong><br>
                                        MAC: ${network.mac}<br>
                                        Security: ${network.auth_mode}<br>
                                        Signal: ${network.rssi} dBm<br>
                                        Channel: ${network.channel}
                                    `);
                                
                                markersLayer.addLayer(marker);
                                bounds.push([network.latitude, network.longitude]);
                            }
                        });
                        
                        if (bounds.length > 0) {
                            map.fitBounds(bounds, {padding: [20, 20]});
                        }
                    } else {
                        // No GPS data for this page, show message
                        infoControl = L.control();
                        infoControl.onAdd = function (map) {
                            this._div = L.DomUtil.create('div', 'info');
                            this._div.innerHTML = '<h4>No GPS Data</h4>No networks with GPS coordinates on this page';
                            return this._div;
                        };
                        infoControl.addTo(map);
                    }
                })
                .catch(error => {
                    console.error('Error loading network data:', error);
                });
        }
        
        // Function to handle navigation and map updates
        function navigateAndUpdateMap(page) {
            // Update URL without refreshing page
            const url = new URL(window.location);
            url.searchParams.set('page', page);
            window.history.pushState({}, '', url);
            
            // Load new data for the page
            loadNetworkLocations(page);
            
            // Prevent default link behavior and reload page normally
            return true;
        }

        // Get current page from URL parameters and load initial data (only for authenticated users)
        {% if session.get('logged_in') %}
        const urlParams = new URLSearchParams(window.location.search);
        const currentPage = urlParams.get('page') || 1;
        loadNetworkLocations(currentPage);
        {% endif %}

        // Function to set time range presets
        function setTimeRange(preset) {
            const now = new Date();
            const startTimeInput = document.getElementById('startTime');
            const endTimeInput = document.getElementById('endTime');
            
            // Format datetime for input (YYYY-MM-DDTHH:MM)
            function formatForInput(date) {
                return date.toISOString().slice(0, 16);
            }
            
            switch(preset) {
                case '1h':
                    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
                    startTimeInput.value = formatForInput(oneHourAgo);
                    endTimeInput.value = formatForInput(now);
                    break;
                case '6h':
                    const sixHoursAgo = new Date(now.getTime() - 6 * 60 * 60 * 1000);
                    startTimeInput.value = formatForInput(sixHoursAgo);
                    endTimeInput.value = formatForInput(now);
                    break;
                case '24h':
                    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                    startTimeInput.value = formatForInput(oneDayAgo);
                    endTimeInput.value = formatForInput(now);
                    break;
                case 'all':
                default:
                    startTimeInput.value = '';
                    endTimeInput.value = '';
                    break;
            }
            
            updateNetworksChart();
        }

        // Function to update networks chart
        function updateNetworksChart() {
            const viewType = document.getElementById('viewType').value;
            const timeScale = document.getElementById('timeScale').value;
            const startTime = document.getElementById('startTime').value;
            const endTime = document.getElementById('endTime').value;
            
            console.log('Updating chart with:', viewType, timeScale, startTime, endTime);
            
            // Build query parameters
            let queryParams = `view_type=${viewType}&time_scale=${timeScale}`;
            if (startTime) {
                queryParams += `&start_time=${encodeURIComponent(startTime)}`;
            }
            if (endTime) {
                queryParams += `&end_time=${encodeURIComponent(endTime)}`;
            }
            
            fetch(`/api/network_stats?${queryParams}`)
                .then(response => {
                    console.log('Response status:', response.status);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Received data:', data);
                    
                    if (!data || data.length === 0) {
                        console.log('No data available for chart');
                        // Show message in chart area
                        const ctx = document.getElementById('networksChart').getContext('2d');
                        if (networksChart) {
                            networksChart.destroy();
                        }
                        // You could draw a "No data" message here
                        return;
                    }
                    
                    if (networksChart) {
                        networksChart.destroy();
                    }
                    
                    const ctx = document.getElementById('networksChart').getContext('2d');
                    const labels = data.map(d => {
                        // Convert the timestamp to local time for display
                        const date = new Date(d.timestamp);
                        return date.toLocaleDateString([], {month: 'short', day: 'numeric'}) + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
                    });
                    const counts = data.map(d => d.count);
                    
                    console.log('Chart labels:', labels);
                    console.log('Chart data:', counts);
                    
                    const chartTitle = viewType === 'cumulative' 
                        ? 'Cumulative Unique Networks with GPS' 
                        : `Unique Networks Discovered Every ${timeScale} Minutes`;
                    
                    const chartColor = viewType === 'cumulative' ? '#27ae60' : '#3498db';
                    const bgColor = viewType === 'cumulative' ? 'rgba(39, 174, 96, 0.1)' : 'rgba(52, 152, 219, 0.1)';
                    
                    networksChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: chartTitle,
                                data: counts,
                                borderColor: chartColor,
                                backgroundColor: bgColor,
                                tension: 0.4,
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        stepSize: 1
                                    }
                                },
                                x: {
                                    ticks: {
                                        maxTicksLimit: 20
                                    }
                                }
                            },
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'top'
                                }
                            }
                        }
                    });
                    
                    console.log('Chart created successfully');
                })
                .catch(error => {
                    console.error('Error loading network stats:', error);
                    // Show error in chart area
                    const ctx = document.getElementById('networksChart').getContext('2d');
                    if (networksChart) {
                        networksChart.destroy();
                    }
                });
        }

        // Initialize time inputs with defaults (last hour for period view)
        function initializeTimeInputs() {
            const now = new Date();
            const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
            
            function formatForInput(date) {
                return date.toISOString().slice(0, 16);
            }
            
            // Set default to last hour for the default period view
            const startTimeInput = document.getElementById('startTime');
            const endTimeInput = document.getElementById('endTime');
            
            console.log('🔧 DEBUG: startTimeInput exists?', !!startTimeInput);
            console.log('🔧 DEBUG: endTimeInput exists?', !!endTimeInput);
            console.log('🔧 DEBUG: Current values:', startTimeInput?.value, endTimeInput?.value);
            
            if (!startTimeInput.value && !endTimeInput.value) {
                startTimeInput.value = formatForInput(oneHourAgo);
                endTimeInput.value = formatForInput(now);
                console.log('🔧 DEBUG: Set default times:', formatForInput(oneHourAgo), 'to', formatForInput(now));
            }
        }

        // Function to convert all UTC timestamps to local time
        function convertTimestampsToLocal() {
            document.querySelectorAll('.utc-timestamp').forEach(function(element) {
                const utcTime = element.getAttribute('data-utc');
                if (utcTime) {
                    element.textContent = formatLocalDateTimeShort(utcTime);
                }
            });
        }

        // Initialize time inputs and load chart (for all users)
        console.log('🔧 DEBUG: Initializing chart for all users');
        console.log('🔧 DEBUG: User logged in?', {{ 'true' if session.get('logged_in') else 'false' }});
        initializeTimeInputs();
        console.log('🔧 DEBUG: Time inputs initialized, calling updateNetworksChart()');
        updateNetworksChart();
        
        // Convert timestamps after page load
        convertTimestampsToLocal();

        // Clear database function
        function clearDatabase() {
            if (confirm('Are you sure you want to clear the entire database? This action cannot be undone.')) {
                fetch('/api/clear_database', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message || 'Database cleared successfully');
                    location.reload();
                })
                .catch(error => {
                    alert('Error clearing database: ' + error);
                });
            }
        }
        
        // Upload to WiGLE function
        function uploadToWigle() {
            if (confirm('Upload all unsubmitted networks to WiGLE? This requires a valid WiGLE API key in Settings.')) {
                fetch('/api/upload_to_wigle', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert(`Successfully uploaded ${data.count} networks to WiGLE!`);
                        location.reload();
                    } else {
                        alert('Error: ' + (data.message || 'Unknown error'));
                    }
                })
                .catch(error => {
                    alert('Error uploading to WiGLE: ' + error);
                });
            }
        }
        
        // Delete network function
        function deleteNetwork(networkId) {
            if (confirm('Are you sure you want to delete this network?')) {
                fetch('/api/network/' + networkId, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        location.reload();
                    } else {
                        alert('Error deleting network: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('Error deleting network: ' + error);
                });
            }
        }

        // Auto-refresh disabled - was causing browser crashes
        // setInterval(function() {
        //     location.reload();
        // }, 30000);
    </script>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - WiFi Wardriving</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 350px;
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: bold;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
            font-size: 16px;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            border-color: #667eea;
            outline: none;
        }
        .btn {
            width: 100%;
            background: #667eea;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .btn:hover {
            background: #5a6fd8;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
        }
        .back-link {
            text-align: center;
            margin-top: 20px;
        }
        .back-link a {
            color: #667eea;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>🔐 Admin Access</h1>
            <p>WiFi Wardriving System</p>
        </div>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="post">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit" class="btn">Login</button>
        </form>
        
        <div class="back-link">
            <a href="/">← Back to Dashboard</a>
        </div>
    </div>
</body>
</html>
'''

def get_or_create_device(mac):
    """Get or create a device record"""
    device = Device.query.filter_by(mac=mac).first()
    if not device:
        device = Device(
            mac=mac,
            name=None,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        )
        db.session.add(device)
        db.session.commit()
    else:
        device.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    return device

@app.route('/')
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 100

    try:
        # Paginated networks
        networks_paginated = WigleData.query.order_by(WigleData.first_seen.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        recent_networks = networks_paginated.items

        # Pagination info
        has_prev = networks_paginated.has_prev
        has_next = networks_paginated.has_next
        prev_num = networks_paginated.prev_num if has_prev else None
        next_num = networks_paginated.next_num if has_next else None
        total_pages = networks_paginated.pages
        current_page = page
    except Exception as e:
        # Fallback if database doesn't exist yet
        recent_networks = []
        has_prev = False
        has_next = False
        prev_num = None
        next_num = None
        total_pages = 1
        current_page = 1

    # Get latest heartbeat per device
    latest_heartbeats = db.session.query(Heartbeat).filter(
        Heartbeat.id.in_(
            db.session.query(db.func.max(Heartbeat.id)).group_by(Heartbeat.mac)
        )
    ).all()

    # Get device info for each heartbeat
    device_data = []
    for hb in latest_heartbeats:
        device = Device.query.filter_by(mac=hb.mac).first()
        device_data.append({
            'heartbeat': hb,
            'device': device
        })

    # Map device_source MACs to their device names
    device_macs = [net.device_source for net in recent_networks if net.device_source]
    device_name_map = {
        dev.mac: dev.name if dev.name else dev.mac
        for dev in Device.query.filter(Device.mac.in_(device_macs)).all()
    }
    
    # Create reverse mapping: device_source (name or MAC) -> actual MAC address for URLs
    device_source_to_mac = {}
    for dev in Device.query.filter(Device.mac.in_(device_macs)).all():
        device_source_to_mac[dev.mac] = dev.mac  # MAC -> MAC
        if dev.name:
            device_source_to_mac[dev.name] = dev.mac  # Name -> MAC

    total_networks = WigleData.query.count()
    unique_networks = db.session.query(WigleData.mac).distinct().count()
    networks_with_gps = WigleData.query.filter(WigleData.latitude.isnot(None)).count()
    uploaded_networks = WigleData.query.filter_by(uploaded_to_wigle=True).count()
    active_devices = len(latest_heartbeats)

    return render_template_string(MAIN_TEMPLATE, 
        recent_networks=recent_networks,
        device_data=device_data,
        total_networks=total_networks,
        unique_networks=unique_networks,
        networks_with_gps=networks_with_gps,
        uploaded_networks=uploaded_networks,
        active_devices=active_devices,
        has_prev=has_prev,
        has_next=has_next,
        prev_num=prev_num,
        next_num=next_num,
        total_pages=total_pages,
        current_page=current_page,
        device_name_map=device_name_map,
        device_source_to_mac=device_source_to_mac
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Authentication
        if username == 'lozaning' and password == 'oneill':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error='Invalid credentials')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('dashboard'))

@app.route('/api/network_locations')
@login_required
def network_locations():
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
    # Get the same paginated networks as the table, but filter for GPS data
    networks_paginated = WigleData.query.filter(
        WigleData.latitude.isnot(None),
        WigleData.longitude.isnot(None),
        WigleData.latitude.between(-90, 90),  # Valid latitude range
        WigleData.longitude.between(-180, 180)  # Valid longitude range
    ).order_by(WigleData.first_seen.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    networks = networks_paginated.items
    
    return jsonify([{
        'ssid': net.ssid,
        'mac': net.mac,
        'auth_mode': net.auth_mode,
        'channel': net.channel,
        'rssi': net.rssi,
        'latitude': net.latitude,
        'longitude': net.longitude
    } for net in networks])

@app.route('/api/network_stats')
def network_stats():
    """
    Provides network discovery statistics over time
    Query params:
    - view_type: 'cumulative' or 'period'  
    - time_scale: minutes (5, 10, 30, 60)
    - start_time: ISO format datetime (optional)
    - end_time: ISO format datetime (optional)
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    try:
        view_type = request.args.get('view_type', 'cumulative')
        time_scale = int(request.args.get('time_scale', 30))  # minutes
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        
        print(f"📊 Network stats request: view_type={view_type}, time_scale={time_scale}, start_time={start_time_str}, end_time={end_time_str}")
        
        # Build query with time filtering
        query = db.session.query(WigleData).filter(
            WigleData.latitude.isnot(None),
            WigleData.longitude.isnot(None)
        )
        
        # Parse and apply time filters if provided
        filter_start_time = None
        filter_end_time = None
        
        if start_time_str:
            try:
                filter_start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                query = query.filter(WigleData.first_seen >= filter_start_time)
                print(f"📊 Filtering from: {filter_start_time}")
            except ValueError as e:
                print(f"⚠️ Invalid start_time format: {e}")
        
        if end_time_str:
            try:
                filter_end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                query = query.filter(WigleData.first_seen <= filter_end_time)
                print(f"📊 Filtering to: {filter_end_time}")
            except ValueError as e:
                print(f"⚠️ Invalid end_time format: {e}")
        
        networks = query.order_by(WigleData.first_seen.asc()).all()
        
        print(f"📊 Found {len(networks)} networks with GPS data (after time filtering)")
        
        if not networks:
            print("📊 No networks found, returning empty array")
            return jsonify([])
        
        # Determine the actual time range for bucketing
        if filter_start_time and filter_end_time:
            # Use the specified range
            start_time = filter_start_time
            end_time = filter_end_time
        elif filter_start_time:
            # Use specified start and data end
            start_time = filter_start_time
            end_time = networks[-1].first_seen
        elif filter_end_time:
            # Use data start and specified end
            start_time = networks[0].first_seen
            end_time = filter_end_time
        else:
            # Use full data range
            start_time = networks[0].first_seen
            end_time = networks[-1].first_seen
        
        print(f"📊 Time range: {start_time} to {end_time}")
        
        # Generate time buckets
        time_buckets = []
        current_time = start_time
        while current_time <= end_time:
            time_buckets.append(current_time)
            current_time += timedelta(minutes=time_scale)
        
        # If we don't have the final bucket, add it
        if time_buckets[-1] < end_time:
            time_buckets.append(end_time + timedelta(minutes=time_scale))
        
        print(f"📊 Created {len(time_buckets)} time buckets")
        
        results = []
        unique_networks_seen = set()
        
        for i, bucket_start in enumerate(time_buckets[:-1]):
            bucket_end = time_buckets[i + 1]
            
            # Find networks first seen in this time bucket
            bucket_networks = [n for n in networks 
                              if bucket_start <= n.first_seen < bucket_end]
            
            # Count unique networks in this bucket (by MAC address)
            unique_in_bucket = set(n.mac for n in bucket_networks)
            period_count = len(unique_in_bucket)
            
            # Add to cumulative set
            unique_networks_seen.update(unique_in_bucket)
            cumulative_count = len(unique_networks_seen)
            
            # Choose value based on view type
            count = cumulative_count if view_type == 'cumulative' else period_count
            
            results.append({
                'timestamp': bucket_start.isoformat(),
                'count': count,
                'label': bucket_start.strftime('%m/%d %H:%M')  # Keep this for fallback, but we'll use timestamp in JS
            })
        
        print(f"📊 Returning {len(results)} data points")
        return jsonify(results)
        
    except Exception as e:
        print(f"❌ Error in network_stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_database', methods=['POST'])
@login_required
def clear_database():
    try:
        num_networks = WigleData.query.delete()
        num_heartbeats = Heartbeat.query.delete()
        db.session.commit()
        return jsonify({
            "status": "success", 
            "message": f"Cleared {num_networks} networks and {num_heartbeats} heartbeats"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/wigle_data', methods=['POST'])
def receive_data():
    data = request.json
    print(f"📡 Received single network: {data.get('mac', 'Unknown')}")
    
    entry = WigleData(
        mac=data.get('mac', 'Unknown'),
        ssid=data.get('ssid', 'Unknown'),
        auth_mode=data.get('auth_mode', 'Unknown'),
        first_seen=datetime.now(timezone.utc),
        channel=data.get('channel', 0),
        rssi=data.get('rssi', 0),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        altitude=data.get('altitude'),
        accuracy=data.get('accuracy'),
        device_source="Legacy API"  # Single network API (likely old data)
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"status": "success"}), 201

@app.route('/api/wigle_data_batch', methods=['POST'])
def receive_batch():
    data = request.json
    networks = data.get('networks', [])
    
    print(f"📦 Received batch: {len(networks)} networks")
    
    # Try to determine device source (from cellular device)
    device_mac = data.get('device_mac')  # If provided in batch
    if device_mac:
        device = get_or_create_device(device_mac)
        device_source_name = device.name if device.name else device_mac
    else:
        # Fallback: try to find device from recent heartbeats based on timing
        recent_heartbeat = Heartbeat.query.order_by(Heartbeat.timestamp.desc()).first()
        if recent_heartbeat:
            if recent_heartbeat.timestamp.tzinfo is None:
                recent_heartbeat.timestamp = recent_heartbeat.timestamp.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - recent_heartbeat.timestamp).total_seconds() < 300:  # Within 5 minutes
                device = Device.query.filter_by(mac=recent_heartbeat.mac).first()
                device_source_name = device.name if (device and device.name) else recent_heartbeat.mac
            else:
                device_source_name = "Cellular Device"  # Fallback
        else:
            device_source_name = "Cellular Device"
    
    # ✅ This block must be *inside* the function too
    entries = []
    for net in networks:
        entry = WigleData(
            mac=net.get('mac', 'Unknown'),
            ssid=net.get('ssid', 'Unknown'),
            auth_mode=net.get('auth_mode', 'Unknown'),
            first_seen=datetime.now(timezone.utc),
            channel=net.get('channel', 0),
            rssi=net.get('rssi', 0),
            latitude=net.get('latitude'),
            longitude=net.get('longitude'),
            altitude=net.get('altitude'),
            accuracy=net.get('accuracy'),
            device_source=device_source_name
        )
        entries.append(entry)
        print(f"  📍 {net.get('ssid', 'Hidden')} ({net.get('mac', 'Unknown')}) from {device_source_name}")

    db.session.add_all(entries)
    db.session.commit()
    return jsonify({"status": "success", "count": len(entries)}), 201



@app.route('/api/heartbeat', methods=['POST'])
def receive_heartbeat():
    data = request.json
    mac = data.get('mac') or data.get('device_mac')
    print(f"💓 Heartbeat from {mac}")
    
    # Create or update device record
    get_or_create_device(mac)
    
    hb = Heartbeat(
        mac=mac,
        timestamp=datetime.now(timezone.utc),
        battery=data.get('battery') or data.get('battery_voltage', 0),
        solar_voltage=data.get('solar_voltage'),
        signal_quality=data.get('signal_quality'),
        free_heap=data.get('free_heap'),
        networks_cached=data.get('networks_cached'),
        gps_active=data.get('gps_active'),
        gps_satellites=data.get('gps_satellites')
    )
    db.session.add(hb)
    db.session.commit()
    return jsonify({"status": "success"}), 201

@app.route('/payload', methods=['POST'])
def receive_helium_payload():
    """
    Endpoint for Helium LoRaWAN webhook integration
    Converts Helium payload format to internal WigleData format
    """
    try:
        print("=" * 80)
        print("*** HELIUM WEBHOOK RECEIVED ***")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Content-Type: {request.content_type}")
        print(f"Content-Length: {request.content_length}")
        print("Raw request data:")
        raw_data = request.get_data()
        print(f"Raw bytes: {raw_data}")
        print(f"Raw string: {raw_data.decode('utf-8', errors='replace')}")
        
        # Try to parse JSON
        try:
            data = request.json
            print(f"Parsed JSON successfully: {data}")
        except Exception as json_error:
            print(f"❌ JSON parsing failed: {json_error}")
            print("❌ Request is not valid JSON!")
            return jsonify({"status": "error", "message": f"Invalid JSON: {str(json_error)}"}), 400
        
        if data is None:
            print("❌ request.json returned None")
            return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
        print("*** ANALYZING WEBHOOK STRUCTURE ***")
        print(f"Top-level keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        # Show complete webhook structure for debugging signal data location
        import json
        print("*** COMPLETE WEBHOOK STRUCTURE ***")
        print(json.dumps(data, indent=2, default=str))
        
        # Extract device information
        dev_eui = data.get('dev_eui', 'Unknown')
        device_name = data.get('name', 'LoRaWAN Device')
        print(f"Device EUI: {dev_eui}")
        print(f"Device Name: {device_name}")
        
        # Look for payload data in multiple possible locations
        payload = None
        print("*** SEARCHING FOR PAYLOAD DATA ***")
        
        # Check for flat structure (direct keys at top level)
        if 'ssid' in data and 'mac' in data:
            print("Found flat structure - creating payload from top-level keys")
            payload = {
                'ssid': data.get('ssid'),
                'mac': data.get('mac'),
                'rssi': data.get('rssi'),
                'channel': data.get('channel'),
                'encryption': data.get('encryption'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'altitude': data.get('altitude'),
                'sats': data.get('sats'),
                'hdop': data.get('hdop')
            }
            print(f"Created flat payload: {payload}")
        
        # Check for decoded payload (Helium Console format)
        elif 'decoded' in data:
            decoded = data['decoded']
            print(f"Found 'decoded' section: {decoded}")
            if 'payload' in decoded:
                payload = decoded['payload']
                print(f"Found payload in decoded.payload: {payload}")
        
        # Check for direct payload
        elif 'payload' in data:
            payload = data['payload']
            print(f"Found direct payload: {payload}")
        
        # Check for base64 payload that needs decoding
        elif 'payload_raw' in data:
            import base64
            raw_payload = data['payload_raw']
            print(f"Found raw payload (base64): {raw_payload}")
            try:
                decoded_bytes = base64.b64decode(raw_payload)
                print(f"Decoded bytes ({len(decoded_bytes)}): {decoded_bytes.hex()}")
                # This would need custom parsing based on our T-Beam struct
            except Exception as b64_error:
                print(f"Base64 decode error: {b64_error}")
        
        if not payload:
            print("❌ No payload found in any expected location")
            print("Available data structure:")
            import json
            print(json.dumps(data, indent=2, default=str))
            return jsonify({"status": "error", "message": "No payload data found"}), 400
        
        print("*** DETAILED PAYLOAD ANALYSIS ***")
        print(f"Payload type: {type(payload)}")
        print(f"Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
        print(f"Full payload: {payload}")
        
        # Map auth_mode from encryption type
        auth_mode_map = {
            0: "open",
            1: "wep", 
            2: "wpa",
            3: "wpa2",
            4: "wpa/wpa2",
            5: "wpa2_enterprise",
            6: "wpa3",
            7: "wpa2/wpa3",
            8: "wapi"
        }
        
        # Convert Helium payload to WigleData format
        mac = payload.get('mac', 'Unknown')
        ssid = payload.get('ssid', 'Unknown')
        try:
            encryption_type = int(payload.get('encryption', 0))
        except (ValueError, TypeError):
            encryption_type = 0
        auth_mode = auth_mode_map.get(encryption_type, 'unknown')
        
        print("*** EXTRACTED WIFI DATA ***")
        print(f"MAC: {mac}")
        print(f"SSID: {ssid}")
        print(f"Encryption Type: {encryption_type}")
        print(f"Auth Mode: {auth_mode}")
        print(f"Channel: {payload.get('channel', 0)}")
        print(f"RSSI: {payload.get('rssi', 0)}")
        
        # Handle GPS coordinates (Helium uses very small numbers for zero)
        latitude = payload.get('latitude', 0)
        longitude = payload.get('longitude', 0)
        
        print("*** GPS COORDINATE PROCESSING ***")
        print(f"Raw latitude: {latitude} (type: {type(latitude)})")
        print(f"Raw longitude: {longitude} (type: {type(longitude)})")
        
        # If coordinates are extremely small (< 0.001), treat as null/no GPS
        if abs(latitude) < 0.001:
            print("Latitude too small, setting to None")
            latitude = None
        if abs(longitude) < 0.001:
            print("Longitude too small, setting to None")
            longitude = None
            
        altitude = payload.get('altitude', 0) if payload.get('altitude', 0) != 0 else None
        
        print(f"Final latitude: {latitude}")
        print(f"Final longitude: {longitude}")
        print(f"Altitude: {altitude}")
        print(f"Satellites: {payload.get('sats', 0)}")
        print(f"HDOP: {payload.get('hdop', None)}")
        
        # Extract device health data
        battery_voltage = payload.get('battery_voltage', 0.0)
        gps_satellites = payload.get('gps_satellites', 0)
        
        print("*** DEVICE HEALTH DATA ***")
        print(f"Battery Voltage: {battery_voltage}V")
        if battery_voltage < 0:
            print(f"⚠️  WARNING: Negative battery voltage detected! Check AXP192 configuration or float parsing.")
        print(f"GPS Satellites (Health): {gps_satellites}")
        
        # Also create/update device record using DevEUI as MAC
        print(f"Creating/updating device record for {dev_eui}...")
        device = get_or_create_device(dev_eui)
        
        # Get device name (use custom name if set, otherwise use device name from webhook, otherwise use dev_eui)
        device_source_name = device.name if device.name else (device_name if device_name != "LoRaWAN Device" else dev_eui)
        
        # Create WigleData entry
        entry = WigleData(
            mac=mac,
            ssid=ssid,
            auth_mode=auth_mode,
            first_seen=datetime.now(timezone.utc),
            channel=payload.get('channel', 0),
            rssi=payload.get('rssi', 0),
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=payload.get('hdop', None),  # Using HDOP as accuracy approximation
            device_source=device_source_name  # Add device source name
        )
        
        print("*** DATABASE OPERATIONS ***")
        print(f"Adding WigleData entry with device source: {device_source_name}")
        db.session.add(entry)
        
        # Extract LoRaWAN signal quality from Helium metadata
        lorawan_rssi = data.get('rssi', -999)  # LoRaWAN RSSI from Helium
        lorawan_snr = data.get('snr', -999)    # LoRaWAN SNR from Helium
        
        # Handle fallback values (when RSSI/SNR not available)
        if lorawan_rssi == -999:
            lorawan_rssi = None
        if lorawan_snr == -999:
            lorawan_snr = 0  # Use 0 as fallback for signal quality field
        
        print("*** LORAWAN SIGNAL QUALITY ***")
        print(f"LoRaWAN RSSI: {lorawan_rssi if lorawan_rssi is not None else 'N/A'} dBm")
        print(f"LoRaWAN SNR: {lorawan_snr} dB")
        if lorawan_rssi == -999 or lorawan_snr == 0:
            print("⚠️  WARNING: Using fallback signal values. Check if Helium provides 'rssi' and 'snr' at top level.")
            print("    Available top-level keys in webhook:", list(data.keys()))
        
        # Create heartbeat with health data piggybacked from network transmission
        hb = Heartbeat(
            mac=dev_eui,
            timestamp=datetime.now(timezone.utc),
            battery=battery_voltage,  # Now using actual battery voltage from device
            solar_voltage=None,  # T-Beam doesn't have solar
            signal_quality=lorawan_snr,  # Use LoRaWAN SNR as signal quality (more reliable than RSSI)
            free_heap=None,  # Not available in LoRaWAN payload
            networks_cached=None,  # Not available in LoRaWAN payload
            gps_active=(latitude is not None and longitude is not None),
            gps_satellites=gps_satellites  # Using device health GPS satellite count
        )
        print(f"Creating heartbeat with battery: {battery_voltage}V, SNR: {lorawan_snr}dB, GPS sats: {gps_satellites}")
        db.session.add(hb)
        
        print("Committing database transaction...")
        db.session.commit()
        
        print(f"✅ Successfully stored LoRaWAN network: {ssid} ({mac}) from device {device_name}")
        print("=" * 80)
        
        return jsonify({"status": "success", "message": "Data stored successfully"}), 200
        
    except Exception as e:
        print("=" * 80)
        print(f"❌ CRITICAL ERROR processing Helium payload: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        print(f"Raw request data: {request.get_data()}")
        print(f"Request headers: {dict(request.headers)}")
        print("=" * 80)
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/csv')
@login_required
def download_csv():
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # WiGLE format header
    writer.writerow(['WigleWifi-1.6,appRelease=2.78,model=LilyGO-SIM7000G,release=1.0.0,device=wardriving,display=ESP32,board=SIM7000G,"brand=LilyGO",star=Sol,body=3,subBody=0'])
    writer.writerow(['MAC', 'SSID', 'AuthMode', 'FirstSeen', 'Channel', 'RSSI', 
                     'CurrentLatitude', 'CurrentLongitude', 'AltitudeMeters', 'AccuracyMeters', 'Type'])
    
    for net in WigleData.query.all():
        writer.writerow([
            net.mac, 
            net.ssid, 
            f'[{net.auth_mode}]', 
            net.first_seen.strftime('%Y-%m-%d %H:%M:%S'),
            net.channel, 
            net.rssi, 
            net.latitude or '', 
            net.longitude or '', 
            net.altitude or '', 
            net.accuracy or '', 
            'WIFI'
        ])
    
    return Response(
        output.getvalue(), 
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=wigle_data.csv"}
    )

@app.route('/status')
def status():
    return jsonify({
        "status": "online", 
        "timestamp": datetime.now().isoformat(),
        "networks": WigleData.query.count(),
        "devices": Heartbeat.query.count(),
        "mode": "production"
    })

# New endpoints for device management, settings, and WiGLE upload

@app.route('/device/<mac>')
@login_required
def device_detail(mac):
    device = get_or_create_device(mac)
    
    # Get all heartbeats for this device
    heartbeats = Heartbeat.query.filter_by(mac=mac).order_by(Heartbeat.timestamp.desc()).limit(100).all()
    
    if not heartbeats:
        return render_template_string("""
        <h1>Device Not Found</h1>
        <p>No data found for device: {{ mac }}</p>
        <a href="/">Back to Dashboard</a>
        """, mac=mac)
    
    # Get latest heartbeat for current status
    latest_hb = heartbeats[0]
    
    # Convert heartbeats to serializable format for charts
    heartbeat_data = []
    for hb in heartbeats:
        heartbeat_data.append({
            'timestamp': hb.timestamp.isoformat(),
            'battery': hb.battery,
            'signal_quality': hb.signal_quality,
            'solar_voltage': hb.solar_voltage,
            'free_heap': hb.free_heap,
            'networks_cached': hb.networks_cached,
            'gps_active': hb.gps_active,
            'gps_satellites': hb.gps_satellites
        })
    
    return render_template_string(DEVICE_DETAIL_TEMPLATE, 
                                  device=device, 
                                  mac=mac,
                                  heartbeats=heartbeat_data,
                                  heartbeats_raw=heartbeats,
                                  latest_hb=latest_hb)

@app.route('/settings')
@login_required  
def settings():
    import time
    
    wigle_api_key = get_wigle_api_key()
    
    # Get statistics
    total_networks = WigleData.query.count()
    uploaded_networks = WigleData.query.filter_by(uploaded_to_wigle=True).count()
    pending_networks = total_networks - uploaded_networks
    
    # Get database info
    db_info = {
        'name': 'wigle_data.db',
        'devices': Device.query.count(),
        'heartbeats': Heartbeat.query.count()
    }
    
    uptime = "Active"  # Simplified for now
    
    return render_template_string(SETTINGS_TEMPLATE,
                                  wigle_api_key=wigle_api_key,
                                  total_networks=total_networks,
                                  uploaded_networks=uploaded_networks,
                                  pending_networks=pending_networks,
                                  db_info=db_info,
                                  uptime=uptime)

# Device name editing endpoint
@app.route('/api/device/<mac>/name', methods=['POST'])
@login_required
def update_device_name(mac):
    try:
        data = request.json
        name = data.get('name', '').strip()
        
        device = get_or_create_device(mac)
        device.name = name if name else None
        db.session.commit()
        
        return jsonify({"status": "success", "message": "Device name updated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Settings management endpoints
@app.route('/api/settings/wigle', methods=['POST'])
@login_required
def save_wigle_settings():
    try:
        data = request.json
        api_key = data.get('api_key', '').strip()
        
        if api_key:
            set_wigle_api_key(api_key)
            return jsonify({"status": "success", "message": "WiGLE API key saved"})
        else:
            return jsonify({"status": "error", "message": "API key cannot be empty"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/settings/wigle', methods=['DELETE'])
@login_required
def clear_wigle_settings():
    try:
        setting = Settings.query.filter_by(key='wigle_api_key').first()
        if setting:
            db.session.delete(setting)
            db.session.commit()
        return jsonify({"status": "success", "message": "WiGLE API key cleared"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# WiGLE API integration
@app.route('/api/test_wigle', methods=['POST'])
@login_required
def test_wigle_connection():
    try:
        data = request.json
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({"status": "error", "message": "API key required"}), 400
        
        import requests
        
        # Test WiGLE API connection
        headers = {
            'Authorization': f'Basic {api_key}',
            'User-Agent': 'WiFi-Wardriving-System/1.0'
        }
        
        response = requests.get('https://api.wigle.net/api/v2/profile/user', 
                               headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            username = user_data.get('user', 'Unknown')
            return jsonify({
                "status": "success", 
                "message": "Connection successful",
                "user": username
            })
        else:
            return jsonify({
                "status": "error", 
                "message": f"API returned status {response.status_code}"
            }), 400
            
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Connection failed: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/network/<int:network_id>', methods=['DELETE'])
@login_required
def delete_network(network_id):
    try:
        network = WigleData.query.get_or_404(network_id)
        db.session.delete(network)
        db.session.commit()
        return jsonify({
            "status": "success", 
            "message": f"Network {network.mac} deleted successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/upload_to_wigle', methods=['POST'])
@login_required
def upload_to_wigle():
    try:
        api_key = get_wigle_api_key()
        if not api_key:
            return jsonify({"status": "error", "message": "No WiGLE API key configured"}), 400
        
        # Get networks that haven't been uploaded and have GPS data
        pending_networks = WigleData.query.filter(
            WigleData.uploaded_to_wigle == False,
            WigleData.latitude.isnot(None),
            WigleData.longitude.isnot(None)
        ).limit(100).all()  # Limit to 100 at a time
        
        if not pending_networks:
            return jsonify({"status": "error", "message": "No networks with GPS data to upload"}), 400
        
        import requests
        from io import StringIO
        import csv
        
        # Create CSV data for WiGLE
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        
        # WiGLE CSV header
        writer.writerow(['MAC', 'SSID', 'AuthMode', 'FirstSeen', 'Channel', 'RSSI', 
                        'CurrentLatitude', 'CurrentLongitude', 'AltitudeMeters', 'AccuracyMeters', 'Type'])
        
        for net in pending_networks:
            writer.writerow([
                net.mac,
                net.ssid,
                f'[{net.auth_mode}]',
                net.first_seen.strftime('%Y-%m-%d %H:%M:%S'),
                net.channel,
                net.rssi,
                net.latitude,
                net.longitude,
                net.altitude or '',
                net.accuracy or '',
                'WIFI'
            ])
        
        csv_data = csv_buffer.getvalue()
        
        # Upload to WiGLE
        headers = {
            'Authorization': f'Basic {api_key}',
            'User-Agent': 'WiFi-Wardriving-System/1.0'
        }
        
        files = {
            'file': ('wardriving_data.csv', csv_data, 'text/csv'),
            'donate': ('', 'false')
        }
        
        response = requests.post('https://api.wigle.net/api/v2/file/upload',
                               headers=headers, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # Mark networks as uploaded
                for net in pending_networks:
                    net.uploaded_to_wigle = True
                db.session.commit()
                
                return jsonify({
                    "status": "success",
                    "count": len(pending_networks),
                    "message": f"Successfully uploaded {len(pending_networks)} networks to WiGLE"
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": f"WiGLE rejected upload: {result.get('message', 'Unknown error')}"
                }), 400
        else:
            return jsonify({
                "status": "error",
                "message": f"WiGLE API returned status {response.status_code}"
            }), 400
            
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Upload failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def update_existing_data():
    """Update existing WigleData records without device_source to have a default value"""
    try:
        # Count records without device_source
        null_count = WigleData.query.filter(WigleData.device_source.is_(None)).count()
        if null_count > 0:
            print(f"🔄 Updating {null_count} existing records without device source...")
            
            # Update all NULL device_source records to "Legacy Data"
            WigleData.query.filter(WigleData.device_source.is_(None)).update(
                {WigleData.device_source: "Legacy Data"}, 
                synchronize_session=False
            )
            db.session.commit()
            print(f"✅ Updated {null_count} records with default device source")
        else:
            print("✅ All records already have device source information")
    except Exception as e:
        print(f"⚠️ Error updating existing data: {e}")
        db.session.rollback()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("📊 Database tables created/verified")
        
        # Update existing data after schema changes
        update_existing_data()
    
    print("🚀 Starting WiFi Wardriving Production Server...")
    print("📍 Production mode - accessible on port 5001")
    print("🔗 Dashboard: http://localhost:5001")
    print("🔐 Login: lozaning / oneill")
    print("")
    
    app.run(host='0.0.0.0', port=5001, debug=False)