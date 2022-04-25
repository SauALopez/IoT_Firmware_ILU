from pickle import FALSE
import ssl
import paho.mqtt.client as mqtt
import os
import json


class AWSMQTTPubSub():
    #AWS MQTT OBJECT THAT CREATES A MQTT CONECTION TO AWS
    #USING SECURE TLS CONECTION THROUGH KEY AND CERTIFACTION AUTH
    #PROVIDED BY PDIR PATH NAME IN DIRECTORY "/certificates" for root.pem
    #AND "/certificates/thingname/" for client private and cert files
    

    def __init__(self, thingname, logger) -> None:
        self.logger = logger
        self.thingname = thingname
        self.IoT_protocol = "x-amzn-mqtt-ca"
        self.awshost = "a2g73gdmwfmjqk-ats.iot.us-east-1.amazonaws.com"
        self.awsport = 8883
        self.ROOT_PATH = os.getcwd()
        self.logger.info("root path {}".format(self.ROOT_PATH))

    def __ssl_alpn(self):
        #Creating path for certificates
        pathCA = os.path.join(self.ROOT_PATH, "certificates/AmazonRootCA1.pem")
        pathCert = os.path.join(self.ROOT_PATH, "certificates/{}/certificate.pem.crt".format(self.thingname))
        pathKey= os.path.join(self.ROOT_PATH, "certificates/{}/private.pem.key".format(self.thingname))

        #Creating ssl context
        try:
            self.logger.info("Creando SLL para el dispostivo {}".format(self.thingname))
            ssl_context = ssl.create_default_context()
            ssl_context.set_alpn_protocols([self.IoT_protocol])
            ssl_context.load_verify_locations(cafile=pathCA)
            ssl_context.load_cert_chain(certfile=pathCert, keyfile=pathKey)
        except FileNotFoundError as e:
            self.logger.error("Directorio de ThingName no existe dentro de /certificates")
            raise e

        return  ssl_context

    def __on_connect(self, client, userdata, flags, rc):
        self.logger.info("{} conectado correctamente".format(self.thingname))

    def __on_disconnect(self, client, userdata, rc):
        self.logger.info("{} desconectado correctamente".format(self.thingname))


    def __on_message(self, client, userdata, message):
        self.logger.info("{} mensaje recibido".format(self.thingname))

    def __on_publish(self, client, userdata, mid):
        self.logger.info("{} mensaje publicado".format(self.thingname))

    def __on_subscribe(self, client, userdata, mid, granted_qos):
        self.logger.info("{} se ha subscrito".format(self.thingname))

    def __on_unsubscribe(self, client, userdata, mid):
        self.logger.info("{} se ha un-subscrito {}".format(self.thingname, userdata))


    def MQTT_connect(self):
        self.MQTT_CLIENT = mqtt.Client()
        ssl_context = self.__ssl_alpn()
        self.MQTT_CLIENT.tls_set_context(context=ssl_context)

        self.MQTT_CLIENT.on_connect = self.__on_connect
        self.MQTT_CLIENT.on_disconnect = self.__on_disconnect
        self.MQTT_CLIENT.on_message = self.__on_message
        self.MQTT_CLIENT.on_publish = self.__on_publish
        self.MQTT_CLIENT.on_subscribe = self.__on_subscribe
        self.MQTT_CLIENT.on_unsubscribe = self.__on_unsubscribe

        self.MQTT_CLIENT.connect(self.awshost, self.awsport)

        return self.MQTT_CLIENT
    
    def MQTT_start(self):
        payload = json.dumps({'json':True, 'txt':False})
        self.MQTT_CLIENT.publish('{}/dev'.format(self.thingname), payload,0)
        self.MQTT_CLIENT.loop_start()