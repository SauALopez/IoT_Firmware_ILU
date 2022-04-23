import struct
from RF24 import RF24, RF24_PA_MAX, RF24_PA_MIN
from RF24Network import RF24Network
from RF24Mesh import RF24Mesh

SENSOR_TYPE_HEADERS = ['G', 'H', 'L', 'T']
COMMAND_TYPE_HEADERS = ['A', 'B', 'C', 'D', 'E']
OTHER_TYPE_HEADERS = ['V', 'W', 'X', 'Y', 'Z']

class RadioMaster():

    def __init__(self) -> None:
        pass