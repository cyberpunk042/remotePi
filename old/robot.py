from time import sleep
import keyboard
import sys
import socket
import time
import RPi.GPIO as GPIO

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = ('0.0.0.0', 10000)
print >>sys.stderr, 'starting up on %s port %s' % server_address
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

#Choice of PINS
leftSideDisable=3
leftSideForward=11
rightSideDisable=5
rightSideForward=13

#Disable warnings
GPIO.setwarnings(False)

frequence=20 #in hz

#PWM dc_speeds
dc_stop = 100
dc_speed1 = 40
dc_speed2 = 35
dc_speed3 = 30
dc_speed4 = 25
dc_speed5 = 15
dc_speed7 = 5

#Configure GPIO
GPIO.setmode(GPIO.BOARD)

GPIO.setup(leftSideDisable, GPIO.OUT)
leftSide = GPIO.PWM(leftSideDisable, frequence)
GPIO.setup(leftSideForward, GPIO.OUT)

GPIO.setup(rightSideDisable, GPIO.OUT)
rightSide = GPIO.PWM(rightSideDisable, frequence)
GPIO.setup(rightSideForward, GPIO.OUT)

#Initial state
rightSide.start(dc_stop)
GPIO.output(leftSideForward , 0)
leftSide.start(dc_stop)
GPIO.output(rightSideForward, 0)

def set_speed_left(power):
    print >>sys.stderr, 'power left', power
    if power == "9":
       leftSide.stop()
    if power == "7":
       leftSide.start(dc_speed7)
    if power == "5":
       leftSide.start(dc_speed5)
    if power == "4":
       leftSide.start(dc_speed4)
    if power == "3":
       leftSide.start(dc_speed3)
    if power == "2":
       leftSide.start(dc_speed2)
    if power == "1":
       leftSide.start(dc_speed1)

def set_speed_right(power):
    print >>sys.stderr, 'power right', power
    if power == "9":
       rightSide.stop()
    if power == "7":
       rightSide.start(dc_speed7)
    if power == "5":
       rightSide.start(dc_speed5)
    if power == "4":
       rightSide.start(dc_speed4)
    if power == "3":
       rightSide.start(dc_speed3)
    if power == "2":
       rightSide.start(dc_speed2)
    if power == "1":
       rightSide.start(dc_speed1)

def left_side_forward(power):
    print >>sys.stderr, 'left_side_forward'
    set_speed_left(power)
    GPIO.output(leftSideForward, 1)

def right_side_forward(power):
    print >>sys.stderr, 'right_side_forward'
    set_speed_right(power)
    GPIO.output(rightSideForward, 1)

def left_side_backward(power):
    print >>sys.stderr, 'left_side_backward'
    set_speed_left(power)
    GPIO.output(leftSideForward, 0)

def right_side_backward(power):
    print >>sys.stderr, 'right_side_backward'
    set_speed_right(power)
    GPIO.output(rightSideForward, 0)

def stopLeft():
    print >>sys.stderr, 'stopLeft'
    leftSide.start(dc_stop)
    GPIO.output(leftSideForward , 0)

def stopRight():
    print >>sys.stderr, 'stopRight'
    rightSide.start(dc_stop)
    GPIO.output(rightSideForward, 0)

data=""


timeToQuit = 0

while not timeToQuit:
    if keyboard.is_pressed('q'):
        timeToQuit = 1
    print >>sys.stderr, 'waiting for a connection'
    connection, client_address = sock.accept()
    print >>sys.stderr, 'connection from', client_address

    while not timeToQuit:
       try:
         if keyboard.is_pressed('q'):
             timeToQuit = 1
         data = connection.recv(2)
     	 print >>sys.stderr, data

         if (len(data) == 1):
            data = data + connection.recv(1)
         elif (len(data) == 2 and data[0] == "S"):
            if (data[1] == "L"):
               stopLeft()
#               connection.send(data)
            elif (data[1] == "R"):
               stopRight()
#               connection.send(data)
         elif (len(data) == 2):
            data = data + connection.recv(1)

         if (len(data) == 3):
            if (data[0] == "L" and data[1] == "F"):
               left_side_forward(data[2])
#               connection.send(data)
            elif (data[0] == "L" and data[1] == "B"):
               left_side_backward(data[2])
#               connection.send(data)
            elif (data[0] == "R" and data[1] == "F"):
               right_side_forward(data[2])
#               connection.send(data)
            elif (data[0] == "R" and data[1] == "B"):
               right_side_backward(data[2])
#               connection.send(data)

         sleep(0.05)

       except KeyboardInterrupt:
         print >>sys.stderr, 'interrupt received, stopping'
         timeToQuit = 1


    connection.close()

GPIO.cleanup()
sock.shutdown(socket.SHUT_RDWR)

