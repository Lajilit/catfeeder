#!/usr/bin/python

import json
from flask import Flask, request

DEBUG = True
PORT_NUMBER = 8080
FEEDING = False

# Setup Flask app

app = Flask(__name__, static_url_path='')
app.debug = DEBUG

# Routes

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_proxy(path):
  return app.send_static_file(path)

@app.route('/feed', methods=['POST'])
def feed():
    global FEEDING
    status = ''

    content = request.json
    print 'Current feeding status: {0} - Received request to feed {1} portions'.format(FEEDING, content['portionCount'])

    if FEEDING == True:
        status = 'Already feeding {0} portions, ignoring request'.format(content['portionCount'])
    else:
        FEEDING = True
        status = 'Starting feeding for {0} portions'.format(content['portionCount'])
    print status

    response = {}
    response['status'] = status
    return json.dumps(response)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT_NUMBER)
