import serial
import paho.mqtt.client as mqtt
import time
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# UART Configuration
SERIAL_PORT = "/dev/ttyS1"  # Adjust as needed
BAUD_RATE = 57600  # Match ESPHome config

# MQTT Configuration
MQTT_BROKER = "192.168.x.x"  # Adjust to your broker's address
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "homeassistant/sensor/paladin"

# Sensor Names
SENSOR_NAMES = [
    "mains_watts", "transfer_watts", "sensor_2", "water_temp", "delta_t", "min_temp", "max_temp", 
    "grid_in", "grid_out", "transfer", "top_up", "sensor_11", "hhours", "inverter_status", "charger_control", 
    "solar_export_flag", "export_limit", "allow_import_flag", "offset_flag", "time_hack"
]

def send_to_mqtt(client, sensor, value):
    topic = f"{MQTT_TOPIC_PREFIX}/{sensor}"
    client.publish(topic, value, retain=True)
    logging.info(f"Published {sensor}: {value}")

def parse_uart_data(data):
    try:
        logging.debug(f"Raw UART Data: {data}")
        values = [float(x) if x.replace('.', '', 1).isdigit() else None for x in data.strip().split(",")]
        if len(values) == 20:
            logging.info(f"Parsed Values: {values}")
            return values
        else:
            logging.warning(f"Unexpected data length: {len(values)} - Data: {data}")
    except ValueError as e:
        logging.error(f"Parsing Error: {e} - Data: {data}")
    return None

def publish_discovery_messages(client):
    """Publish MQTT discovery messages for Home Assistant."""
    for sensor in SENSOR_NAMES:
        discovery_topic = f"homeassistant/sensor/paladin_{sensor}/config"
        payload = {
            "name": f"Paladin {sensor.replace('_', ' ').title()}",
            "state_topic": f"{MQTT_TOPIC_PREFIX}/{sensor}",
            "unique_id": f"paladin_{sensor}",
            "device": {
                "identifiers": ["paladin_device"],
                "name": "Paladin Energy System",
                "manufacturer": "Paladin",
                "model": "Custom UART Sensor"
            },
            "unit_of_measurement": "W" if "watts" in sensor else None,
            "device_class": "power" if "watts" in sensor else None,
            "state_class": "measurement"
        }
        client.publish(discovery_topic, json.dumps(payload), retain=True)
        logging.info(f"Published MQTT discovery for {sensor}")

def main():
    # Initialize UART
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        logging.error(f"Failed to open UART: {e}")
        return
    
    # Initialize MQTT
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        logging.info("Connected to MQTT Broker")
    except Exception as e:
        logging.error(f"Failed to connect to MQTT: {e}")
        return
    
    # Publish MQTT auto-discovery messages
    publish_discovery_messages(client)
    
    while True:
        try:
            ser.write(b"A")  # Send command
            time.sleep(0.1)  # Give time for response
            response = ser.readline().decode("utf-8", errors="ignore").strip()
            
            if response:
                logging.info(f"Received UART response: {response}")
                values = parse_uart_data(response)
                if values:
                    for i, sensor in enumerate(SENSOR_NAMES):
                        if values[i] is not None:
                            send_to_mqtt(client, sensor, values[i])
                    logging.info("Data sent to MQTT")
                else:
                    logging.warning("Invalid response received")
            else:
                logging.warning("No data received from UART")
            
        except Exception as e:
            logging.error(f"Error: {e}")
        
        time.sleep(30)  # Repeat every 30 seconds

if __name__ == "__main__":
    main()

