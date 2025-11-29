from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import json
import threading
import time
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect('farm_data.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_id TEXT,
                  soil_moisture REAL,
                  water_level REAL,
                  soil_temperature REAL,
                  air_temperature REAL,
                  air_humidity REAL,
                  light_intensity REAL,
                  co2_level REAL,
                  soil_npk REAL,
                  pump_status INTEGER,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS commands
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_id TEXT,
                  command_type TEXT,
                  command_value TEXT,
                  executed INTEGER DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS crop_problems
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  problem_type TEXT,
                  symptoms TEXT,
                  causes TEXT,
                  solutions TEXT,
                  pesticides TEXT,
                  organic_remedies TEXT)''')
    
    conn.commit()
    conn.close()
    
    # Insert sample crop problem data
    insert_sample_data()

def insert_sample_data():
    conn = sqlite3.connect('farm_data.db')
    c = conn.cursor()
    
    # Clear existing data
    c.execute('DELETE FROM crop_problems')
    
    problems = [
        ("Nitrogen Deficiency", "Yellowing of older leaves, stunted growth", 
         "Poor soil fertility, inadequate fertilization", 
         "Apply nitrogen-rich fertilizers, use legume cover crops",
         "Urea (100-150 kg/ha), Ammonium Sulfate",
         "Vermicompost, neem cake, cow dung manure"),
        
        ("Phosphorus Deficiency", "Purple or reddish leaves, poor root development",
         "Acidic soil, cold temperatures, compacted soil",
         "Apply phosphorus fertilizers, maintain soil pH 6-7",
         "DAP (60-80 kg/ha), SSP",
         "Bone meal, rock phosphate, compost"),
        
        ("Potassium Deficiency", "Yellow leaf margins, weak stems",
         "Sandy soil, excessive leaching, imbalanced fertilization",
         "Apply potassium fertilizers, improve organic matter",
         "MOP (40-60 kg/ha), Potassium Sulfate",
         "Wood ash, banana peels, compost"),
        
        ("Water Stress", "Wilting leaves, dry soil, slow growth",
         "Insufficient irrigation, high temperature, poor water retention",
         "Increase irrigation frequency, add mulch, improve soil organic matter",
         "Not applicable",
         "Mulching, water conservation techniques, organic matter addition"),
        
        ("Over Watering", "Yellow leaves, root rot, fungal growth",
         "Excessive irrigation, poor drainage",
         "Reduce watering frequency, improve soil drainage",
         "Not applicable",
         "Improve drainage, add organic matter"),
        
        ("Aphid Infestation", "Curled leaves, sticky residue, stunted growth",
         "Soft-bodied insects sucking plant sap",
         "Use insecticidal soap, introduce beneficial insects",
         "Imidacloprid (0.5 ml/L), Acetamiprid",
         "Neem oil spray, garlic-chili solution, ladybugs"),
        
        ("Fungal Infection", "White powdery substance, leaf spots, rot",
         "High humidity, poor air circulation, contaminated soil",
         "Improve ventilation, remove affected parts, apply fungicide",
         "Carbendazim (1g/L), Copper oxychloride",
         "Baking soda solution, neem oil, proper spacing")
    ]
    
    c.executemany('''INSERT INTO crop_problems 
                    (problem_type, symptoms, causes, solutions, pesticides, organic_remedies) 
                    VALUES (?, ?, ?, ?, ?, ?)''', problems)
    
    conn.commit()
    conn.close()
    print("✅ Sample crop data inserted successfully")

init_db()

# AI-based problem detection
class CropProblemDetector:
    def detect_problems(self, sensor_data):
        problems = []
        
        # Check soil moisture
        if sensor_data['soil_moisture'] < 30:
            problems.append({
                'type': 'Water Stress',
                'confidence': 85,
                'solution': 'Increase irrigation frequency and add organic mulch',
                'immediate_action': 'Start irrigation pump'
            })
        elif sensor_data['soil_moisture'] > 80:
            problems.append({
                'type': 'Over Watering',
                'confidence': 75,
                'solution': 'Reduce irrigation frequency and improve drainage',
                'immediate_action': 'Stop irrigation pump'
            })
        
        # Check soil nutrients
        if sensor_data['soil_npk'] < 30:
            problems.append({
                'type': 'Nitrogen Deficiency',
                'confidence': 80,
                'solution': 'Apply nitrogen-rich fertilizer or organic compost',
                'immediate_action': 'Add vermicompost or urea'
            })
        elif sensor_data['soil_npk'] < 50:
            problems.append({
                'type': 'Phosphorus Deficiency',
                'confidence': 70,
                'solution': 'Apply phosphorus fertilizers or bone meal',
                'immediate_action': 'Add DAP or rock phosphate'
            })
        
        # Check environmental conditions
        if sensor_data['air_temperature'] > 35:
            problems.append({
                'type': 'Heat Stress',
                'confidence': 65,
                'solution': 'Provide shade and increase watering frequency',
                'immediate_action': 'Use shade nets and ensure adequate moisture'
            })
        
        return problems

detector = CropProblemDetector()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        print(f"✅ Received sensor data: {data}")
        
        # Store in database
        conn = sqlite3.connect('farm_data.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO sensor_data 
                    (device_id, soil_moisture, water_level, soil_temperature, 
                     air_temperature, air_humidity, light_intensity, co2_level, 
                     soil_npk, pump_status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['device_id'], data['soil_moisture'], data['water_level'],
                   data['soil_temperature'], data['air_temperature'], 
                   data['air_humidity'], data['light_intensity'], data['co2_level'],
                   data['soil_npk'], data['pump_status']))
        
        conn.commit()
        conn.close()
        
        # Auto control pump based on soil moisture
        if data['soil_moisture'] < 30 and data['water_level'] > 20:
            send_command(data['device_id'], 'pump_control', True)
            print("🔄 Auto: Starting pump - Low soil moisture")
        elif data['soil_moisture'] > 70:
            send_command(data['device_id'], 'pump_control', False)
            print("🔄 Auto: Stopping pump - Soil moisture adequate")
        
        return jsonify({"status": "success", "message": "Data received"})
    
    except Exception as e:
        print(f"❌ Error receiving sensor data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/commands/<device_id>', methods=['GET'])
def get_commands(device_id):
    try:
        conn = sqlite3.connect('farm_data.db')
        c = conn.cursor()
        
        c.execute('''SELECT command_type, command_value FROM commands 
                    WHERE device_id = ? AND executed = 0''', (device_id,))
        
        commands = []
        for row in c.fetchall():
            commands.append({
                'command_type': row[0],
                'command_value': row[1]
            })
            
            # Mark as executed
            c.execute('UPDATE commands SET executed = 1 WHERE device_id = ? AND command_type = ? AND executed = 0', 
                     (device_id, row[0]))
        
        conn.commit()
        conn.close()
        
        print(f"📡 Sending commands to {device_id}: {commands}")
        return jsonify(commands)
    
    except Exception as e:
        print(f"❌ Error getting commands: {e}")
        return jsonify([])

@app.route('/api/control-pump', methods=['POST'])
def control_pump():
    data = request.get_json()
    device_id = data.get('device_id', 'farm_unit_001')
    pump_state = data.get('pump_state', False)
    
    send_command(device_id, 'pump_control', pump_state)
    
    action = "ON" if pump_state else "OFF"
    print(f"🔧 Manual: Pump turned {action}")
    
    return jsonify({"status": "success", "pump_state": pump_state})

@app.route('/api/activate-sound', methods=['POST'])
def activate_sound():
    data = request.get_json()
    device_id = data.get('device_id', 'farm_unit_001')
    
    send_command(device_id, 'sound_alert', True)
    
    print("🔊 Manual: Sound repellent activated")
    return jsonify({"status": "success", "sound_activated": True})

@app.route('/api/current-status', methods=['GET'])
def get_current_status():
    try:
        conn = sqlite3.connect('farm_data.db')
        c = conn.cursor()
        
        c.execute('''SELECT * FROM sensor_data 
                    ORDER BY timestamp DESC LIMIT 1''')
        
        row = c.fetchone()
        conn.close()
        
        if row:
            sensor_data = {
                'soil_moisture': row[2],
                'water_level': row[3],
                'soil_temperature': row[4],
                'air_temperature': row[5],
                'air_humidity': row[6],
                'light_intensity': row[7],
                'co2_level': row[8],
                'soil_npk': row[9],
                'pump_status': row[10],
                'timestamp': row[11]
            }
            
            # Detect problems
            problems = detector.detect_problems(sensor_data)
            
            return jsonify({
                'sensor_data': sensor_data,
                'detected_problems': problems,
                'overall_health': calculate_health_score(sensor_data)
            })
        
        return jsonify({"error": "No data available"})
    
    except Exception as e:
        print(f"❌ Error getting current status: {e}")
        return jsonify({"error": "Database error"})

@app.route('/api/crop-problems', methods=['GET'])
def get_crop_problems():
    problem_type = request.args.get('type', '')
    
    conn = sqlite3.connect('farm_data.db')
    c = conn.cursor()
    
    if problem_type:
        c.execute('SELECT * FROM crop_problems WHERE problem_type LIKE ?', 
                 (f'%{problem_type}%',))
    else:
        c.execute('SELECT * FROM crop_problems')
    
    problems = []
    for row in c.fetchall():
        problems.append({
            'id': row[0],
            'problem_type': row[1],
            'symptoms': row[2],
            'causes': row[3],
            'solutions': row[4],
            'pesticides': row[5],
            'organic_remedies': row[6]
        })
    
    conn.close()
    return jsonify(problems)

@app.route('/api/voice-command', methods=['POST'])
def handle_voice_command():
    data = request.get_json()
    command = data.get('command', '').lower()
    
    response = process_voice_command(command)
    
    return jsonify({"response": response})

def process_voice_command(command):
    if 'pump' in command and 'on' in command:
        send_command('farm_unit_001', 'pump_control', True)
        return "Turning water pump ON"
    elif 'pump' in command and 'off' in command:
        send_command('farm_unit_001', 'pump_control', False)
        return "Turning water pump OFF"
    elif 'soil' in command and 'moisture' in command:
        # Get current moisture
        status = get_current_status().get_json()
        if 'sensor_data' in status:
            moisture = status['sensor_data'].get('soil_moisture', 0)
            return f"Current soil moisture is {moisture}%"
        return "Soil moisture data not available"
    elif 'problem' in command or 'issue' in command:
        status = get_current_status().get_json()
        problems = status.get('detected_problems', [])
        if problems:
            return f"Detected {len(problems)} problems. {problems[0]['type']} - {problems[0]['solution']}"
        else:
            return "No major problems detected. Your crops are healthy!"
    else:
        return "I can help you with pump control, soil moisture checks, and crop problem detection."

def send_command(device_id, command_type, command_value):
    try:
        conn = sqlite3.connect('farm_data.db')
        c = conn.cursor()
        
        # Clear previous unexecuted commands of same type
        c.execute('DELETE FROM commands WHERE device_id = ? AND command_type = ? AND executed = 0', 
                 (device_id, command_type))
        
        # Insert new command
        c.execute('INSERT INTO commands (device_id, command_type, command_value) VALUES (?, ?, ?)', 
                 (device_id, command_type, str(command_value)))
        
        conn.commit()
        conn.close()
        print(f"📝 Command saved: {device_id} - {command_type} = {command_value}")
    
    except Exception as e:
        print(f"❌ Error sending command: {e}")

def calculate_health_score(sensor_data):
    score = 100
    
    # Deduct points based on sensor readings
    if sensor_data['soil_moisture'] < 30 or sensor_data['soil_moisture'] > 80:
        score -= 30
    elif sensor_data['soil_moisture'] < 40 or sensor_data['soil_moisture'] > 70:
        score -= 15
    
    if sensor_data['soil_npk'] < 30:
        score -= 25
    elif sensor_data['soil_npk'] < 50:
        score -= 10
    
    if sensor_data['air_temperature'] > 35:
        score -= 10
    
    return max(score, 0)

if __name__ == '__main__':
    print("🚀 Starting KrishiSanjeevani 3.0 Server...")
    print("📍 Server running on: http://0.0.0.0:5000")
    print("📍 Local access: http://localhost:5000")
    print("📍 Network access: http://[YOUR-IP]:5000")
    print("📊 Dashboard: Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)