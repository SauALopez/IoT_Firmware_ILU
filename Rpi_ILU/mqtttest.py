import ssl
import paho.mqtt.client as mqtt

import sys

import logging


IoT_protocol_name = "x-amzn-mqtt-ca"
awshost = "a2g73gdmwfmjqk-ats.iot.us-east-1.amazonaws.com"
awsport = 8883

ca = "./certificates/AmazonRootCA1.pem" # Root certificate authority, comes from AWS with a long, long name
cert = "./certificates/Ardu_1_ILU/5676-certificate.pem.crt"
private = "./certificates/Ardu_1_ILU/5676-private.pem.key"

MQTT_TOPIC = "test/dev"

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
log_format = logging.Formatter('%(asctime)s - %(name)s [ %(levelname)s ] - %(message)s')
handler.setFormatter(log_format)
logger.addHandler(handler)

def ssl_alpn():
    try:
        #debug print opnessl version
        ssl_context = ssl.create_default_context()
        ssl_context.set_alpn_protocols([IoT_protocol_name])
        ssl_context.load_verify_locations(cafile=ca)
        ssl_context.load_cert_chain(certfile=cert, keyfile=private)

        return  ssl_context
    except Exception as e:
        print("exception ssl_alpn()")
        raise e

def on_message(client, userdata, msg):
        print("Topic: " + str(msg.topic))
        print("QoS: " + str(msg.qos))
        print("Payload: " + str(msg.payload)
)
def on_connect(mosq, obj, flags, rc):
        print ("Connected!")
        MQTT_client.subscribe(MQTT_TOPIC, 1)

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed to Topic: " +
        MQTT_TOPIC + " with QoS: " + str(granted_qos))



MQTT_client = mqtt.Client()


MQTT_client.enable_logger()

ssl_context = ssl_alpn()

MQTT_client.tls_set_context(context=ssl_context)

MQTT_client.on_message = on_message
MQTT_client.on_connect = on_connect
MQTT_client.on_subscribe = on_subscribe


MQTT_client.connect(host= awshost, port=awsport,keepalive=120)

if MQTT_client.is_connected:
    MQTT_client.publish('test/dev','Hola texto mio',1)
    print("mensaje enviado")

MQTT_client.loop_forever()



