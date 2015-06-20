#include <math.h>
/* Three variables to hold values for all analog functions allows for reuse 
*  Count holds the raw reading
*  Voltage holds reading after converted from raw to true
*  SensorReading holds values for all functions in analog functions it seres as Y in
*  standard slope intercept line formula. */
float Count;
float Voltage;
float SensorReading;
/* Analog setup for slope intercept formulas */
float phIntercept = -3.838;
float phSlope = 13.720;
float salIntercept = 0;
float salSlope = 16.3;
float parIntercept = -19.295;
float parSlope = 175.416;
int threshold = 100;  // threshold value to decide when movement detected

void setup() {
  Serial1.begin(9600); //initialize serial communication at 9600 baud

}

void loop() {
  if (Serial1.available() > 0) {
    int inCase = Serial1.read();
/*Takes functions 1-6 to call functions
  1 = pH
  2 = Salinity
  3 = Temperature
  4 = PAR
  5 = Pump Movement
  6 = Test
  */

    switch (inCase) {
      case 49:    
        ph();
        break;
      case 50:    
        sal();
        break;
      case 51:    
        temp();
        break;
      case 52:    
        par();
        break;
      case 53:    
        mvt();
        break;
      case 54:    
        tst();
        break;
    } 
  }
}


void ph(){ // measures ph balance of tank
  Count = analogRead(A0);
  Voltage = Count / 1024 * 5.0;// convert from count to raw voltage
  SensorReading= phIntercept + Voltage * phSlope;
  Serial1.println(SensorReading);
}

void sal(){ // measures salinity of the tank
  Count = analogRead(A1);
  Voltage = Count / 1024 * 5.0;// convert from count to raw voltage
  SensorReading= salIntercept + Voltage * salSlope;
  Serial1.println(SensorReading);
}

void par(){ // Measures light into tank
  Count = analogRead(A2);
  Voltage = Count / 1024 * 5.0;// convert from count to raw voltage
  SensorReading= parIntercept + Voltage * parSlope;
  Serial1.println(SensorReading);
}

void temp(){ // measures temp of system
  Count = analogRead(A3);       // read count from the A/D converter 
  SensorReading = Thermistor(Count);       // and  convert it to CelsiusSerial.print(Time/1000);
  Serial1.println(SensorReading);  
}

float Thermistor(int Raw) //This function calculates temperature from ADC count
{
 /* 
 * This version utilizes the Steinhart-Hart Thermistor Equation:
 *    Temperature in Kelvin = 1 / {A + B[ln(R)] + C[ln(R)]3}
 *   for the themistor in the Vernier TMP-BTA probe:
 *    A =0.00102119 , B = 0.000222468 and C = 1.33342E-7
 *    Using these values should get agreement within 1 degree C to the same probe used with one
 *    of the Vernier interfaces
 * 
 * Schematic:
 *   [Ground] -- [thermistor] -------- | -- [15,000 ohm bridge resistor] --[Vcc (5v)]
 *                                     |
 *                                Analog Pin 1
 *
 For the circuit above:
 * Resistance = ( Count*RawADC /(1024-Count))
 */
 long Resistance; 
 float Resistor = 15000; //brige resistor
// the measured resistance of your particular bridge resistor in
  float Temp;  // Dual-Purpose variable to save space.
  Resistance=( Resistor*Raw /(1024-Raw)); 
  Temp = log(Resistance); // Saving the Log(resistance) so not to calculate  it 4 times later
  Temp = 1 / (0.00102119 + (0.000222468 * Temp) + (0.000000133342 * Temp * Temp * Temp));
  Temp = Temp - 273.15;  // Convert Kelvin to Celsius                      
  return Temp;                                      // Return the Temperature
}

void mvt() { //Measures if pump is working
  // read the sensor and store it in the variable sensorReading:
  SensorReading = analogRead(A4);    
  
  // if the sensor reading is greater than the threshold:
  if (SensorReading >= threshold) {
    // send the string "Knock!" back to the computer, followed by newline
    Serial1.println("True");         
  }
  else {Serial1.println("False");}
  \
  
}

void tst(){
  Serial1.println("working");
}
