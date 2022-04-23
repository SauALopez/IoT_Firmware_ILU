"""
Example of using the rf24_mesh module to operate the nRF24L01 transceiver as
a Mesh network master node.
"""
import struct
from RF24 import RF24, RF24_PA_MAX, RF24_PA_MIN
from RF24Network import RF24Network
from RF24Mesh import RF24Mesh


# radio setup for RPi B Rev2: CS0=Pin 24
radio = RF24(22, 0)
network = RF24Network(radio)
mesh = RF24Mesh(radio, network)
mesh.setNodeID(0)
if not mesh.begin():
    # if mesh.begin() returns false for a master node,
    # then radio.begin() returned false.
    raise OSError("Radio hardware not responding.")
radio.setPALevel(RF24_PA_MIN)  # Power Amplifier
radio.printDetails()
f = open('data.txt','w')
try:
    while True:
        mesh.update()
        mesh.DHCP()

        while network.available():
            calcsize_text = "llllllll"
            
            header, payload = network.read(struct.calcsize(calcsize_text)) #default to 'L'
            print(f"Received message {header.toString()}")
            if (header.type == 76):#El valor que recibi es de luz
                print(payload)
                print(payload[0], payload[1])
            elif (header.type == 71):#El valor que recibi es de humedad de agua
                print(payload)
                print(payload[0], payload[1])
            elif (header.type == 72):#El valor que recibi es de humedad
                print(payload)
                print(payload[0], payload[1])
            elif(header.type == 84):#El valor que recibi es de temperatura
                print(payload)
                print(payload[0], payload[1])
            else:
                print("Paquete diferente")
            

except KeyboardInterrupt:
    f.close()
    radio.powerDown()  # power radio down before exiting
