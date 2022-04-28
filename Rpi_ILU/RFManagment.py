from email.header import Header
import struct
from RF24 import RF24, RF24_PA_MAX, RF24_PA_MIN
from RF24Network import RF24Network
from RF24Mesh import RF24Mesh

from MQTTManagment import AWSMQTTPubSub

import logging
import sys
from datetime import datetime
import json
# This type headers indicates  
# the type sensor to asignate the value 
# that has the payload
# G --> Ground Humidity sensor, YL-10
# H --> Humidity sensor, AHT10
# L --> Light sensor, *KY-008
# T --> Temperature sensor, AHT10 
# This headers just Publish information from Nodes --> MQTT
SENSOR_TYPE_HEADERS = { 'G' : 'nodo/{}/sensores/humedad_suelo', 
                        'H' : 'nodo/{}/sensores/humedad', 
                        'L' : 'nodo/{}/sensores/luz', 
                        'T' : 'nodo/{}/sensores/temperatura'}


# This type headers are used for 
# actions that involucrate both the 
# master or the nodes devices
# Or any kind of implemetnation for GPIO control en nodes.
# This header dont publish  anything to MQTT.
# Are just used to communicate bethew Master and Nodes
COMMAND_TYPE_HEADERS = {'A',    #Master send to node too activate/deactivate bomb/accionador. 
                                #Base on the limits establish betwen master and control 
                                #MASTER NEEDS TO HANDLE, THIS MESSAGE
                        'B',    #Master Listen to notification from node that are missing packets from humedad de suelo
                        'C',    #Master Listen to notification from node that are missing packets from humedad 
                        'D',    #Master Listen to notification from node that are missing packets from luz
                        'E'}    #Master Listen to notification from node that are missing packets from temperatura


# Control topic for each node liste for future implementations
# Corresponding to control the GPIO pins with control sistems
CONTROL_TOPIC = 'nodo/{}/control'

# Sync topic for each node, to sync conf and control data.
SYNC_TOPIC = 'nodo/{}/web-sync'

