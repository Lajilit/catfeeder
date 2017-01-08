#!/usr/bin/python

import json
import logging
import time
import RPi.GPIO as GPIO
from flask import Flask, request

DEBUG = True
PORT_NUMBER = 80
PWM = 0
FEEDING = False # True if the Servo is running

# config values
SERVO_PWM_PHYSICAL_PIN = 11   # Pin 11 is GPIO 18 on RPi3
SERVO_PWM_FREQUENCY = 50      # PWM Frequency in Hz
FEEDER_PWM_DUTY_CYCLE = 1     # Duty Cycle to run PMM
FEEDER_PORTION_TIME_MS = 1000 # ms to run servo for each portion

# logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('catfeeder')

# Setup Servo PWM

def setupServo():
    global PWM
    GPIO.setwarnings(False) # ignore warnings if GPIO channel is already in use
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(SERVO_PWM_PHYSICAL_PIN, GPIO.OUT)
    PWM = GPIO.PWM(SERVO_PWM_PHYSICAL_PIN, SERVO_PWM_FREQUENCY)

# Setup Flask app

app = Flask(__name__, static_url_path='')
app.info = DEBUG

# Routes

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_proxy(path):
  return app.send_static_file(path)

@app.route('/feed', methods=['POST'])
def feed():
    global logger
    global PWM
    global FEEDING
    global FEEDER_PWM_DUTY_CYCLE
    global FEEDER_PORTION_TIME_MS

    status = ''
    content = request.json

    logger.info('POST /feed')
    logger.info('Current feeding status: {0} - Received request to feed {1} portions'.format(FEEDING, content['portionCount']))

    if FEEDING == True:
        status = 'Already feeding {0} portions, ignoring request'.format(content['portionCount'])
        logger.info(status)

    else:
        portionCount = int(content['portionCount'])
        if (portionCount > 2):
            status = 'Portion count is too high ({0}), ignoring'.format(portionCount)
        else:
            durationMs = FEEDER_PORTION_TIME_MS * portionCount
            logger.debug('Starting servo for {0}ms'.format(durationMs))

            FEEDING = True
            PWM.start(FEEDER_PWM_DUTY_CYCLE)
            time.sleep(durationMs / 1000)
            PWM.stop()
            FEEDING = False
            logger.debug('Servo stopped')

            status = 'Fed {0} portions'.format(content['portionCount'])
            logger.info(status)

    response = {}
    response['status'] = status
    return json.dumps(response)

if __name__ == "__main__":
    # # create file handler which logs even debug messages
    # fh = logging.FileHandler('catfeeder.log')
    # fh.setLevel(logging.DEBUG)
    #
    # # create console handler with a higher log level
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.INFO)
    #
    # # create formatter and add it to the handlers
    # # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # # fh.setFormatter(formatter)
    # # ch.setFormatter(formatter)
    #
    # # add the handlers to the logger
    # logger.addHandler(fh)
    # logger.addHandler(ch)
    #
    #
    # # handler = RotatingFileHandler('catfeeder.log', maxBytes=10000, backupCount=1)
    # # handler.setLevel(logging.DEBUG)
    # # app.logger.addHandler(handler)
    # # logger.addHandler(ch)
    # #
    # #
    # # log = logging.getLogger('werkzeug')
    # # log.setLevel(logging.DEBUG)
    # # log.addHandler(handler)

    setupServo()
    logging.info('Catfeeder starting. PWM using physical pin {0} @ {1}Hz '.format(SERVO_PWM_PHYSICAL_PIN, SERVO_PWM_FREQUENCY))
    app.run(host='0.0.0.0', port=PORT_NUMBER)
