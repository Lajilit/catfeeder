#!/usr/bin/env python

#
# To feed, send a newline after valid json to the TCP socket:
#
# {
#   "seconds": 0.5,
#   "count": 2
# }
#
# Where seconds the the time in seconds to turn the feeder,
# and count is the number of times to repeat it.
# Everything else will be ignored.
#

import socket
import sys
import os
import logging
import datetime
import json
import time
import RPi.GPIO as GPIO
from flask import Flask, request
from logging.handlers import RotatingFileHandler
from multiprocessing import Process, Value, Lock

# config values
SERVER_PORT = 9000
HTTP_PORT = 80
SOCKET_READ_LENGTH = 1024
STATE_FILE = 'feeder_state.json'
BUTTON_PHYSICAL_PIN = 13       # Pin 13 is GPIO 27 on RPi3
BUTTON_DEBOUNCE_MS = 200       # ms to pause before reading button again
SERVO_PWM_PHYSICAL_PIN = 11    # Pin 11 is GPIO 18 on RPi3
SERVO_PWM_FREQUENCY = 50       # PWM Frequency in Hz
FEEDER_PWM_DUTY_CYCLE = 1      # Duty Cycle to run PMM
FEEDER_PORTION_TIME_MS = 1000  # ms to run servo for each portion
FEEDER_PORTION_COUNT_MAX = 2   # maximum number of allowed portions

# multiprocessing shared value and lock states across processes
feedingState = Value('b', False)
lock = Lock()

# TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# web app
app = Flask(__name__, static_url_path="")

# shared app state
appState = None

# GPIO
PWM = 0


# feeding instruction
class FeedInstruction:
    def __init__(self):
        self._seconds = None
        self._count = None

    def set(self, data):
        if 'seconds' in data and 'count' in data:
            self._seconds = data.get('seconds')
            self._count = data.get('count')
            return True
        logger.error('invalid data: %s' % data)
        return False

    def seconds(self):
        return self._seconds

    def count(self):
        return self._count


# response message format
class Status:
    def __init__(self, status, message):
        self.status = status
        self.message = message

    def toJSON(self):
        return json.dumps({
            'status': self.status,
            'message': self.message
        })


# Shared application state
class AppState:
    def __init__(self):
        self.timeLastFed = None
        self.count = None
        self.seconds = None
        self.fileInit()

    def fileInit(self):
        if os.path.isfile(STATE_FILE):
            logger.debug('Feeder state file found')
            self.load()
        else:
            logger.debug('Creating feeder state file')
            self.save()

    def log(self, seconds, count):
        self.seconds = seconds
        self.count = count
        self.timeLastFed = datetime.datetime.utcnow().isoformat()
        self.save()

    def save(self):
        with open(STATE_FILE, 'w') as outfile:
            json.dump(self.__dict__, outfile)

    def load(self):
        with open(STATE_FILE) as infile:
            appState = json.load(infile)

            if ('seconds' in appState
                and 'count' in appState
                and 'timeLastFed' in appState):
                    self.seconds = appState.get('seconds')
                    self.count = appState.get('count')
                    self.timeLastFed = appState.get('timeLastFed')
                    return True

            logger.error('unable to load app state from file')
            return False

    def lastFed(self):
        return self.timeLastFed


# activate feeder for seconds
def doServo(feed):
    global appState

    # blocking call
    with lock:
        feedingState.value = True
        logger.info('Feed start, activating servo for %s seconds %s times',
                    feed.seconds(),
                    feed.count())

        for x in range(0, feed.count()):
            logger.debug('Feeding portion: start')
            PWM.start(FEEDER_PWM_DUTY_CYCLE)
            time.sleep(feed.seconds())
            PWM.stop()
            logger.debug('Feeding portion: stopped')

        logger.info('Feed complete')

        # save the feeding event
        appState.log(feed.seconds(), feed.count())
        feedingState.value = False


# handle a valid message, lock on action
def handleFeedData(data):
    global feedingState
    global lock
    response = None
    feed = FeedInstruction()
    if feed.set(data):
        doServo(feed)
        response = Status('ok', 'feeding successful').toJSON(), 200
    else:
        response = Status('error', 'invalid json schema').toJSON(), 400
        logger.error('invalid feed data: %s' % data)

    return response


# return json object if valid json string
def validJSONParser(buffer):
    obj = None
    try:
        obj = json.loads(buffer)
        logger.debug('decoded json: %s' % obj)
    except Exception, e:
        logger.debug('error decoding json: %s' % e)
    return obj


# HTP Handlers


