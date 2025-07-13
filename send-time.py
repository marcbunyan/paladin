import serial
import datetime
import time

# --- IMPORTANT: ARDUINO_DISPLAY_UTC_OFFSET_COMPENSATION_SECONDS ---
# This value compensates for the Arduino displaying time as UTC,
# while you want it to display NZ local time (NZST/NZDT).
# NZST is UTC+12 hours. NZDT (during daylight saving) is UTC+13 hours.
# You need to add this offset to the UTC UNIX timestamp before sending.
# Use 12 hours for NZST, or 13 hours for NZDT.
# 12 hours = 12 * 60 * 60 = 43200 seconds
# 13 hours = 13 * 60 * 60 = 46800 seconds

# Since your 'date' command showed 'NZST', we'll use +12 hours for now.
# You will need to manually change this to 46800 when NZ goes into Daylight Saving Time.
ARDUINO_DISPLAY_UTC_OFFSET_COMPENSATION_SECONDS = 12 * 3600 # For NZST (UTC+12)

def send_compensated_unix_time_to_serial():
    """
    Gets the current UNIX timestamp, adds the NZST/NZDT offset to it (since Arduino displays UTC),
    prefixes it with 'T', and sends it over the serial port.
    The script's console output will show the time based on the Omega's local system clock.
    """
    serial_port = "/dev/ttyS1"
    baud_rate = 57600
    
    try:
        # Get current actual UTC UNIX timestamp
        actual_current_unix_timestamp_utc = int(time.time())

        # Calculate the compensated UNIX timestamp to send to Arduino
        # This makes the Arduino's UTC display match NZ local time
        unix_timestamp_to_send = actual_current_unix_timestamp_utc + ARDUINO_DISPLAY_UTC_OFFSET_COMPENSATION_SECONDS

        # --- For internal script reporting/printing ---
        # Get current time based on the Omega's system clock (which is NZST/NZDT)
        local_now_dt = datetime.datetime.now()
        # --- End of simple local time reporting ---

        # The actual data to send: 'T' + compensated UNIX timestamp as a string
        time_string_to_send = f"T{unix_timestamp_to_send}"
        data_to_send = time_string_to_send.encode('utf-8')

        print(f"Script started at (Omega System Time): {local_now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Current actual UTC UNIX timestamp (before compensation): {actual_current_unix_timestamp_utc}")
        print(f"Applying compensation of +{ARDUINO_DISPLAY_UTC_OFFSET_COMPENSATION_SECONDS} seconds (for NZST).")
        print(f"UNIX timestamp to send to Arduino (after compensation): {unix_timestamp_to_send}")
        print(f"Attempting to open serial port: {serial_port} at {baud_rate} baud.")
        
        with serial.Serial(serial_port, baud_rate, timeout=1) as ser:
            print(f"Serial port {ser.name} opened successfully.")
            print(f"Attempting to send: '{time_string_to_send}' (bytes: {data_to_send})")
            print(f"This should make the Arduino display: {local_now_dt.strftime('%H:%M:%S')} (NZ local time).")
            
            bytes_written = ser.write(data_to_send)
            ser.flush()

            print(f"Successfully sent {bytes_written} bytes: '{time_string_to_send}' to {serial_port}")
            
            # time.sleep(0.1) # Optional delay

    except serial.SerialException as e:
        print(f"Serial port error on '{serial_port}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    send_compensated_unix_time_to_serial()
