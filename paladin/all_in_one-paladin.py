import serial
import paho.mqtt.client as mqtt
import time
import json
import logging
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# UART Configuration
SERIAL_PORT = "/dev/ttyS1"  # Adjust as needed
BAUD_RATE = 57600           # Match ESPHome config

# MQTT Configuration
MQTT_BROKER = "192.168.X.X"  # Adjust to your broker's address
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "homeassistant/sensor/paladin"

# Sensor Names (for MQTT publishing)
SENSOR_NAMES = [
    "mains_watts", "transfer_watts", "sensor_2", "water_temp", "delta_t", "min_temp", "max_temp", 
    "grid_in", "grid_out", "transfer", "top_up", "sensor_11", "hhours", "inverter_status", "charger_control", 
    "solar_export_flag", "export_limit", "allow_import_flag", "offset_flag", "time_hack"
]

# --- Helper Functions ---

def send_time_to_serial(ser_instance):
    """
    Gets the current time, calculates the seconds since the beginning of the day,
    formats it, and sends it over the provided serial port instance.
    """
    try:
        now = datetime.datetime.now()
        seconds_today = now.hour * 3600 + now.minute * 60 + now.second
        time_string = f"T{seconds_today}"
        data_to_send = time_string.encode('utf-8')

        logging.info(f"Attempting to send time: '{time_string}' (bytes: {data_to_send})")
        
        # Ensure the serial port is open before writing
        if not ser_instance.is_open:
            ser_instance.open() # Re-open if it was closed for some reason
            logging.info(f"Serial port {ser_instance.name} re-opened for time send.")

        bytes_written = ser_instance.write(data_to_send)
        ser_instance.flush() # Ensure all data is written to the serial port
        logging.info(f"Successfully sent {bytes_written} bytes: '{time_string}' to {ser_instance.name}")
        
    except serial.SerialException as e:
        logging.error(f"Serial port error during time send on '{ser_instance.port}': {e}")
        logging.error("Please check device connection, permissions, and baud rate.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during time send: {e}")

def send_to_mqtt(client, sensor, value):
    """Publishes sensor data to MQTT."""
    topic = f"{MQTT_TOPIC_PREFIX}/{sensor}"
    client.publish(topic, value, retain=True)
    logging.info(f"Published {sensor}: {value}")

def parse_uart_data(data):
    """Parses raw UART data into a list of values."""
    try:
        logging.debug(f"Raw UART Data: {data}")
        # Assuming 20 values are always expected based on SENSOR_NAMES length
        values = [float(x) if x.replace('.', '', 1).isdigit() else None for x in data.strip().split(",")]
        if len(values) == 20: # Ensure the number of parsed values matches expected sensors
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
        # Special handling for specific sensors if needed (e.g., unit for temperature)
        if "temp" in sensor:
            payload["unit_of_measurement"] = "°C"
            payload["device_class"] = "temperature"
        elif "time_hack" in sensor: # Example: if time_hack is an integer, it might not need units
            payload["unit_of_measurement"] = None
            payload["device_class"] = None
        
        client.publish(discovery_topic, json.dumps(payload), retain=True)
        logging.info(f"Published MQTT discovery for {sensor}")

def main():
    # Initialize UART
    ser = None
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        logging.info(f"UART port {SERIAL_PORT} opened successfully.")
    except Exception as e:
        logging.error(f"Failed to open UART port {SERIAL_PORT}: {e}")
        return
    
    # Initialize MQTT
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start() # Start MQTT background loop
        logging.info("Connected to MQTT Broker")
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker {MQTT_BROKER}: {e}")
        # It's better to close the serial port if MQTT fails, or handle graceful exit
        if ser and ser.is_open:
            ser.close()
        return
    
    # Publish MQTT auto-discovery messages
    publish_discovery_messages(client)
    
    # Initialize last_time_sent to current time to send it immediately on startup
    last_time_sent = time.time() - 3600 # Subtract 1 hour to trigger immediate send
    send_time_to_serial(ser) # Send time immediately on startup

    while True:
        try:
            # --- Send Time Task (Every Hour) ---
            current_time = time.time()
            if current_time - last_time_sent >= 3600: # 3600 seconds = 1 hour
                logging.info("It's time to send the current time to the serial device.")
                send_time_to_serial(ser)
                last_time_sent = current_time # Update the last sent time

            # --- UART to MQTT Task (Every 30 Seconds) ---
            ser.write(b"A")  # Send command to ESPHome device
            time.sleep(0.1)  # Give time for response
            response = ser.readline().decode("utf-8", errors="ignore").strip()
            
            if response:
                logging.info(f"Received UART response: {response}")
                values = parse_uart_data(response)
                if values:
                    for i, sensor in enumerate(SENSOR_NAMES):
                        # Ensure index is within bounds and value is not None
                        if i < len(values) and values[i] is not None:
                            send_to_mqtt(client, sensor, values[i])
                    logging.info("Data sent to MQTT")
                else:
                    logging.warning("Invalid or incomplete data received from UART, skipping MQTT publish.")
            else:
                logging.warning("No data received from UART within timeout period.")
            
        except serial.SerialException as e:
            logging.error(f"Serial communication error: {e}. Attempting to re-establish connection...")
            # Attempt to re-open serial port on error
            if ser and ser.is_open:
                ser.close()
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                logging.info("Successfully re-opened serial port.")
            except Exception as e_reopen:
                logging.critical(f"Failed to re-open serial port: {e_reopen}. Script will exit.")
                break # Exit the loop if critical error
        except paho.mqtt.client.MqttError as e:
            logging.error(f"MQTT error: {e}. Attempting to reconnect to broker...")
            # MQTT client's loop_start() should handle re-connection, but explicit check might be needed
            client.reconnect()
        except Exception as e:
            logging.error(f"An unexpected error occurred in main loop: {e}")
        
        # This sleep ensures the main loop runs roughly every 30 seconds
        # The time sending is checked within this 30-second interval.
        time.sleep(30)

if __name__ == "__main__":
    main()
