import struct
from RF24 import RF24, RF24_PA_MAX, RF24_PA_MIN
from RF24Network import RF24Network
from RF24Mesh import RF24Mesh

from MQTTManagment import AWSMQTTPubSub

import logging
import sys
from datetime import datetime
# This type headers indicates  
# the type sensor to asignate the value 
# that has the payload
# G --> Ground Humidity sensor, YL-10
# H --> Humidity sensor, AHT10
# L --> Light sensor, *KY-008
# T --> Temperature sensor, AHT10 
# This headers just Publish information from Nodes --> MQTT
SENSOR_TYPE_HEADERS = { 'G' : 'nodos/{}/sensores/humedad_suelo', 
                        'H' : 'nodos/{}/sensores/humedad', 
                        'L' : 'nodos/{}/sensores/luz', 
                        'T' : 'nodos/{}/sensores/temperatura'}


# This type headers are used for 
# actions that involucrate both the 
# master or the nodes devices
# Or any kind of implemetnation for GPIO control en nodes.
# This header dont publish  anything to MQTT.
# Are just used to communicate bethew Master and Nodes
COMMAND_TYPE_HEADERS = ['A', 'B', 'C', 'D', 'E']


# This type of headers, can be used for future 
# Usage, like calibrations, some kind of update
# Or any implematation added to the sensors devices.
# This headers are to subscribe by the nodes.
CONF_TYPE_HEADERS = {   'V' : 'nodos/{}/configuracion/velocidad/humedad_suelo',  ##
                        'W' : 'nodos/{}/configuracion/velocidad/humedad',
                        'X' : 'nodos/{}/configuracion/velocidad/humedad', 
                        'Y' : 'nodos/{}/configuracion/velocidad/temperatura',
                        'Z' : 'nodos/{}/configuracion/resolucion'}

####################################################
# Class base for make object oriented functionality
# to the master logic to route all the comming trafic from 
# nodes to their corresponding channel/topic
# to the MQTT Broker
class RadioMaster(AWSMQTTPubSub):

    def __init__(self, thingname):

        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        log_format = logging.Formatter('[%(asctime)s] - [ %(levelname)s ] - %(message)s')
        handler.setFormatter(log_format)
        self.logger.addHandler(handler) 

        AWSMQTTPubSub.__init__(self,thingname=thingname,logger=self.logger)

        self.logger.info("Iniciando configuracion de RF24 Network & Mesh")
        self.radio = RF24(22, 0)    #Radio CE Y CSN PINS in RP
        #Create radio instance.
        self.network = RF24Network(self.radio)
        self.mesh = RF24Mesh(self.radio, self.network)
        self.mesh.setNodeID(0)
        self.logger.info("Configracion de RF24, terminada.")

        self.nodes = {}

    def RF_Start(self):
        self.logger.info("Iniciando red, Nodo 0 (Master)")
        
        if not self.mesh.begin():
            self.MQTT_CLIENT.publish('{}/alertas/critico'.format(self.thingname), "[CRITICO] No se pudo, conectar al modulo NRF24",0)
            self.logger.critical("No se pudo conectar al modulo NRF24")
            raise OSError("Hardware malfunction!!!")

        self.radio.setPALevel(RF24_PA_MIN)
        self.radio.printDetails

    def RFloop_start(self):
        self.logger.info("Iniciando Loop infinito") 
        
        calcsize_value = "llllllll"
        self.buff_size = len(calcsize_value)*4
        self.logger.info("Iniciando recepcion de datos Tamanio de buffer: {}".format(len(calcsize_value)*4))
        while(1):
            self.mesh.update()
            self.mesh.DHCP()


            while self.network.available():
                header, payload = self.network.read(struct.calcsize(calcsize_value))
                self.__to_nodes(header, payload)


    def __to_nodes(self, header, payload):
        node = self.__check_nodes(self.mesh.getNodeID(header.from_node))
        node.dispatch_msg(header, payload)

    def __check_nodes(self, id):
        #check if the node has already connect to this master
        if id in self.nodes:
            #node already exist, return node class
            return self.nodes[id]
            
        else:
            #node dont exist, create node
            self.nodes[id] = RFNode(id, self.mesh, self.logger)
            return self.nodes[id]


class RFNode(AWSMQTTPubSub):
    
    def __init__(self, id, mesh, logger):

        self.thingname = "Ardu_{}_ILU".format(id)    
        self.mesh = mesh
        self.logger = logger

        AWSMQTTPubSub.__init__(self,self.thingname, self.logger)
        self.MQTT_thing_connect()
        self.MQTT_start()
        #Create dictionary header for this nodes
        #To assigne each type message with their
        #corresponding topic to MQTT
        self.__header_dictionary()

    def __header_dictionary(self):
        self.sensors_topics = {}
        for msg_type in SENSOR_TYPE_HEADERS:
            self.sensors_topics[msg_type] = SENSOR_TYPE_HEADERS[msg_type].format(self.thingname)

    def MQTT_thing_connect(self):
        #Call MQTT_connect from AWSMQTT class
        self.MQTT_connect()
        #SUBSCRIBE TO CONF HEADER/TOPICS
        for topic_type in CONF_TYPE_HEADERS:
            topic = CONF_TYPE_HEADERS[topic_type].format(self.thingname)
            self.MQTT_CLIENT.subscribe(topic, 0)

    def dispatch_msg(self, header, payload):
        topic = self.sensors_topics.get(chr(header.type), None)
        #NOT A SENSOR MESSAGE
        if topic is None:
            self.__comand_msg(header, payload)
        else:
        #IS A SENSOR MESSAGE
            value = payload[0] + (payload[1]<<8)/100
            self.logger.info("Payload {}".format(value))
            self.MQTT_CLIENT.publish(topic,str(value),0)
        
    def __comand_msg(self, header, payload):
        if chr(header.type) in COMMAND_TYPE_HEADERS:
            ##Work the comand
            self.alive = datetime.now()
            pass
        else:
            self.logger.info("Mensaje no manejado, no es de ningun tipo")