import requests
import time
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD

# =====================
# CONFIG
# =====================
UPDATE_URL = "http://127.0.0.1:5000/api/update"
LATEST_URL = "http://127.0.0.1:5000/api/latest-data"

GREEN_LED = 17
RED_LED = 27

# =====================
# GPIO SETUP (FIXED)
# =====================
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.cleanup()  # clean previous broken runs

GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

# =====================
# LCD (20x4 I2C)
# =====================
lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    cols=20,
    rows=4
)

lcd.clear()

# =====================
# BLINK STATE
# =====================
blink_state = False

# =====================
# SENSOR PLACEHOLDERS
# REPLACE WITH REAL MLX + SCT LATER
# =====================
def read_mlx_temp():
    """
    Replace with MLX90614 / MLX90640 driver
    """
    return 35.0  # placeholder

def read_sct_current():
    """
    Replace with SCT + ADC (ADS1115 / MCP3008)
    """
    return 2.5  # placeholder


# =====================
# LED CONTROL
# =====================
def update_leds(state, blink):
    if state == "Overheating":
        GPIO.output(GREEN_LED, 0)
        GPIO.output(RED_LED, blink)

    elif state == "Overload":
        GPIO.output(GREEN_LED, 0)
        GPIO.output(RED_LED, 1)

    else:
        GPIO.output(GREEN_LED, 1)
        GPIO.output(RED_LED, 0)


# =====================
# LCD UPDATE (STABLE VERSION)
# =====================
def update_lcd(state, temp, current, mode):
    lcd.cursor_pos = (0, 0)
    lcd.write_string(f"STATE: {state:<12}")

    lcd.cursor_pos = (1, 0)
    lcd.write_string(f"TEMP : {temp:>5.1f} C")

    lcd.cursor_pos = (2, 0)
    lcd.write_string(f"CURR : {current:>5.1f} A")

    lcd.cursor_pos = (3, 0)
    lcd.write_string(f"MODE : {mode:<10}")


# =====================
# MAIN LOOP
# =====================
def run():
    global blink_state

    print("🚀 SYSTEM STARTED (MLX + SCT + ML + LCD)")

    while True:
        try:
            # =====================
            # 1. READ SENSORS
            # =====================
            temp = read_mlx_temp()
            current = read_sct_current()

            # =====================
            # 2. SEND TO FLASK ML ENGINE
            # =====================
            requests.post(
                UPDATE_URL,
                json={
                    "temperature": temp,
                    "current": current
                },
                timeout=3
            )

            # =====================
            # 3. GET PROCESSED RESULT
            # =====================
            response = requests.get(LATEST_URL, timeout=3)
            data = response.json()

            state = data.get("breakerState", "Unknown")
            mode = data.get("ml", {})

            # =====================
            # 4. BLINK LOGIC
            # =====================
            if state == "Overheating":
                blink_state = not blink_state
            else:
                blink_state = False

            # =====================
            # 5. OUTPUT CONTROL
            # =====================
            update_leds(state, blink_state)
            update_lcd(state, temp, current, mode)

            # =====================
            # DEBUG OUTPUT
            # =====================
            print(
                f"T={temp:.1f}°C | "
                f"I={current:.2f}A | "
                f"STATE={state}"
            )

        except Exception as e:
            print("❌ SYSTEM ERROR:", e)

            GPIO.output(GREEN_LED, 0)
            GPIO.output(RED_LED, 0)

            lcd.clear()
            lcd.write_string("SYSTEM ERROR")

        time.sleep(1)


# =====================
# CLEAN EXIT
# =====================
if __name__ == "__main__":
    try:
        run()

    except KeyboardInterrupt:
        print("🛑 Shutting down safely...")
        GPIO.cleanup()
        lcd.clear()