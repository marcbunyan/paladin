import serial
import datetime
import time # For a small delay if needed

def send_time_to_serial():
    """
    Gets the current time, calculates the seconds since the beginning of the day,
    formats it, and sends it over the serial port once.
    Uses parameters from the user's working serial reading script.
    """
    # Configuration from your working example
    serial_port = "/dev/ttyS1"  # Adjusted as per your working script
    baud_rate = 57600        # Adjusted as per your working script

    try:
        # Get current time
        now = datetime.datetime.now()

        # Calculate seconds since the beginning of the day
        seconds_today = now.hour * 3600 + now.minute * 60 + now.second

        # Format the string as per the original ESPHome lambda
        time_string = f"T{seconds_today}"
        data_to_send = time_string.encode('utf-8') # Encode string to bytes

        print(f"Attempting to open serial port: {serial_port} at {baud_rate} baud.")
        # Ensure to set a timeout, even if short, for open and write operations
        # The 'with' statement handles closing the port automatically.
        with serial.Serial(serial_port, baud_rate, timeout=1) as ser:
            print(f"Serial port {ser.name} opened successfully.")
            print(f"Attempting to send: '{time_string}' (bytes: {data_to_send})")
            
            bytes_written = ser.write(data_to_send)
            ser.flush() # Ensure all data is written to the serial port

            print(f"Successfully sent {bytes_written} bytes: '{time_string}' to {serial_port}")
            
            # Optional: Add a small delay if the receiving device needs time
            # time.sleep(0.1) 

    except serial.SerialException as e:
        print(f"Serial port error on '{serial_port}': {e}")
        print("Please check the following:")
        print(f"1. Is a device correctly connected to {serial_port} and powered on?")
        print(f"2. Do you have the necessary permissions to access {serial_port}?")
        print("   (On Linux, you might need to be part of the 'dialout' group or use sudo).")
        print(f"3. Is the baud rate {baud_rate} and other serial parameters (8N1 typically) correct for the receiving device?")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print(f"Script started at: {datetime.datetime.now()}")
    print("Sending current time (seconds since midnight, prefixed with 'T') to serial port...")
    send_time_to_serial()
    print(f"Script finished at: {datetime.datetime.now()}")
