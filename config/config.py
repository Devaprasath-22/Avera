# Mode Selection
# True: Runs in offline simulation mode using pre-recorded audio and mock sensors.
# False: Real mode, which interfaces with real sensors and real AI/ASR pipelines.
DEMO_MODE = False

# Audio playback configuration
AUDIO_OUTPUT_DEVICE = "plughw:0,0"

# Sequence of languages cycled through during consecutive start assessments
LANGUAGE_SEQUENCE = ["en", "ta", "hi", "ml", "te"]

# Simulated Sensor Readings (used when DEMO_MODE is True or fallback is active)
TEMPERATURE_DEMO_VALUE = 36.8
SPO2_DEMO_VALUE = 98
PULSE_DEMO_VALUE = 72
ECG_DEMO_HEART_RATE = 72
