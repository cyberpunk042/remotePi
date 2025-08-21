import asyncio
import sys
import socket
import time
import RPi.GPIO as GPIO
from remotePiClasses.directionClass import DirectionSystem
import remotePiClasses.configClass as Config
import fcntl, os
import logging
import json
from logging.handlers import RotatingFileHandler
import shutil
import glob
import psutil
import threading
try:
    from serial.tools import list_ports  # type: ignore
except Exception:
    list_ports = None

# --- Load configuration from config.json ---
with open('config.json', 'r') as f:
    CONFIG = json.load(f)

# --- Logging setup with rotation ---
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
log_handler = RotatingFileHandler(CONFIG.get('log_file', 'remotePi.log'), maxBytes=1024*1024, backupCount=3)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.handlers.clear()  # Prevent duplicate logs
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# --- Direction system (Arduino motor controller) ---
def find_candidate_motor_ports():
    candidates = []
    # Configured port first, if provided
    cfg_port = CONFIG.get('motor_serial_port')
    if cfg_port:
        candidates.append(cfg_port)
    # Enumerate pyserial ports if available
    if list_ports is not None:
        try:
            for p in list_ports.comports():
                if getattr(p, 'device', None):
                    candidates.append(p.device)
        except Exception:
            pass
    # Add common device patterns
    candidates.extend(sorted(glob.glob('/dev/serial/by-id/*')))
    candidates.extend(sorted(glob.glob('/dev/ttyACM*')))
    candidates.extend(sorted(glob.glob('/dev/ttyUSB*')))
    candidates.extend(sorted(glob.glob('/dev/ttyAMA*')))

    # Deduplicate while preserving order
    unique = []
    seen = set()
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    return unique

DIRECTION_BAUD = CONFIG.get('motor_baud', 115200)
direction = None
DIRECTION_SERIAL_PORT = None
for candidate_port in find_candidate_motor_ports():
    try:
        direction = DirectionSystem(
            port=candidate_port,
            baudrate=DIRECTION_BAUD,
            debug=bool(Config.DEBUG_ENABLED),
        )
        DIRECTION_SERIAL_PORT = candidate_port
        logging.info(f"DirectionSystem initialized on {candidate_port} @ {DIRECTION_BAUD} bps")
        break
    except Exception as e:
        logging.warning(f"Failed to open motor controller on {candidate_port}: {e}")
        direction = None
        continue
if direction is None:
    logging.error("No usable serial port found for DirectionSystem. Set 'motor_serial_port' in config.json or connect the device.")

# --- Metrics ---
service_start_time = time.time()
metrics = {
    'connections': 0,
    'commands_processed': 0,
    'errors': 0,
    'uptime_sec': 0,
    'memory_mb': 0.0
}

# --- Camera stream config ---
ENABLE_CAMERA_STREAM = CONFIG.get('enable_camera_stream', False)
CAMERA_STREAM_HOST = CONFIG.get('camera_stream_host', '0.0.0.0')
CAMERA_STREAM_PORT = CONFIG.get('camera_stream_port', 8081)
CAMERA_INDEX = CONFIG.get('camera_index', 0)
CAMERA_WIDTH = CONFIG.get('camera_width', 640)
CAMERA_HEIGHT = CONFIG.get('camera_height', 480)
CAMERA_FPS = CONFIG.get('camera_fps', 20)
CAMERA_JPEG_QUALITY = CONFIG.get('camera_jpeg_quality', 80)

# --- Uptime and memory usage logging ---
async def metrics_logger_task():
    log_interval = CONFIG.get('metrics_log_interval_sec', 600)  # 10 minutes default
    while True:
        metrics['uptime_sec'] = int(time.time() - service_start_time)
        process = psutil.Process(os.getpid())
        metrics['memory_mb'] = process.memory_info().rss / (1024 ** 2)
        logging.info(f"Uptime: {metrics['uptime_sec']}s, Memory usage: {metrics['memory_mb']:.2f}MB")
        await asyncio.sleep(log_interval)

# --- Disk space monitoring and log cleanup ---
def get_disk_free_mb(path="/"):
    total, used, free = shutil.disk_usage(path)
    return free / (1024 ** 2)  # Free space in MB

