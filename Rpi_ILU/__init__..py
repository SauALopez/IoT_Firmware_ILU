from RFManagment import RadioMaster

if __name__ == "__main__":
    Master = RadioMaster('Rpi_ILU')
    Master.MQTT_connect()
    Master.MQTT_start()

    Master.RF_Start()
    Master.RFloop_start()
