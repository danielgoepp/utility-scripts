#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
import sys
from config import MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_CLIENT_ID

def on_message(client, userdata, msg):
    print("Message received on topic {0}: {1}".format(msg.topic, msg.payload))

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print(f"Failed to connect to MQTT broker with result code {rc}")
        sys.exit(1)

def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT broker")

if not all([MQTT_HOST, MQTT_USERNAME, MQTT_PASSWORD]):
    print("Error: Missing required MQTT configuration. Please check your .env file.")
    sys.exit(1)

client = mqtt.Client(client_id=MQTT_CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.connect(MQTT_HOST, MQTT_PORT)

# client.loop_start()

client.subscribe("#")
client.on_message=on_message 

# time.sleep(30)
# client.loop_stop()
client.loop_forever()