async def disk_monitor_task():
    min_free_mb = CONFIG.get('min_free_mb', 100)  # Default 100 MB
    log_pattern = CONFIG.get('log_cleanup_pattern', 'remotePi.log*')
    check_interval = CONFIG.get('disk_check_interval_sec', 600)  # 10 minutes default
    while True:
        free_mb = get_disk_free_mb(CONFIG.get('disk_check_path', '/'))
        if free_mb < min_free_mb:
            logging.warning(f"Low disk space: {free_mb:.2f}MB free. Flushing logs matching {log_pattern}.")
            for log_file in glob.glob(log_pattern):
                try:
                    os.remove(log_file)
                    logging.info(f"Deleted log file: {log_file}")
                except Exception as e:
                    logging.error(f"Failed to delete {log_file}: {e}")
        await asyncio.sleep(check_interval)

# Optionally import aiohttp and define health server if enabled
ENABLE_HEALTH_SERVER = CONFIG.get('enable_health_server', False)
if ENABLE_HEALTH_SERVER:
    try:
        from aiohttp import web
        async def handle_health(request):
            # Update uptime and memory before reporting
            metrics['uptime_sec'] = int(time.time() - service_start_time)
            process = psutil.Process(os.getpid())
            metrics['memory_mb'] = process.memory_info().rss / (1024 ** 2)
            return web.json_response({
                'status': 'ok',
                'connections': metrics['connections'],
                'commands_processed': metrics['commands_processed'],
                'errors': metrics['errors'],
                'uptime_sec': metrics['uptime_sec'],
                'memory_mb': metrics['memory_mb']
            })
        async def start_health_server():
            app = web.Application()
            app.router.add_get('/health', handle_health)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, CONFIG.get('health_host', '0.0.0.0'), CONFIG.get('health_port', 8080))
            await site.start()
            logging.info(f"Health check server running on {CONFIG.get('health_host', '0.0.0.0')}:{CONFIG.get('health_port', 8080)}")
    except ImportError:
        logging.error("aiohttp is not installed, but enable_health_server is True in config.json. Health server will not start.")
        ENABLE_HEALTH_SERVER = False
else:
    async def start_health_server():
        pass

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
server_address = (CONFIG.get('host', '0.0.0.0'), CONFIG.get('port', 9999))
logging.info('starting up on (%s,%s)', server_address[0], server_address[1])
sock.bind(server_address)

# Listen for incoming connections
sock.listen(SYSTEMD_FIRST_SOCKET_FD)

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

