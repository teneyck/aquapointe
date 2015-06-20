
/*
Function to take soil content redading  and
return raeding as int called SoilMisture()


To build the circuit
Take baeline reading in water(100%)
And out in air (0%)
Connect two nails and a resistor as shown

digital 2---*
                  |
                  \ R1
                  /
                  |
analog 0----*
                  |
                  *----> nail 1
                  
                  *----> nail 2
                  |
digital 3---*
*/

#define moisture_input A0
#define divider_top 2
#define divider_bottom 3
#define temp_input A1
#define hum_input A2

int SoilMoisture(){
  int moisture;
  // set driver pins to outputs
  pinMode(divider_top,OUTPUT);
  pinMode(divider_bottom,OUTPUT);

  // drive a current through the divider in one direction
  digitalWrite(divider_top,HIGH);
  digitalWrite(divider_bottom,LOW);

  // wait a moment for capacitance effects to settle
  delay(1000);

  // take a moisture reading
  moisture=analogRead(moisture_input);

  // reverse the current
  digitalWrite(divider_top,LOW);
  digitalWrite(divider_bottom,HIGH);

  // give as much time in 'revers'e as in 'forward'
  delay(1000);

  // stop the current
  digitalWrite(divider_bottom,LOW);

  return moisture;

}


/* Takes temperature reading and outputs it as a float in 
degrees farenhiet.

5v----------*
                  |
                  |
                  |
analog 1----*      TMP 36
                  |
                  |
                  |
GND---------*

*/

float temperature()                     
{
 //getting the voltage reading from the temperature sensor
 int reading = analogRead(temp_input);  
 
 // converting that reading to voltage, for 3.3v arduino use 3.3
 float voltage = reading * 5.0;
 voltage /= 1024.0; 
 
 
 // convert volts to temperature converting from 10 mv per degree wit 500 mV offset
 float temperatureC = (voltage - 0.5) * 100 ; 
 
 
 // now convert to Fahrenheit
 float temperatureF = (temperatureC * 9.0 / 5.0) + 32.0;
 
 return temperatureF;
}


/* Takes Humidity reading and outputs it as a float in 
degrees farenhiet.

A2----------*
                  |
                  |
                  |
                   Humidty
                  |
                  |
                  |
GND---------*

*/



float humidity()
{
float humidity = 0;
float prehum = 0;
float humconst = 0;
float truehum = 0;
long val = 0;

// intake humidity value
val = analogRead(hum_input);

//factor for humidity
prehum = (val/5);

//const for humidty
humconst = (0.16/0.0062);

//factory actual humidity
humidity = prehum - humconst;

return humidity;
}



