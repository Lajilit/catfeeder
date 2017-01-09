import json
import logging
import time
from logging.handlers import RotatingFileHandler
from multiprocessing import Process, Value, Lock
from flask import Flask, request
import RPi.GPIO as GPIO

# config values
PORT_NUMBER = 80               # HTTP Port
BUTTON_PHYSICAL_PIN = 13       # Pin 13 is GPIO 27 on RPi3
SERVO_PWM_PHYSICAL_PIN = 11    # Pin 11 is GPIO 18 on RPi3
SERVO_PWM_FREQUENCY = 50       # PWM Frequency in Hz
FEEDER_PWM_DUTY_CYCLE = 1      # Duty Cycle to run PMM
FEEDER_PORTION_TIME_MS = 1000  # ms to run servo for each portion
DEFAULT_PORTION_COUNT = 1      # default number of portions to feed

# logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("catfeeder")

# flask setup
app = Flask(__name__, static_url_path="")
app.info = True  # enable debug mode

# multiprocessing shared value and lock states across processes
feedingState = Value('b', False)
lock = Lock()

# global values
PWM = 0


def feed(portionCount=DEFAULT_PORTION_COUNT):
    global logger
    global feedingState
    global lock

    logger.debug("{0} portion feed requested, current feed state: {1}".
                format(portionCount, feedingState.value))

    if feedingState.value == False:
        durationMs = FEEDER_PORTION_TIME_MS * portionCount
        logger.debug("Starting servo for {0}ms".format(durationMs))

        with lock:
            feedingState.value = True
            PWM.start(FEEDER_PWM_DUTY_CYCLE)
            time.sleep(durationMs / 1000)
            PWM.stop()
            feedingState.value = False
            logger.debug("Servo stopped")
    else:
        logger.debug("Ignoring request to feed, feeding in progress")


def setupGPIO():
    GPIO.setwarnings(False)   # ignore warnings if GPIO channel in use
    GPIO.setmode(GPIO.BOARD)  # use physical pin numbers


def setupServo():
    global PWM
    global logging
    global SERVO_PWM_PHYSICAL_PIN
    GPIO.setup(SERVO_PWM_PHYSICAL_PIN,
               GPIO.OUT)
    PWM = GPIO.PWM(SERVO_PWM_PHYSICAL_PIN,
                   SERVO_PWM_FREQUENCY)
    logger.info("PWM using physical pin {0} @ {1}Hz "
                .format(SERVO_PWM_PHYSICAL_PIN, SERVO_PWM_FREQUENCY))


def buttonHandler(feedingState, lock):
    global logging
    global BUTTON_PHYSICAL_PIN

    GPIO.setup(BUTTON_PHYSICAL_PIN,
               GPIO.IN,
               pull_up_down=GPIO.PUD_UP)
    logger.info("Button using physical pin {0}".format(BUTTON_PHYSICAL_PIN))
    logger.info("Button handler loop starting")
    while True:
        input_state = GPIO.input(BUTTON_PHYSICAL_PIN)
        if input_state == False:
            logger.debug("Button press detected")
            feed()
        time.sleep(0.2)  # ghetto debounce


@app.route("/")
def root():
    return app.send_static_file("index.html")


@app.route("/<path:path>")
def static_proxy(path):
    return app.send_static_file(path)


@app.route("/feed", methods=["POST"])
def postFeed():
    global logger
    status = ""
    content = request.json

    logger.info("POST /feed - received request to feed {0} portions"
                .format(content["portionCount"]))

    portionCount = int(content["portionCount"])
    if (portionCount > 2):
        status = "Portion count is too high ({0}), ignoring\
        ".format(portionCount)
    else:
        feed(portionCount)
        status = "Fed {0} portions".format(portionCount)
        logger.info(status)

    response = {}
    response["status"] = status
    return json.dumps(response)


if __name__ == "__main__":
    # rotating file handler which logs debug messages
    fh = RotatingFileHandler("catfeeder.log", maxBytes=10000, backupCount=1)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    logger.info("Catfeeder starting")
    setupGPIO()
    setupServo()

    # create button handler process
    buttonProcess = Process(target=buttonHandler, args=(feedingState, lock))
    buttonProcess.daemon = True
    buttonProcess.start()

    # start flask web app
    app.run(host="0.0.0.0", port=PORT_NUMBER, threaded=True)
