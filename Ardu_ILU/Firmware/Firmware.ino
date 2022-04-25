
#include "RF24.h"
#include "RF24Network.h"
#include "RF24Mesh.h"
#include <SPI.h>
#include <CircularBuffer.h>
#include <Adafruit_AHT10.h>

/**** Configuracion de nrf24l01 CE and CS pins ****/
RF24 radio(7, 8);
RF24Network network(radio);
RF24Mesh mesh(radio, network);
#define nodeID 1

/*Creacion de aht, para sensor digital*/
Adafruit_AHT10 aht;


/*Pin definitions for analog sensors */
#define LightSensorPin A1
#define GroudHumiditySensorPin A0

/*  Buffers para guardar informacion de sensores
    cuando estos no logran enviar la informacion
    La aplicacion va vaciar el buffer cada vez que
    se intente enviar la informacion del sensor.
    Se le notificara al master, que los datos de 
    este sensor van a ser historicos, en base a la 
    frecuencia de muestreo del sensor
*/
CircularBuffer<uint16_t, 10> lightbuff;
CircularBuffer<uint16_t, 10> groundbuff;
CircularBuffer<uint16_t, 10> humiditybuff;
CircularBuffer<uint16_t, 10> temperaturebuff;

/*  Variables de control de tiempo para los sensores
    Estas variables son los contadores para crear
    un Timer por software independiente para cada sensor
*/
uint32_t lightTimer = 0;
uint32_t groundTimer = 0;
uint32_t humidityTimer = 0;
uint32_t temperatureTimer = 0;

/*  Variables para velocidad de muestreo de sensores
    #Ejemplo cada 3 segundos -> in millis 3,000
    esta variable recibe unicament valores hasta 255 segundos
    La multiplicacion se hara al momento de la condicional del
    SoftTimer.
*/
uint8_t t_lightlimit = 15;  
uint8_t t_groundlimit = 20;
uint8_t t_humiditylimit = 25;
uint8_t t_temperaturelimit = 30;
/*
  Decimal variable that indicates de number of decimal places
*/
uint8_t decimal = 2;
bool actuador = false;
/*
void lightsensor(void);
void groundsensor(void);
void humiditysensor(void);
void temperaturesensor(void);
void sendmaster(CircularBuffer &buff, char type[1]);
void received_command(void);
*/
void setup()
{
  pinMode(LED_BUILTIN,OUTPUT);

  Serial.begin(115200);
  while (!Serial)
  {
    // some boards need this because of native USB capability
  }
  Serial.println("[INFO] Comunicacion serial inicializada");

  if (!aht.begin())
  {
    Serial.println("[ERROR] SENSOR AHT10, NO ENCOTRADO.");
  }

  // Set the nodeID
  mesh.setNodeID(nodeID);

  // Connect to the mesh
  Serial.println(F("[INFO] Iniciando conexion a la red"));
  if (!mesh.begin())
  {
    Serial.println(F("[ERROR] Comunicacion fallida, porblemas de hardware"));
    while (1)
    {
      // hold in an infinite loop
    }
  }
  Serial.print(F("[INFO] Conectada a la red con ID:"));
  Serial.println(nodeID);
}

void sendmaster(CircularBuffer<uint16_t, 10> &buff, char type[1], char notify[1])
{
  if(buff.size() > 1){
    //Sensor fault to send in the past
    //Send to master notification containing 
    //Missing packages to handle future paquets send
    Serial.println("[WARNING] Hay mensajes en cola");
    uint16_t buff_size = buff.size();
    if (!mesh.write(&buff_size, notify, sizeof(buff_size)))
      {
        // If a write fails, check connectivity to the mesh network
        if (!mesh.checkConnection())
        {
          // refresh the network address
          Serial.println("[INFO] Renovando direccion");
          if (!mesh.renewAddress())
          {
            // If address renewal fails, reconfigure the radio and restart the mesh
            // This allows recovery from most if not all radio errors
            mesh.begin();
          }
        }
        else
        {
          Serial.println("[ERROR] ALERTA FALLIDA");
        }
      }
      else
      {
        Serial.println("[INFO] ALERTA ENVIADA");
        Serial.println("[INFO] ENVIO DE PAQUETES ATRASADOS");
        while(!buff.isEmpty())
        {
          uint16_t value = buff.pop();
          if (!mesh.write(&value, type, sizeof(value)))
          {

            // If a write fails, check connectivity to the mesh network
            if (!mesh.checkConnection())
            {
              // refresh the network address
              Serial.println("[INFO] Renovando direccion");
              if (!mesh.renewAddress())
              {
                // If address renewal fails, reconfigure the radio and restart the mesh
                // This allows recovery from most if not all radio errors
                mesh.begin();
              }
              buff.push(value);
              break;
            }
            else
            {
              Serial.println("[ERROR] ENVIOFALLIDO, VALOR GUARDADO");
              buff.push(value);
              break;
            }
          }
          else
          {
            Serial.println("[INFO] Envio correcto");    
          }
        }
      }
  }else{
    //asign to value the last, unique value in buffer
    uint16_t value = buff.pop();
    if (!mesh.write(&value, type, sizeof(value)))
    {

      // If a write fails, check connectivity to the mesh network
      if (!mesh.checkConnection())
      {
        // refresh the network address
        Serial.println("[INFO] Renovando direccion, VALOR GUARDADO");
        if (!mesh.renewAddress())
        {
          // If address renewal fails, reconfigure the radio and restart the mesh
          // This allows recovery from most if not all radio errors
          mesh.begin();
        }
        buff.push(value);
      }
      else
      {
        Serial.println("[ERROR] ENVIOFALLIDO, VALOR GUARDADO");
        buff.push(value);
      }
    }
    else
    {
      Serial.println("[INFO] Envio correcto");    
    }
  }  
}

