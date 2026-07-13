# IonityEdge · K10 — standalone learning demos (run individually)
# © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import time

def sensors_demo(k10):
    """Print all onboard sensor values once a second."""
    while True:
        print("temp=%.1f  hum=%d  light=%d  accel=%s" % (
            k10.temperature(), k10.humidity(), k10.ambient_light(), k10.accel()))
        time.sleep(1)

def buttons_demo(k10):
    """React to the A/B buttons."""
    while True:
        if k10.button_a():
            k10.text("A -> Ask / Voice", 6, 100)
        if k10.button_b():
            k10.text("B -> Scan / OCR", 6, 100)
        time.sleep(0.05)

def camera_demo(k10):
    """Grab a frame and hand it to the on-device recognizer (TinyML)."""
    frame = k10.camera_capture()            # TODO: BSP capture
    label = k10.recognize(frame)            # TODO: BSP TinyML model
    k10.text("I see: %s" % label, 6, 140)

def wakeword_demo(k10):
    """Blink the RGB LED when the wake-word is heard."""
    while True:
        if k10.wake_word():                 # TODO: BSP offline keyword
            k10.rgb(0, 210, 255)            # Ionity cyan
            time.sleep(0.4)
            k10.rgb(0, 0, 0)
        time.sleep(0.05)