@app.route("/")
def root():
    return app.send_static_file("index.html")


@app.route("/<path:path>")
def static_proxy(path):
    return app.send_static_file(path)


@app.route("/lastFed", methods=["GET"])
def getLastFed():
    logger.info("HTTP GET /lastFed")
    response = {
        'lastFed': appState.lastFed()
    }
    return json.dumps(response)


@app.route("/feed", methods=["POST"])
def postFeed():
    logger.info("HTTP POST /feed")

    if ('portionCount' not in request.json):
        return Status('error', 'portionCount is required').toJSON(), 400
    count = int(request.json.get("portionCount"))
    if (count > FEEDER_PORTION_COUNT_MAX):
        return Status('error', 'portionCount is too high').toJSON(), 400
    else:
        resp, status = handleFeedData({
            'count': count,
            'seconds': FEEDER_PORTION_TIME_MS / 1000
        })
        return resp, status


# handle physical button press events
def buttonHandler():
    GPIO.setup(BUTTON_PHYSICAL_PIN,
               GPIO.IN,
               pull_up_down=GPIO.PUD_UP)
    logger.info("Button handler loop using physical pin {0}"
                .format(BUTTON_PHYSICAL_PIN))
    while True:
        input_state = GPIO.input(BUTTON_PHYSICAL_PIN)
        if input_state is False:
            logger.info("Button press detected")
            handleFeedData({
                'count': 1,
                'seconds': FEEDER_PORTION_TIME_MS / 1000
            })
        time.sleep(BUTTON_DEBOUNCE_MS / 1000)


# setup GPIO
def gpioInit():
    GPIO.setwarnings(False)   # ignore warnings if GPIO channel in use
    GPIO.setmode(GPIO.BOARD)  # use physical pin numbers


# setup servo
def servoInit():
    GPIO.setup(SERVO_PWM_PHYSICAL_PIN,
               GPIO.OUT)
    PWM = GPIO.PWM(SERVO_PWM_PHYSICAL_PIN,
                   SERVO_PWM_FREQUENCY)
    logger.info("Servo PWM using physical pin {0} @ {1}Hz "
                .format(SERVO_PWM_PHYSICAL_PIN, SERVO_PWM_FREQUENCY))


# setup service
def appInit():
    global sock
    global app
    global appState

    # shared application state
    appState = AppState()

    # set socket options to reuse
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to the port
    server_address = ('localhost', SERVER_PORT)
    sock.bind(server_address)
    logger.info('tcp server bound to %s on port %s' % server_address)

    # flask setup
    app.info = True  # enable debug mode
    http_address = ('0.0.0.0', HTTP_PORT)
    logger.info('http server bound to %s on port %s' % http_address)


# listen for clients on webserver
def httpListen():
    global app

    # start flask web app
    app.run(host="0.0.0.0", port=HTTP_PORT, threaded=True)


# listen for clients on socket
def socketListen():
    global sock

    # Listen for incoming connections
    sock.listen(1)

    while True:
        # Wait for a connection
        logger.info('waiting for a connection')
        connection, client_address = sock.accept()

        try:
            logger.info('connection from %s', client_address)

            # Receive the data in small chunks and retransmit it
            while True:
                buffer = ''
                continue_recv = True
                while continue_recv:
                    try:
                        # Try to receive som data
                        data = connection.recv(SOCKET_READ_LENGTH)
                        buffer += data
                        logger.debug('read data from socket: %s',
                                     data.replace("\n", ""))

                        # check if buffer is valid json
                        jsonObj = validJSONParser(buffer)
                        if jsonObj is not None:
                            # attempt to feed
                            resp, status = handleFeedData(jsonObj)

                            # respond and clear buffer
                            connection.sendall(resp)
                            buffer = ''

                    except socket.error, e:
                        if e.errno != errno.EWOULDBLOCK:
                            # Error! Print it and tell main loop to stop
                            logger.error('Error: %r' % e)
                        # If e.errno is errno.EWOULDBLOCK, then no more data
                        continue_recv = False

        finally:
            # Clean up the connection
            connection.close()


if __name__ == "__main__":
    # logging setup
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("feedcontrol")

    # rotating file handler which logs debug messages
    fh = RotatingFileHandler("catfeeder_controller.log",
                             maxBytes=10000,
                             backupCount=1)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    # start things up
    gpioInit()
    servoInit()
    appInit()

    # create button handler process
    buttonProcess = Process(target=buttonHandler, args=())
    buttonProcess.daemon = True
    buttonProcess.start()

    httpListen()
    # socketListen()
