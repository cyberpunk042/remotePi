import asyncio
import sys
import socket
import time
import RPi.GPIO as GPIO
import remotePiClasses.directionClass as DirectionSystem
import remotePiClasses.distanceCaptorClass as DistanceCaptor
import remotePiClasses.configClass as Config
import socket
import fcntl, os
import logging
import remotePiClasses.colorModuleClass as ColorModule
logging.basicConfig(level=logging.INFO)

# Create a TCP/IP socket
SYSTEMD_FIRST_SOCKET_FD = 1
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#sock = socket.fromfd(SYSTEMD_FIRST_SOCKET_FD, socket.AF_INET, socket.SOCK_STREAM)

# Reusable socket
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Non blocking socket
#fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)
sock.setblocking(0)


# Bind the socket to the port
server_address = ('0.0.0.0', 10000)
logging.info('starting up on (%s,%s)', server_address[0], server_address[1])
sock.bind(server_address)

# Listen for incoming connections
sock.listen(SYSTEMD_FIRST_SOCKET_FD)


#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BOARD)

RESET_TRIGGER_PIN=40
GPIO.setup(RESET_TRIGGER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
 
#Disable warnings
GPIO.setwarnings(False)


async def thread_socket_server(sharedProperties):
    while not sharedProperties.endOfProgram:        
        if sharedProperties.connection is None:
            logging.info('waiting for a connection')
            try:
                sharedProperties.connection, client_address = sock.accept()
                logging.info('connection from: %s', client_address)
                sharedProperties.connection.setblocking(0)
                ColorModule.turnOnBlueLed()

            except IOError as e:  # and here it is handeled
                pass    
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(1)
    
    if sharedProperties.connection is not None:
        sharedProperties.connection.close()
        ColorModule.turnOffBlueLed()
        logging.info("Closed connection")

    GPIO.cleanup()
    logging.info("GPIO cleanup")
    sock.shutdown(socket.SHUT_RDWR)
    logging.info("Disconnected socket")

async def thread_direction_controller(sharedProperties):
    data=""
    while not sharedProperties.endOfProgram:
        await asyncio.sleep(0.01)
        if sharedProperties.connection is not None:
            try:  
                # In case someone blocked the way temporary we have to be able to detect there is no longer obstuction and keep going forward
                if sharedProperties.forceStopForward == 0 and (DirectionSystem.lastSavedDirectionLeftSide == 'forward' or  DirectionSystem.lastSavedDirectionRightSide == 'forward'):
                    DirectionSystem.restoreDirection()
                    if Config.DEBUG_ENABLED:
                        logging.info('Restored direction - Current save direction : (L:%s,R:%s)', DirectionSystem.lastSavedDirectionLeftSide, DirectionSystem.lastSavedDirectionRightSide)
                if sharedProperties.forceStopBackward == 0 and (DirectionSystem.lastSavedDirectionLeftSide == 'backward' or  DirectionSystem.lastSavedDirectionRightSide == 'backward'):
                    DirectionSystem.restoreDirection()
                    if Config.DEBUG_ENABLED:
                        logging.info('Restored direction - Current save direction : (L:%s,R:%s)', DirectionSystem.lastSavedDirectionLeftSide, DirectionSystem.lastSavedDirectionRightSide)
                        
                # In the eventuality that there is a fontral poximity alert
                if sharedProperties.forceStopForward == 1 and (DirectionSystem.currentDirectionLeftSide == 'forward' or  DirectionSystem.currentDirectionRightSide == 'forward'):
                    DirectionSystem.saveDirection()
                    DirectionSystem.stopLeft()
                    DirectionSystem.stopRight()
                    if Config.DEBUG_ENABLED:
                        logging.info('Saved direction: (L:%s,R:%s)', DirectionSystem.currentDirectionLeftSide, DirectionSystem.currentDirectionRightSide)

                # In the eventuality that there is a dorsal poximity alert
                if sharedProperties.forceStopBackward == 1 and (DirectionSystem.currentDirectionLeftSide == 'backward' or  DirectionSystem.currentDirectionRightSide == 'backward'):
                    DirectionSystem.saveDirection()
                    DirectionSystem.stopLeft()
                    DirectionSystem.stopRight()
                    if Config.DEBUG_ENABLED:
                        logging.info('Saved direction: (L:%s,R:%s)', DirectionSystem.currentDirectionLeftSide, DirectionSystem.currentDirectionRightSide)
                    

                data = sharedProperties.connection.recv(2048).decode('utf-8') # 2048 or 4096 ?
                if Config.DEBUG_ENABLED:
                    logging.info('data: %s', data)

                # End of connection from client
                if not data:
                    sharedProperties.connection.close()
                    sharedProperties.connection = None
                    ColorModule.turnOffBlueLed() # Turn off connection led
                else:
                    # One joystick at a time
                    if (len(data) == 2 and data[0] == "S"):
                        if (data[1] == "L"):
                            DirectionSystem.stopLeft()
                            if DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                DirectionSystem.lastSavedDirectionLeftSide = 'none'
                        elif (data[1] == "R"):
                            DirectionSystem.stopRight()
                            if DirectionSystem.lastSavedDirectionRightSide != 'none':
                                DirectionSystem.lastSavedDirectionRightSide = 'none'
                    # Two joystick at a time
                    elif(len(data) == 4 and data[0] == "S" and data[2] == "S"):
                        if (data[1] == "L"):
                            DirectionSystem.stopLeft()
                            if DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                DirectionSystem.lastSavedDirectionLeftSide = 'none'
                        if (data[1] == "R"):
                            DirectionSystem.stopRight()
                            if DirectionSystem.lastSavedDirectionRightSide != 'none':
                                DirectionSystem.lastSavedDirectionRightSide = 'none'
                        if (data[3] == "L"):
                            DirectionSystem.stopLeft()
                            if DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                DirectionSystem.lastSavedDirectionLeftSide = 'none'
                        if (data[3] == "R"):
                            DirectionSystem.stopRight()
                            if DirectionSystem.lastSavedDirectionRightSide != 'none':
                                DirectionSystem.lastSavedDirectionRightSide = 'none'
                    else:
                        # It is not a stop command, this mean it is a forward/backward command

                        # Data length indicate that it is one joystick at a time
                        if (len(data) == 3):
                            if (data[0] == "L" and data[1] == "F"):
                                if sharedProperties.forceStopForward != 1:
                                    DirectionSystem.left_side_forward(data[2])
                                elif DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                    DirectionSystem.lastSavedDirectionLeftSide = 'forward'
                                    DirectionSystem.stopLeft()
                                else:
                                    # Make sure it still record the ordered direction
                                    DirectionSystem.currentDirectionLeftSide = 'forward' 

                            elif (data[0] == "L" and data[1] == "B"):
                                if sharedProperties.forceStopBackward != 1:
                                    DirectionSystem.left_side_backward(data[2])
                                elif DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                    DirectionSystem.lastSavedDirectionLeftSide = 'backward'
                                    DirectionSystem.stopLeft()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionLeftSide = 'backward' 

                            elif (data[0] == "R" and data[1] == "F"):
                                if sharedProperties.forceStopForward != 1:
                                    DirectionSystem.right_side_forward(data[2])
                                elif DirectionSystem.lastSavedDirectionRightSide != 'none':
                                    DirectionSystem.lastSavedDirectionRightSide = 'forward'
                                    DirectionSystem.stopRight()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionRightSide = 'forward' 

                            elif (data[0] == "R" and data[1] == "B"):
                                if sharedProperties.forceStopBackward != 1:
                                    DirectionSystem.right_side_backward(data[2])
                                elif DirectionSystem.lastSavedDirectionRightSide != 'none':
                                    DirectionSystem.lastSavedDirectionRightSide = 'backward'
                                    DirectionSystem.stopRight()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionRightSide = 'backward' 
                                
                        # Data length indicate that it is two joystick at a time
                        if (len(data) == 6):
                            if (data[0] == "L" and data[1] == "F"):
                                if sharedProperties.forceStopForward != 1:
                                    DirectionSystem.left_side_forward(data[2])
                                elif DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                    DirectionSystem.lastSavedDirectionLeftSide = 'forward'
                                    DirectionSystem.stopLeft()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionLeftSide = 'forward' 

                            elif (data[0] == "L" and data[1] == "B"):
                                if sharedProperties.forceStopBackward != 1:
                                    DirectionSystem.left_side_backward(data[2])
                                elif DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                    DirectionSystem.lastSavedDirectionLeftSide = 'backward'
                                    DirectionSystem.stopLeft()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionLeftSide = 'backward' 

                            elif (data[0] == "R" and data[1] == "F"):
                                if sharedProperties.forceStopForward != 1:
                                    DirectionSystem.right_side_forward(data[2])
                                elif DirectionSystem.lastSavedDirectionRightSide != 'none':
                                    DirectionSystem.lastSavedDirectionRightSide = 'forward'
                                    DirectionSystem.stopRight()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionRightSide = 'forward' 

                            elif (data[0] == "R" and data[1] == "B"):
                                if sharedProperties.forceStopBackward != 1:
                                    DirectionSystem.right_side_backward(data[2])
                                elif DirectionSystem.lastSavedDirectionRightSide != 'none':
                                    DirectionSystem.lastSavedDirectionRightSide = 'backward'
                                    DirectionSystem.stopRight()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionRightSide = 'backward' 

                            
                            if (data[3] == "L" and data[4] == "F"):
                                if sharedProperties.forceStopForward != 1:
                                    DirectionSystem.left_side_forward(data[5])
                                elif DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                    DirectionSystem.lastSavedDirectionLeftSide = 'forward'
                                    DirectionSystem.stopLeft()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionLeftSide = 'forward' 

                            elif (data[3] == "L" and data[4] == "B"):
                                if sharedProperties.forceStopBackward != 1:
                                    DirectionSystem.left_side_backward(data[5])
                                elif DirectionSystem.lastSavedDirectionLeftSide != 'none':
                                    DirectionSystem.lastSavedDirectionLeftSide = 'backward'
                                    DirectionSystem.stopLeft()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionLeftSide = 'backward' 

                            elif (data[3] == "R" and data[4] == "F"):
                                if sharedProperties.forceStopForward != 1:
                                    DirectionSystem.right_side_forward(data[5])
                                elif DirectionSystem.lastSavedDirectionRightSide != 'none':
                                    DirectionSystem.lastSavedDirectionRightSide = 'forward'
                                    DirectionSystem.stopRight()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionRightSide = 'forward' 
                                    
                            elif (data[3] == "R" and data[4] == "B"):
                                if sharedProperties.forceStopBackward != 1:
                                    DirectionSystem.right_side_backward(data[5])
                                elif DirectionSystem.lastSavedDirectionRightSide != 'none':
                                    DirectionSystem.lastSavedDirectionRightSide = 'backward'
                                    DirectionSystem.stopRight()
                                else:
                                    # Make sure it still record the desired new
                                    DirectionSystem.currentDirectionRightSide = 'backward' 

                    
            except IOError as e:  # and here it is handeled
                pass
            await asyncio.sleep(0.05)
        else:
            await asyncio.sleep(1)
    

    
async def thread_distance_calculator(sharedProperties):
    while not sharedProperties.endOfProgram:
    
        sharedProperties.frontalDistance = DistanceCaptor.distanceFront()
        if Config.DEBUG_ENABLED:
            logging.info('frontalDistance: %s', sharedProperties.frontalDistance)
        if (sharedProperties.frontalDistance < Config.DISTANCE_THRESHOLD):
            sharedProperties.forceStopForward = 1
            logging.info('Proximity frontal alert !!')
            if Config.DEBUG_ENABLED:
                logging.info('sharedProperties.forceStopForward1: %s', sharedProperties.forceStopForward)
        else:
            sharedProperties.forceStopForward = 0
            if Config.DEBUG_ENABLED:
                logging.info('sharedProperties.forceStopForward2: %s', sharedProperties.forceStopForward)
            
        await asyncio.sleep(0.1)

        sharedProperties.rearDistance = DistanceCaptor.distanceRear()
        if Config.DEBUG_ENABLED:
            logging.info('rearDistance: %s', sharedProperties.rearDistance)
        if (sharedProperties.rearDistance < Config.DISTANCE_THRESHOLD):
            sharedProperties.forceStopBackward = 1
            logging.info('Proximity dorsal alert !!')
            if Config.DEBUG_ENABLED:
                logging.info('sharedProperties.forceStopBackward1: %s', sharedProperties.forceStopBackward)
        else:
            sharedProperties.forceStopBackward = 0
            if Config.DEBUG_ENABLED:
                logging.info('sharedProperties.forceStopBackward2: %s', sharedProperties.forceStopBackward)
        """ 
        await asyncio.sleep(0.01)

        sharedProperties.objectDetection = DistanceCaptor.distanceFrontTop()
        if Config.DEBUG_ENABLED:
            logging.info('objectDetection: %s', sharedProperties.objectDetection)
             """
        await asyncio.sleep(1)

async def thread_detect_reset_switch(sharedProperties):
    while not sharedProperties.endOfProgram:
        input_state = GPIO.input(RESET_TRIGGER_PIN)
        if input_state == False:
            sharedProperties.endOfProgram = 1
        
        await asyncio.sleep(0.2)

async def thread_screen_controller(sharedProperties):
    while not sharedProperties.endOfProgram:
    
        #Connect socketTwo
        
        await asyncio.sleep(1)
    #Disconnect socketTwo
        
async def thread_sound_controller(sharedProperties):
    while not sharedProperties.endOfProgram:
    
        #Connect socketThree
        
        await asyncio.sleep(1)
    #Disconnect socketThree
        

# Define a main async method (our program)
async def robotProgram():
    # Setup an object to track our state in
    sharedProperties = type('', (), {})()
    sharedProperties.endOfProgram = 0
    sharedProperties.frontalDistance = 999999
    sharedProperties.rearDistance = 999999
    sharedProperties.currentDireciton = "none"
    sharedProperties.forceStopForward = 0
    sharedProperties.forceStopBackward = 0
    sharedProperties.objectDetection = 999999
    sharedProperties.connection = None
    
    # Run all thread and wait for them to complete (passing in sharedProperties)
    #await asyncio.gather(thread_distance_calculator(sharedProperties), thread_direction_controller(sharedProperties), thread_screen_controller(sharedProperties), thread_sound_controller(sharedProperties))
    await asyncio.gather(thread_socket_server(sharedProperties), thread_direction_controller(sharedProperties), thread_detect_reset_switch(sharedProperties), thread_distance_calculator(sharedProperties))
    #await asyncio.gather(thread_socket_server(sharedProperties), thread_direction_controller(sharedProperties))
    
    # Once both are complete print done
    logging.info("End of program")

# Run our program until it is complete
loop = asyncio.get_event_loop()
loop.run_until_complete(robotProgram())
loop.close()

#####
# Add verification of frontalDistance when trying to move forward
# And add in socket loop a verification of forceStop status in case signal has cut
####

#LCD
#https://www.teachmemicro.com/raspberry-pi-lcd-hd44780/
