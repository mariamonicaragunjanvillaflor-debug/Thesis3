import requests
import time
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD

# =====================
# CONFIG
# =====================

FLASK_URL = "http://127.0.0.1:5000/api/latest-data"

GREEN_LED = 17
RED_LED = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

# =====================
# LCD (I2C 20x4)
# =====================

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    port=1,
    cols=20,
    rows=4
)

lcd.clear()

# =====================
# STATE MEMORY
# =====================

last_state = None
blink_state = False


# =====================
# SAFE HELPERS
# =====================

def reset_leds():
    GPIO.output(GREEN_LED, 0)
    GPIO.output(RED_LED, 0)


def safe_write(row, text):
    """
    Prevent leftover characters on LCD
    """
    lcd.cursor_pos = (row, 0)
    lcd.write_string(f"{text:<20}"[:20])


# =====================
# LED CONTROL
# =====================

def update_leds(state, blink_state):
    reset_leds()

    if state == "Normal":
        GPIO.output(GREEN_LED, 1)

    elif state == "Overload":
        GPIO.output(RED_LED, 1)

    elif state == "Critical Overload":
        GPIO.output(RED_LED, blink_state)

    else:
        GPIO.output(RED_LED, 1)


# =====================
# LCD DISPLAY
# =====================

def update_lcd(data):
    global last_state

    current = data.get("current", 0)
    state = data.get("breakerState", "Unknown")

    ml = data.get("ml", {})
    ovl_prob = ml.get("overload_prob", 0) * 100

    # Clear only when state changes
    if state != last_state:
        lcd.clear()
        last_state = state

    # Row 1
    safe_write(
        0,
        f"Current:{current:5.1f}A"
    )

    # Row 2
    safe_write(
        1,
        f"State:{state}"
    )

    # Row 3
    safe_write(
        2,
        f"Overload:{ovl_prob:3.0f}%"
    )

    # Row 4
    if state == "Normal":
        safe_write(3, "System Stable")

    elif state == "Overload":
        safe_write(3, "High Current")

    elif state == "Critical Overload":
        safe_write(3, "CHECK LOAD NOW!")

    else:
        safe_write(3, "System Error")


# =====================
# MAIN LOOP
# =====================

def run():
    global blink_state

    print("🚀 Overload Monitoring Running")

    while True:
        try:
            response = requests.get(FLASK_URL, timeout=5)
            data = response.json()

            state = data.get("breakerState", "Unknown")

            # Blink only for critical overload
            if state == "Critical Overload":
                blink_state = not blink_state
            else:
                blink_state = False

            update_leds(state, blink_state)
            update_lcd(data)

            # Debug Print
            ml = data.get("ml", {})

            print(
                f"I={data.get('current',0):.1f}A | "
                f"O={ml.get('overload_prob',0):.2f} | "
                f"{state}"
            )

        except Exception as e:
            print("❌ ERROR:", e)

            reset_leds()
            lcd.clear()

            safe_write(0, "FLASK OFFLINE")
            safe_write(1, "CHECK SERVER")

        time.sleep(0.7)


# =====================
# CLEAN EXIT
# =====================

if __name__ == "__main__":
    try:
        run()

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        GPIO.cleanup()
        lcd.clear()