# This type of headers, can be used for future 
# Usage, like calibrations, some kind of updaten
# Or any implematation added to the sensors devices.
# This headers are to subscribe by the nodes.
CONF_TYPE_HEADERS = {   'V' : 'nodo/{}/configuracion/velocidad/luz',  ##
                        'W' : 'nodo/{}/configuracion/velocidad/humedad_suelo',
                        'X' : 'nodo/{}/configuracion/velocidad/humedad', 
                        'Y' : 'nodo/{}/configuracion/velocidad/temperatura',
                        'Z' : 'nodo/{}/configuracion/resolucion'}

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
            self.MQTT_CLIENT.publish('master/{}/alertas/critico'.format(self.thingname), "[CRITICO] No se pudo, conectar al modulo NRF24",0)
            self.logger.critical("No se pudo conectar al modulo NRF24")
            raise OSError("Hardware malfunction!!!")

        self.radio.setPALevel(RF24_PA_MAX)
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
        self.nodeid = int(id)
        self.thingname = "Ardu_{}_ILU".format(id)    
        self.mesh = mesh
        self.logger = logger
        
        #Control Limits for sensor variables
        self.resolucion = 2 #por defecto
        self.time_stamps = self._set_timestamp()
        self.sensors_limits = self._defaultlimtis()
        self.control_flag = {"humedad_suelo":False,
                             "humedad":False,
                             "luz":False,
                             "temperatura":False}
        #Create dictionary header for this nodes
        #To assigne each type message with their
        #corresponding topic to MQTT
        self.__header_dictionary()
        self.control_topic = CONTROL_TOPIC.format(self.thingname)
        self.sync_topic = SYNC_TOPIC.format(self.thingname)
        self.notification_topic = "nodo/{}/notificaciones".format(self.thingname)

        AWSMQTTPubSub.__init__(self,self.thingname, self.logger)
        self.MQTT_thing_connect()
        self.MQTT_start()


    def _AWSMQTTPubSub__on_message(self, client, userdata, message):

        # Implementation, to send de configurations send from web controler
        # too the respective node
        if message.topic in self.topic_dict:
            msg_type = self.topic_dict[message.topic]
            msg_payload = int(message.payload.decode('utf-8'))
            if msg_type == 'Z':
                self.resolucion = msg_payload
            else:
                sensor_type = message.topic.split('/')[-1]
                self.time_stamps[sensor_type] = msg_payload
            self.logger.info("Tipo: {} Mensaje: {}. Enviando a: {}".format(msg_type,msg_payload, self.thingname))
            
            data = struct.pack("l", msg_payload)
            self.mesh.write(data, ord(msg_type), self.nodeid)
        else:
        # Implementation, to handle control sistems by configurations from web-control
        # There is just one topic to handle control, it expect json type format from web control
        # Basic implementation, sets the new limit values for the type of sensor
            #check especific topic
            if message.topic == self.control_topic:
                payload = json.loads(message.payload.decode('utf-8'))
                self._new_limits(payload['type'], payload['max_value'], payload['min_value'])
                self.logger.info("Nuevos limites para el sensor '{}' ".format(payload))
                
            elif message.topic == self.sync_topic:
            # Check who send the message "who" in json
            # the only action is to send sync data to this topic    
                payload = json.loads(message.payload.decode('utf-8'))
                if payload['who'] == self.thingname:
                    #Is my info, don't do anything
                    pass
                elif payload['who'] == 'www':
                    msg = {
                        "who" : self.thingname,
                        "resolution" : self.resolucion,
                        "velocity" : self.time_stamps,
                        'limits' : self.sensors_limits,
                        "control_flags" : self.control_flag
                    }
                    payload = json.dumps(msg)
                    self.MQTT_CLIENT.publish(message.topic, payload, 0)
       
    def __header_dictionary(self):
        self.sensors_topics = {}
        for msg_type in SENSOR_TYPE_HEADERS:
            self.sensors_topics[msg_type] = SENSOR_TYPE_HEADERS[msg_type].format(self.thingname)

    def MQTT_thing_connect(self):
        #Call MQTT_connect from AWSMQTT class
        self.MQTT_connect()
        
        #SUBSCRIBE TO CONF HEADER/TOPICS
        self.topic_dict = {}
        for topic_type in CONF_TYPE_HEADERS:
            topic = CONF_TYPE_HEADERS[topic_type].format(self.thingname)
            self.MQTT_CLIENT.subscribe(topic, 0)
            self.topic_dict[topic] = topic_type
            self.logger.info("Subscrito: {}".format(topic))

        #SUBSCRIBE TO CONTROL TOPIC
        self.MQTT_CLIENT.subscribe(self.control_topic, 0)
        #SUBSCRIBE TO SYNC TOPIC
        self.MQTT_CLIENT.subscribe(self.sync_topic, 0)

    def dispatch_msg(self, header, payload):
        topic = self.sensors_topics.get(chr(header.type), None)
        #NOT A SENSOR MESSAGE
        if topic is None:
            self.__conf_msg(header, payload)
        else:
        #IS A SENSOR MESSAGE
            value = round((payload[0] + (payload[1]<<8))/(pow(10,self.resolucion)),self.resolucion)
            msg = { "time": datetime.now().isoformat(timespec='seconds'),
                    "value": value,
                    "name": self.thingname,
                    "type": topic.split('/')[-1],
                    "resolution": self.resolucion }
            msg_out = json.dumps(msg)
            self.logger.info("Message recived: {}, to topic:{}".format(value,topic))
            self.MQTT_CLIENT.publish(topic,msg_out,0)

            ##check control limit
            sensor_type = topic.split('/')[-1]
            self.control_limits(sensor_type, value)
        
    def __conf_msg(self, header, payload):
        if chr(header.type) in COMMAND_TYPE_HEADERS:
            ##Work the comand
            self.alive = datetime.now()
            pass
        else:
            self.logger.info("Mensaje no manejado, no es de ningun tipo")

    def _new_limits(self, type, max, min):
        if self.sensors_limits.get(type):
            self.sensors_limits[type] = [int(max), int(min)]
        else:
            self.logger.warning("No existe sensor")

    def _defaultlimtis(self):
        sensor_limits = {}
        sensor_limits['humedad_suelo'] = [50,25]
        sensor_limits['humedad'] = [70, 40]
        sensor_limits['luz'] = [4000, 10]
        sensor_limits['temperatura'] = [35, 10]

        return sensor_limits
    def _set_timestamp(self):
        timestamp = {}

        timestamp['luz'] = 30
        timestamp['humedad_suelo'] = 30
        timestamp['humedad'] = 30
        timestamp['temperatura'] = 30

        data = struct.pack("l", 30)
        self.mesh.write(data, ord('V') , self.nodeid)
        data = struct.pack("l", 30)
        self.mesh.write(data, ord('W') , self.nodeid)
        data = struct.pack("l", 30)
        self.mesh.write(data, ord('X') , self.nodeid)
        data = struct.pack("l", 30)
        self.mesh.write(data, ord('Y') , self.nodeid)

        return timestamp 
    
    def control_limits(self, sensor_type, value):
        limite_max, limite_min = self.sensors_limits[sensor_type]
        if (limite_min < value < limite_max):
            control = False
            #send notification only once, base on self.control_flag 
            if not self.control_flag[sensor_type] == control:
                self.logger.info("Enviando notificacion de limites buenos para el sensor {} del {}".format(sensor_type, self.thingname))
                self.control_flag[sensor_type] = control    #change control flag
                #We havent send notification on change to control
                msg_payload = json.dumps({
                    "name" : self.thingname,
                    "msg_type" : "notification",
                    "values" : self.control_flag
                })
                self.MQTT_CLIENT.publish(self.notification_topic, msg_payload, 0)  
                #Si es el sensor de humedad, desactivar el actuador
                if sensor_type == 'humedad_suelo':
                    data = struct.pack("l", 1)
                    self.mesh.write(data, ord('F'), self.nodeid)
                    self.sc_flag = True

            
        else:
            control = True   
            #send notification to web and device if need
            if not self.control_flag[sensor_type] == control:
                self.logger.info("Enviando notificacion de limites malos para el sensor {} del {}".format(sensor_type, self.thingname))
                self.control_flag[sensor_type] = control    #change control flag
                #We havent send notification on change to control
                msg_payload = json.dumps({
                    "name" : self.thingname,
                    "msg_type" : "notification",
                    "values" : self.control_flag
                })
                self.MQTT_CLIENT.publish(self.notification_topic, msg_payload, 0) 
                #Si es el sensor de humedad, activar el actuador
                if sensor_type == 'humedad_suelo':
                    data = struct.pack("l", 1)
                    self.mesh.write(data, ord('A'), self.nodeid)
                    self.sc_flag = True
            
        return None

    
        