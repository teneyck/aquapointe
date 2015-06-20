

#define temp_input A1

void setup() {

}  
  
 void loop() { 
 float tempF;
 tempF = temperature(); 
 Serial.print(tempF);
 Serial.print("\n"); 
}

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
