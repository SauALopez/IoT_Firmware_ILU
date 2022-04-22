#include "RF24.h"
#include "RF24Network.h"
#include <RF24Mesh.h>
#include <SPI.h>

#include "config.h"

/*Asignar pines para NRF24*/
RF24 radio(NRF24L01_CE, NRF24L01_CS);
RF24Network network(radio);
RF24Mesh mesh(radio, network);

uint32_t millisTimer = 0;


void setup(){
    Serial.begin(115200);
    while(!Serial){

    }
    Serial.println("Iniciando configuracion...");


    mesh.setNodeID(NodeID);
    Serial.println("Conectdando a la red de sensores");
    
    if (!mesh.begin()){
        Serial.println("Modulo NRF24L01, no esta respondiendo...");
        Serial.println("[ERROR] Termina configuracion sin exito.");
        while(1){}
    }
}

void loop(){
    if (network.available()) {
    RF24NetworkHeader header;
    uint32_t mills;
    network.read(header, &mills, sizeof(mills));
    Serial.print("Rcv "); Serial.print(mills);
    Serial.print(" from nodeID ");
    int _ID = mesh.getNodeID(header.from_node);
    if ( _ID > 0) {
      Serial.println(_ID);
    } else {
      Serial.println("Mesh ID Lookup Failed");
    }
  }


  // Send to the other node every second
  if (millis() - millisTimer >= 1000) {
    millisTimer = millis();

    // Send an 'M' type to other Node containing the current millis()
    if (!mesh.write(&millisTimer, 'M', sizeof(millisTimer), otherNodeID)) {
      if ( ! mesh.checkConnection() ) {
        Serial.println("Renewing Address");
        mesh.renewAddress();
      } else {
        Serial.println("Send fail, Test OK");
      }
    }
  }

}

