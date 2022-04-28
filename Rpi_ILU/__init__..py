from RFManagment import RadioMaster

Master = RadioMaster('Rpi_ILU')
Master.MQTT_connect()
Master.MQTT_start()

Master.RF_Start()
Master.RFloop_start()