void received_command(void)
{
  while(network.available())
  {
    RF24NetworkHeader header;
    uint8_t payload;
    network.read(header, &payload, sizeof(payload));
    switch (header.type)
    {
    case 'V':
      t_lightlimit = payload;
      break;
    case 'W':
      t_groundlimit = payload;
      break;
    case 'X':
      t_humiditylimit = payload;
      break;
    case 'Y':
      t_temperaturelimit = payload;
    case 'Z':
      decimal = int(payload);
    case 'A':
      actuador = true;
    default:
      break;
    }
  }
}

void lightsensor()
{
  //Make sensor calculations
  Serial.println("[INFO] TIMER - LIGHT");
  uint16_t analogico = analogRead(LightSensorPin);
  float lm = 22224685.9421 * (pow(analogico,-2.2713));
  lm = lm * pow(10,decimal);
  uint16_t value = (uint16_t) lm;
  lightbuff.push(value);
  sendmaster(lightbuff, 'L', 'D');
}

void groundsensor()
{
  //Make sensor calculations
  Serial.println("[INFO] TIMER - GROUND");
  uint16_t analogico = analogRead(GroudHumiditySensorPin);
  float hr =  (0.0001468 * pow(analogico,2)) - (0.2508 * analogico) + (105.3);
  hr = hr * pow(10,decimal);
  uint16_t value = (uint16_t) hr;
  groundbuff.push(value);
  sendmaster(groundbuff, 'G', 'B');
}

void humiditysensor()
{
  //Make sensor calculations
  Serial.println("[INFO] TIMER - HUMEDAD");
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);
  float temp_humidity = humidity.relative_humidity * pow(10,decimal);
  uint16_t value = (uint16_t) temp_humidity;
  humiditybuff.push(value);
  sendmaster(humiditybuff, 'H', 'C');
}

void temperaturesensor()
{
  //Make sensor calculations
  Serial.println("[INFO] TIMER - TEMP");
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);
  float temp_temp = temp.temperature * pow(10,decimal);
  uint16_t value = (uint16_t) temp_temp;
  temperaturebuff.push(value);
  sendmaster(temperaturebuff,'T', 'E');
}


void loop()
{
  

  mesh.update(); // check for updated address
  received_command(); //check is there ir a msg and procces it
  
  if(actuador)
  {
    digitalWrite(LED_BUILTIN, HIGH);
  }
  else
  {
    digitalWrite(LED_BUILTIN, LOW);
  }

  /*
    SoftTimer for Light sensor
  */
  if(millis() - lightTimer >= (t_lightlimit*1000)){
    lightTimer = millis();
    lightsensor();
  }

  /*
    SoftTimer for Ground Humidity sensor
  */
  if(millis() - groundTimer >= (t_groundlimit*1000)){
    groundTimer = millis();
    groundsensor();
    
  }

  /*
    SoftTimer for Humidity sensor
  */
  if(millis() - humidityTimer >= (t_humiditylimit*1000)){
    humidityTimer = millis();
    humiditysensor();
  }

  /*
    SoftTimer for Temperature sensor
  */
  if(millis() - temperatureTimer >= (t_temperaturelimit*1000)){
    temperatureTimer = millis();
    temperaturesensor();  
  }

}

