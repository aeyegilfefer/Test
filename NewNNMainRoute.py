from __future__ import absolute_import, division, print_function, unicode_literals
'''
Created on Feb 6, 2020

@author: GilFefer
'''
import argparse
from flask import Flask, request, send_from_directory, jsonify
import json
from NNManagement import NNMainServer
import sys
import requests
import os
import shutil
import tensorflow as tf
from ErrorCodes import ErrorCodes
from uuid import getnode as get_mac
from hashlib import sha256
import yaml

app = Flask(__name__)
NN = None

@app.route("/nnregister/<registrationstring>", methods=["GET"])
def nnregister(registrationstring):

    r = NN.nnregister(registrationstring)
    return r

@app.route("/isalive")
def isalive():
    lambda_alive = 0
    try:
        from RemoteCall import RemoteCall
        RemoteCall = RemoteCall()
        res_json = RemoteCall.CallRemoteFunction('isalive', None, 'filters')
        del RemoteCall
        lambda_alive = res_json.get('body')

    except Exception as e:
        lambda_alive = -1

    return "{\"isalive\":\"1\",\"lambda_alive\":\"" + str(lambda_alive) + "\"}"

@app.route("/getnumberofgpus", methods=["GET"])
def getnumberofgpus():
    numofgpus = tf.contrib.eager.num_gpus()
    outputdata = {}
    outputdata["numofgpus"] = numofgpus
    jsondata = json.dumps(outputdata)
    return jsondata

    #return jsonify("{\"numofgpus\":" + str(numofgpus) + "}")
    #print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))

@app.route("/getsysteminfo", methods=["GET"])
def getsysteminfo():
    mac = get_mac()
    #dmi = DMIDecode()
    #Processor = dmi.get("Processor")[0].get("ID")
    numofgpus = tf.contrib.eager.num_gpus()
    total_root, used_root, free_root = shutil.disk_usage("/")
    total_m, used_m, free_m = map(int, os.popen('free -t -m').readlines()[-1].split()[1:])

    outputdata = {}
    outputdata["mac"] = mac
    #outputdata["ProcessorID"] = Processor
    outputdata["numofgpus"] = numofgpus
    outputdata["total_root"] = total_root
    outputdata["used_root"] = used_root
    outputdata["free_root"] = free_root
    outputdata["total_m"] = total_m
    outputdata["used_m"] = used_m
    outputdata["free_m"] = free_m
    jsondata = json.dumps(outputdata)
    return jsondata

@app.route("/getconfiguration", methods=["GET"])
def getconfiguration():
    resp = NN.getconfiguration()
    return resp

@app.route("/setconfiguration", methods=["POST"])
def setconfiguration():
    r = NN.setconfiguration(request.json)
    return r

@app.route('/getlogfile/<filename>', methods=['GET'])
def getlogfile(filename):
    return send_from_directory(directory='/var/log/aeyelogs/filters', filename=filename)

@app.route("/uploadandcheckimages", methods=["POST"])
def uploadandcheckimages():
    try:
        getalldebugdata = False
        if 'getalldebugdata' in request.json:
            getalldebugdata = request.json.get('getalldebugdata')
        settings = request.json.get('settings')

        # Write the license file
        mac = ""
        code = ""
        if 'mac' in request.json:
            mac = request.json.get('mac')
        if 'code' in request.json:
            code = request.json.get('code')

        data = {
            'mac': mac,
            'code': code
        }
        with open('license.yaml', 'w') as file:
            documents = yaml.dump(data, file)

        r = NN.processuploadimages(request.json, settings)
        r_json = r.json
        errorcode = r_json.get('errorcode')
        if errorcode == 1000:
            diskfullfilename_l = r_json.get('diskfullfilename_l')
            diskfullfilename_r = r_json.get('diskfullfilename_r')
            maculafullfilename_l = r_json.get('maculafullfilename_l')
            maculafullfilename_r = r_json.get('maculafullfilename_r')
            numberofimages = r_json.get('numberofimages')
            r = NN.processcheckimages(numberofimages, diskfullfilename_l, diskfullfilename_r, maculafullfilename_l, maculafullfilename_r, getalldebugdata, settings)
            if diskfullfilename_l != None:
                if os.path.isfile(diskfullfilename_l) == True:
                    os.remove(diskfullfilename_l)
            if diskfullfilename_r != None:
                if os.path.isfile(diskfullfilename_r) == True:
                    os.remove(diskfullfilename_r)
            if maculafullfilename_l != None:
                if os.path.isfile(maculafullfilename_l) == True:
                    os.remove(maculafullfilename_l)
            if maculafullfilename_r != None:
                if os.path.isfile(maculafullfilename_r) == True:
                    os.remove(maculafullfilename_r)
        return r
    except:
        #print('Unexpected error: ', sys.exc_info()[0])
        outputdata = {}
        outputdata["errorcode"] = ErrorCodes.PROCESS_CHECK_IMAGES_EXCEPTION
        outputdata["message"] = 'General exception'
        jsondata = json.dumps(outputdata)
        return jsondata

@app.route("/stop", methods=["POST"])
def stop():
    print("Got stop command, going to stop the process")
    r = NN.stop()
    del NN
    return r

def sendStopCommand():
    jsondata = {'stopcommand': True}
    r = requests.post(url = "http://localhost:5000/stop", json=jsondata)
    data = r.json()
    print (data)

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--start', action='store_true', help = 'an integer for the accumulator')
parser.add_argument('--stop', action='store_true', help = 'an integer for the accumulator')
parser.add_argument('--ssl', action='store_true', help = 'an integer for the accumulator')
args = parser.parse_args()

if args.start == False and args.stop == False:
    parser.print_help(sys.stderr)
    exit(1)

print("Commad line is: start: " + str(args.start) + " stop: " + str(args.stop))
if args.start == True:
    NN = NNMainServer()
    cur_env = dict(os.environ)
    cur_env["FL_CENTRAL_CONFIG"] = NN.CenteralConfigPath + "/fl_central_config.yaml"
    os.environ.update(cur_env)
    #NN.start()

if args.stop == True:
    print("Going to send stop command")
    sendStopCommand()

if __name__ == '__main__':
    if args.ssl == True:
        app.run(port = 5000, debug = False, host="0.0.0.0", ssl_context='adhoc')
    else:
        app.run(port = 5000, debug = False, host="0.0.0.0")
