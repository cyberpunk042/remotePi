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
server_address = ('0.0.0.0', 9999)
logging.info('starting up on (%s,%s)', server_address[0], server_address[1])
sock.bind(server_address)

# Listen for incoming connections
sock.listen(SYSTEMD_FIRST_SOCKET_FD)


#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

RESET_TRIGGER_PIN=21
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
                # ColorModule.turnOnBlueLed()

            except IOError as e:  # and here it is handeled
                pass    
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(1)
    
    if sharedProperties.connection is not None:
        sharedProperties.connection.close()
        # ColorModule.turnOffBlueLed()
        logging.info("Closed connection")

    GPIO.cleanup()
    logging.info("GPIO cleanup")
    # Explicitly cleanup motors
    try:
        DirectionSystem.left_motor.cleanup()
        DirectionSystem.right_motor.cleanup()
        logging.info("Motor cleanup done")
    except Exception as e:
        logging.error(f"Motor cleanup error: {e}")
    sock.shutdown(socket.SHUT_RDWR)
    logging.info("Disconnected socket")

async def thread_direction_controller(sharedProperties):
    data=""
    while not sharedProperties.endOfProgram:
        await asyncio.sleep(0.005)
        # Periodically update motors for smooth acceleration
        DirectionSystem.update_motors_periodic()
        if sharedProperties.connection is not None:
            try:  
                data = sharedProperties.connection.recv(2048).decode('utf-8') # 2048 or 4096 ?
                if Config.DEBUG_ENABLED:
                    logging.info('data: %s', data)

                # End of connection from client
                if not data:
                    sharedProperties.connection.close()
                    sharedProperties.connection = None
                    # ColorModule.turnOffBlueLed() # Turn off connection led
                
                # Client is killing the instance
                elif len(data) == 5 and data == "reset":
                    sharedProperties.endOfProgram = 1 
                else:
                    # Joystick float commands: L:<float> or R:<float>
                    if data.startswith("L:"):
                        value = data[2:]
                        DirectionSystem.set_speed_left(value)
                    elif data.startswith("R:"):
                        value = data[2:]
                        DirectionSystem.set_speed_right(value)
                    else:
                        pass
                    
            except IOError as e:  # and here it is handeled
                pass
            await asyncio.sleep(0.05)
        else:
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
    await asyncio.gather(thread_socket_server(sharedProperties), thread_direction_controller(sharedProperties), thread_detect_reset_switch(sharedProperties))
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
