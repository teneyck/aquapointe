

#define temp_input A1
#define light 13
long linuxBaud = 250000;
boolean commandMode = false;

void setup() {
  Serial.begin(115200);
  pinMode(temp_input, INPUT);
  pinMode(light, OUTPUT);
  Serial1.begin(linuxBaud);
}  
  
void loop() { 
  float tempF;
  tempF = temperature();
  Serial.print(tempF);
  Serial.print("\n");
  digitalWrite(light, HIGH);
  delay(1000); 
  digitalWrite(light, LOW);
  delay(1000); 
    if (Serial.available()) {           // got anything from USB-Serial?
    char c = (char)Serial.read();     // read from USB-serial
    if (commandMode == false) {       // if we aren't in command mode...
      if (c == '~') {                 //    Tilde '~' key pressed?
        commandMode = true;           //       enter in command mode
      } else {
        Serial1.write(c);             //    otherwise write char to Linux
      }
    } else {                          // if we are in command mode...
      if (c == '0') {                 //     '0' key pressed?
        Serial1.begin(57600);         //        set speed to 57600
        Serial.println("Speed set to 57600");
      } else if (c == '1') {          //     '1' key pressed?
        Serial1.begin(115200);        //        set speed to 115200
        Serial.println("Speed set to 115200");
      } else if (c == '2') {          //     '2' key pressed?
        Serial1.begin(250000);        //        set speed to 250000
        Serial.println("Speed set to 250000");
      } else if (c == '3') {          //     '3' key pressed?
        Serial1.begin(500000);        //        set speed to 500000
        Serial.println("Speed set to 500000");
      } else if (c == '~') {
        Serial1.write((uint8_t *)"\xff\0\0\x05XXXXX\x0d\xaf", 11);
        Serial.println("Sending bridge's shutdown command");
      } else {                        //     any other key pressed?
        Serial1.write('~');           //        write '~' to Linux
        Serial1.write(c);             //        write char to Linux
      }
      commandMode = false;            //     in all cases exit from command mode
    }
  }
  if (Serial1.available()) {          // got anything from Linux?         
    char c = (char)Serial1.read();    // read from Linux  
    Serial.write(c);                  // write to USB-serial
  }
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
