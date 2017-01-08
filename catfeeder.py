#!/usr/bin/python

import json
import logging
import time
import RPi.GPIO as GPIO
from flask import Flask, request

DEBUG = True
PORT_NUMBER = 80
FEEDING = False
PWM = 0
PWM_PHYSICAL_PIN = 11 # Pin 11 is GPIO 18 on RPi3
PWM_FREQUENCY = 50 # Duty Cycle Frequency in Hz
PWM_DUTY_CYCLE = 1
ROTATION_TIME_MS = 2000

# logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('catfeeder')

# Setup Servo PWM

def setupServo():
    global PWM
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PWM_PHYSICAL_PIN, GPIO.OUT)
    PWM = GPIO.PWM(PWM_PHYSICAL_PIN, PWM_FREQUENCY)

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
    global FEEDING
    global PWM
    global PWM_DUTY_CYCLE
    global ROTATION_TIME_MS

    status = ''
    content = request.json

    logger.info('POST /feed')
    logger.info('Current feeding status: {0} - Received request to feed {1} portions'.format(FEEDING, content['portionCount']))

    if FEEDING == True:
        status = 'Already feeding {0} portions, ignoring request'.format(content['portionCount'])
        logger.info(status)

    else:
        FEEDING = True
        status = 'Starting feeding for {0} portions'.format(content['portionCount'])
        logger.info(status)

        logger.debug('Starting servo for {0}s'.format(ROTATION_TIME_MS / 1000))
        PWM.start(PWM_DUTY_CYCLE)
        time.sleep(ROTATION_TIME_MS / 1000)
        PWM.stop()
        logger.debug('Servo stopped')
        FEEDING = False

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
    logger.info('Starting')
    app.run(host='0.0.0.0', port=PORT_NUMBER)
