#!/usr/bin/env python

import datetime, time

def main():
    name = raw_input("Enter name of controller: ")
    writeFile(name)

def writeFile(name):
    fileName = name + ".csv"    
    outFile = open(fileName,"w")
    i=0
    outFile.write("Line, Controller Name, Date and Time, pH Level, Salinity, Flow Level, Temperature\n")
    while i<6:
        outFile.write(str(i) + "," + name + "," + writeLine())
        time.sleep(600) # for testing purposes, this number is low
        i +=1
    outFile.close()

def writeLine():
    d = datetime.datetime.now()             # for current time
    s = d.strftime("%B %d %Y %I:%M:%S %p")  # converts time to string

#
# This is where we will call the serial path
#
    
    s += ", pH, saline, flow, temp\n" # s += "," + temperatureCall()

#
# The above will be replaced by the serial path call
#
    
    return s

main()

#
#
# NOTE: need to write a function wich stores a few, maybe 10, readings and returns the average.
# That way if there is noise, the readings will not be too inaccurate.
#
#
# http://playground.arduino.cc/interfacing/python has documentation on communicating between
# arduino and python also, it appears that the module for the serial interface is not included
# in python, but is available here http://pyserial.sourceforge.net/
#
#