RESET_TRIGGER_PIN = CONFIG.get('reset_trigger_pin', 21)
GPIO.setup(RESET_TRIGGER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
 
#Disable warnings
GPIO.setwarnings(False)

async def thread_socket_server(sharedProperties):
    while not sharedProperties.endOfProgram:        
        if sharedProperties.connection is None:
            logging.info('waiting for a connection')
            try:
                sharedProperties.connection, client_address = sock.accept()
                metrics['connections'] += 1
                logging.info('connection from: %s', client_address)
                sharedProperties.connection.setblocking(0)
                # ColorModule.turnOnBlueLed()
            except IOError as e:  # and here it is handeled
                await asyncio.sleep(1)
            except Exception as e:
                metrics['errors'] += 1
                logging.exception('Unexpected error accepting connection:')
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(1)
    if sharedProperties.connection is not None:
        sharedProperties.connection.close()
        # ColorModule.turnOffBlueLed()
        logging.info("Closed connection")
    GPIO.cleanup()
    logging.info("GPIO cleanup")
    sock.shutdown(socket.SHUT_RDWR)
    logging.info("Disconnected socket")

async def thread_direction_controller(sharedProperties):
    data = ""
    while not sharedProperties.endOfProgram:
        await asyncio.sleep(0.001)
        # If using Arduino for motor control, you may not need update_motors_periodic
        # DirectionSystem.update_motors_periodic()
        if sharedProperties.connection is not None:
            try:
                raw = sharedProperties.connection.recv(2048)
                if not raw:
                    # Client disconnected
                    logging.info("Client disconnected (recv returned empty)")
                    sharedProperties.connection.close()
                    sharedProperties.connection = None
                    continue
                data = raw.decode('utf-8')
                if Config.DEBUG_ENABLED:
                    logging.info('raw data: %r', data)
                # Split and process each line
                for line in data.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("L:"):
                        value = line[2:]
                        if direction is not None:
                            direction.set_speed_left(value)
                            logging.info(f"Set left speed to {value}")
                        else:
                            logging.error("DirectionSystem unavailable; cannot set left speed")
                        metrics['commands_processed'] += 1
                    elif line.startswith("R:"):
                        value = line[2:]
                        if direction is not None:
                            direction.set_speed_right(value)
                            logging.info(f"Set right speed to {value}")
                        else:
                            logging.error("DirectionSystem unavailable; cannot set right speed")
                        metrics['commands_processed'] += 1
                    elif line == "reset":
                        sharedProperties.endOfProgram = 1
                        logging.info("Received reset command")
                        metrics['commands_processed'] += 1
                    # (other command handling as needed)
            except (ConnectionResetError, BrokenPipeError) as e:
                logging.info(f"Client disconnected ({type(e).__name__})")
                if sharedProperties.connection:
                    sharedProperties.connection.close()
                sharedProperties.connection = None
            except IOError as e:
                await asyncio.sleep(0.05)
            except Exception as e:
                metrics['errors'] += 1
                logging.exception('Unexpected error in direction controller:')
                await asyncio.sleep(0.05)
        else:
            await asyncio.sleep(1)
    

async def thread_detect_reset_switch(sharedProperties):
    while not sharedProperties.endOfProgram:
        input_state = GPIO.input(RESET_TRIGGER_PIN)
        if input_state == False:
            sharedProperties.endOfProgram = 1
            logging.info("Physical reset switch triggered")
        await asyncio.sleep(0.2)

async def thread_screen_controller(sharedProperties):
    enable_screen = CONFIG.get('enable_robot_face_screen', True)
    if not enable_screen:
        # Screen disabled via config
        while not sharedProperties.endOfProgram:
            await asyncio.sleep(1)
        return

    # Defer pygame to a background thread to avoid blocking asyncio
    from remotePiClasses.robotFaceDisplay import RobotFaceDisplay

    def _run_face():
        face = RobotFaceDisplay(fullscreen=CONFIG.get('screen_fullscreen', True))
        face.run(sharedProperties)

    screen_thread = threading.Thread(target=_run_face, name="RobotFaceDisplayThread", daemon=True)
    screen_thread.start()

    try:
        while not sharedProperties.endOfProgram:
            await asyncio.sleep(0.2)
    finally:
        # Wait a moment for thread to exit gracefully
        for _ in range(10):
            if not screen_thread.is_alive():
                break
            await asyncio.sleep(0.1)
        
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
    
    # Start health check server if enabled
    if ENABLE_HEALTH_SERVER:
        await start_health_server()
    # Run all thread and wait for them to complete (passing in sharedProperties)
    camera_stream_task = None
    if ENABLE_CAMERA_STREAM:
        try:
            from remotePiClasses.cameraStreamer import CameraStreamer
            camera_streamer = CameraStreamer(
                camera_index=CAMERA_INDEX,
                frame_width=CAMERA_WIDTH,
                frame_height=CAMERA_HEIGHT,
                target_fps=CAMERA_FPS,
                jpeg_quality=CAMERA_JPEG_QUALITY,
                debug=bool(Config.DEBUG_ENABLED),
            )
            async def _start_camera():
                try:
                    await camera_streamer.start(CAMERA_STREAM_HOST, CAMERA_STREAM_PORT)
                except Exception:
                    logging.exception("Failed to start camera stream server")
            camera_stream_task = asyncio.create_task(_start_camera())
        except Exception:
            logging.exception("CameraStreamer not available")
            camera_stream_task = None

    try:
        await asyncio.gather(
            thread_socket_server(sharedProperties),
            thread_direction_controller(sharedProperties),
            thread_detect_reset_switch(sharedProperties),
            thread_screen_controller(sharedProperties),
            disk_monitor_task(),
            metrics_logger_task(),
        )
    finally:
        # Close DirectionSystem serial connection if initialized
        try:
            if 'direction' in globals() and direction is not None:
                direction.close()
                logging.info("DirectionSystem closed")
        except Exception:
            logging.exception("Error while closing DirectionSystem")
        if ENABLE_CAMERA_STREAM and 'camera_streamer' in locals():
            try:
                await camera_streamer.stop()
            except Exception:
                logging.exception("Error while stopping camera streamer")
        if camera_stream_task is not None:
            try:
                camera_stream_task.cancel()
            except Exception:
                pass
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
