'''
Created on Feb 6, 2020

@author: GilFefer
'''
from flask import jsonify
import yaml
import threading
import os
import time
import json
from filter_engine import filter_engine
import pathlib
import sys
import subprocess
from werkzeug.utils import secure_filename
import logging
from logging.handlers import RotatingFileHandler
from asyncio.tasks import sleep
import base64
import configparser
#from inf_v6_detailed import infV5Detailed
from NNLogger import NNLogger
from ErrorCodes import ErrorCodes
from _ast import If

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class NNMainServer:
    def __init__(self):
        self.nnlogger = NNLogger(__name__)
        self.logger = self.nnlogger.getLogger()
        self.logger.debug('Init NNMainServer')
        workingfolder = os.getcwd()
        self.logger.debug("The current directory is: " + workingfolder)
        self.CenteralConfigPath = workingfolder

        self.numberofthreads = 1
        self.readingEnginesCounter = threading.Semaphore(self.numberofthreads)
        self.lockReadingEngines = threading.Lock()
        self.readingEngines = []
        for x in range(self.numberofthreads):
            readingengine = filter_engine()
            self.readingEngines.append(readingengine)

        #self.analyze4Images = analyze4Images()

    def __del__(self):
        del self.nnlogger
        for x in range(self.numberofthreads):
            readingengine = self.readingEngines.pop(0)
            del readingengine

    def start(self):
        self.logger.debug('Enter start')

    def stop(self):
        self.logger.debug('Enter stop')

    def nnregister(self, registrationstring):
        self.logger.debug('Enter nnregister')
        try:
            rc = False
            self.OnPremiseFunctions = None
            if os.path.isfile('OnPremiseFunctions.py') == True:
                from OnPremiseFunctions import OnPremiseFunctions
                self.OnPremiseFunctions = OnPremiseFunctions()

            if self.OnPremiseFunctions != None:
                rc = self.OnPremiseFunctions.nnregister(registrationstring)

            outputdata = {}
            outputdata["errorcode"] = ErrorCodes.PROCESS_OK
            outputdata["rc"] = rc
            jsondata = json.dumps(outputdata)
            return jsondata

        finally:
            self.logger.debug('Exit nnregister')

    def processcheckimages(self, numberofimages, diskfullfilename_l, diskfullfilename_r, maculafullfilename_l, maculafullfilename_r, getalldebugdata = False, settings = None):
        self.logger.debug('Enter processcheckimages')
        try:
            outputdata = {}
            if numberofimages == 2:

                #self.lockReadingEngines.acquire()
                self.readingEnginesCounter.acquire(blocking=True, timeout=None)
                filter_engine = self.readingEngines.pop(0)

                try:
                    self.logger.debug('Before run_engine')
                    readings = filter_engine.run_engine(maculafullfilename_l, maculafullfilename_r, settings)
                    self.logger.debug('After run_engine')

                except:
                    outputdata["errorcode"] = ErrorCodes.PROCESS_CHECK_READING_ENGINE_EXCEPTION
                    outputdata["message"] = 'General exception in reading engine'
                    jsondata = json.dumps(outputdata)
                    return jsondata

                finally:
                    self.readingEngines.append(filter_engine)
                    self.readingEnginesCounter.release()

                filter_results_l = readings["filter_results"][0]
                filter_results_r = readings["filter_results"][1]
                macula_r_bad = False
                macula_l_bad = False

                if filter_results_l != None and "fatalerror" in filter_results_l:
                    macula_l_bad = True
                    filter_results_l = None
                else:
                    if filter_results_l != None and (filter_results_l["zfilter_filtered"] or filter_results_l["cv_filtered"] or filter_results_l["cdw_filtered"] or filter_results_l["flares_filtered"] or filter_results_l["frangi_filtered"] or filter_results_l["oe_filtered"]):
                        macula_l_bad = True
                    else:
                        macula_l_bad = False

                if filter_results_r != None and "fatalerror" in filter_results_r:
                    macula_r_bad = True
                    filter_results_r = None
                else:
                    if filter_results_r != None and (filter_results_r["zfilter_filtered"] or filter_results_r["cv_filtered"] or filter_results_r["cdw_filtered"] or filter_results_r["flares_filtered"] or filter_results_r["frangi_filtered"] or filter_results_r["oe_filtered"]):
                        macula_r_bad = True
                    else:
                        macula_r_bad = False

                outputdata["maculaR_bad"] = macula_r_bad
                outputdata["maculaL_bad"] = macula_l_bad

                if getalldebugdata == True:
                    self.getFilterResults(outputdata, filter_results_l, filter_results_r, None, None)

                    filters_total_elapsed_r = 0
                    filters_total_elapsed_l = 0
                    if filter_results_r != None:
                        filters_total_elapsed_r = filter_results_r["zfilter_test_elapsed_time"] + filter_results_r["cvfilter_test_elapsed_time"] + filter_results_r["cdwfilter_test_elapsed_time"] + filter_results_r["flaresfilter_test_elapsed_time"] + filter_results_r["frangifilter_test_elapsed_time"] + filter_results_r["oefilter_test_elapsed_time"] + filter_results_r["cats_test_elapsed_time"]
                    if filter_results_l != None:
                        filters_total_elapsed_l = filter_results_l["zfilter_test_elapsed_time"] + filter_results_l["cvfilter_test_elapsed_time"] + filter_results_l["cdwfilter_test_elapsed_time"] + filter_results_l["flaresfilter_test_elapsed_time"] + filter_results_l["frangifilter_test_elapsed_time"] + filter_results_l["oefilter_test_elapsed_time"] + filter_results_l["cats_test_elapsed_time"]
                    outputdata["filters_total_elapsed"] = filters_total_elapsed_r + filters_total_elapsed_l

                outputdata["errorcode"] = ErrorCodes.PROCESS_OK
                jsondata = json.dumps(outputdata)
                self.logger.debug("JSON:" + jsondata)

                #self.lockReadingEngines.acquire()
                #self.lockReadingEngines.release()

                return jsondata
            elif numberofimages == 4:
                self.logger.debug('Inside 4 images')
                #[filter_results, macula_reading_result, optic_disc_reading_result, one_image_model_bottom_line, two_image_model_bottom_line] = self.analyze4Images.internal_analyze_4_images(maculafullfilename_r, maculafullfilename_l, diskfullfilename_r, diskfullfilename_l)

                self.readingEnginesCounter.acquire(blocking=True, timeout=None)
                filter_engine = self.readingEngines.pop(0)

                try:
                    self.logger.debug('Before run_engine_2_images')
                    readings = filter_engine.run_engine_2_images(maculafullfilename_l, maculafullfilename_r, diskfullfilename_l, diskfullfilename_r, settings)
                    self.logger.debug('After run_engine_2_images')
                except:
                    outputdata["errorcode"] = ErrorCodes.PROCESS_CHECK_READING_ENGINE_EXCEPTION
                    outputdata["message"] = 'General exception in reading engine'
                    jsondata = json.dumps(outputdata)
                    return jsondata

                finally:
                    self.readingEngines.append(filter_engine)
                    self.readingEnginesCounter.release()

                filter_results_l = readings["filter_results"][0]
                filter_results_r = readings["filter_results"][1]
                filter_results_disc_l = readings["filter_results"][2]
                filter_results_disc_r = readings["filter_results"][3]
                macula_r_bad = False
                macula_l_bad = False
                disc_r_bad = False
                disc_l_bad = False

                if "fatalerror" in filter_results_l:
                    macula_l_bad = True
                else:
                    if filter_results_l != None and (filter_results_l["zfilter_filtered"] or filter_results_l["cv_filtered"] or filter_results_l["cdw_filtered"] or filter_results_l["flares_filtered"] or filter_results_l["frangi_filtered"] or filter_results_l["oe_filtered"]):
                        macula_l_bad = True
                    else:
                        macula_l_bad = False

                if "fatalerror" in filter_results_r:
                    macula_r_bad = True
                else:
                    if filter_results_r != None and (filter_results_r["zfilter_filtered"] or filter_results_r["cv_filtered"] or filter_results_r["cdw_filtered"] or filter_results_r["flares_filtered"] or filter_results_r["frangi_filtered"] or filter_results_r["oe_filtered"]):
                        macula_r_bad = True
                    else:
                        macula_r_bad = False

                if "fatalerror" in filter_results_disc_l:
                    disc_r_bad = True
                else:
                    if filter_results_disc_l != None and (filter_results_disc_l["zfilter_filtered"] or filter_results_disc_l["cv_filtered"] or filter_results_disc_l["cdw_filtered"] or filter_results_disc_l["flares_filtered"] or filter_results_disc_l["frangi_filtered"] or filter_results_disc_l["oe_filtered"]):
                        disc_r_bad = True
                    else:
                        disc_r_bad = False

                if "fatalerror" in filter_results_disc_r:
                    disc_l_bad = True
                else:
                    if filter_results_disc_r != None and (filter_results_disc_r["zfilter_filtered"] or filter_results_disc_r["cv_filtered"] or filter_results_disc_r["cdw_filtered"] or filter_results_disc_r["flares_filtered"] or filter_results_disc_r["frangi_filtered"] or filter_results_disc_r["oe_filtered"]):
                        disc_l_bad = True
                    else:
                        disc_l_bad = False

                outputdata["maculaR_bad"] = macula_r_bad
                outputdata["maculaL_bad"] = macula_l_bad
                outputdata["discR_bad"] = disc_r_bad
                outputdata["discL_bad"] = disc_l_bad

                if getalldebugdata == True:
                    self.getFilterResults(outputdata, filter_results_l, filter_results_r, filter_results_disc_l, filter_results_disc_r)

                    filters_total_elapsed_r = 0
                    filters_total_elapsed_l = 0
                    filters_total_elapsed_disc_r = 0
                    filters_total_elapsed_disc_l = 0
                    if filter_results_r != None:
                        filters_total_elapsed_r = filter_results_r["zfilter_test_elapsed_time"] + filter_results_r["cvfilter_test_elapsed_time"] + filter_results_r["cdwfilter_test_elapsed_time"] + filter_results_r["flaresfilter_test_elapsed_time"] + filter_results_r["frangifilter_test_elapsed_time"] + filter_results_r["oefilter_test_elapsed_time"] + filter_results_r["cats_test_elapsed_time"]
                    if filter_results_l != None:
                        filters_total_elapsed_l = filter_results_l["zfilter_test_elapsed_time"] + filter_results_l["cvfilter_test_elapsed_time"] + filter_results_l["cdwfilter_test_elapsed_time"] + filter_results_l["flaresfilter_test_elapsed_time"] + filter_results_l["frangifilter_test_elapsed_time"] + filter_results_l["oefilter_test_elapsed_time"] + filter_results_l["cats_test_elapsed_time"]
                    if filter_results_disc_r != None:
                        filters_total_elapsed_disc_r = filter_results_disc_r["zfilter_test_elapsed_time"] + filter_results_disc_r["cvfilter_test_elapsed_time"] + filter_results_disc_r["cdwfilter_test_elapsed_time"] + filter_results_disc_r["flaresfilter_test_elapsed_time"] + filter_results_disc_r["frangifilter_test_elapsed_time"] + filter_results_disc_r["oefilter_test_elapsed_time"] + filter_results_disc_r["cats_test_elapsed_time"]
                    if filter_results_disc_l != None:
                        filters_total_elapsed_disc_l = filter_results_disc_l["zfilter_test_elapsed_time"] + filter_results_disc_l["cvfilter_test_elapsed_time"] + filter_results_disc_l["cdwfilter_test_elapsed_time"] + filter_results_disc_l["flaresfilter_test_elapsed_time"] + filter_results_disc_l["frangifilter_test_elapsed_time"] + filter_results_disc_l["oefilter_test_elapsed_time"] + filter_results_disc_l["cats_test_elapsed_time"]

                    outputdata["filters_total_elapsed"] = filters_total_elapsed_r+ filters_total_elapsed_l + filters_total_elapsed_disc_r + filters_total_elapsed_disc_l

                outputdata["errorcode"] = ErrorCodes.PROCESS_OK
                jsondata = json.dumps(outputdata)
                return jsondata
            else:
                outputdata["errorcode"] = ErrorCodes.PROCESS_MUST_PASS_2_OR_4_IMAGES
                outputdata["message"] = 'Must pass 2 or 4 images'
                jsondata = json.dumps(outputdata)
                return jsondata
        except:
            outputdata["errorcode"] = ErrorCodes.PROCESS_CHECK_IMAGES_EXCEPTION
            outputdata["message"] = 'General exception'
            jsondata = json.dumps(outputdata)
            return jsondata

        finally:
            self.logger.debug('Exit processcheckimages')

    def getFilterResults(self, outputdata, filter_results_l, filter_results_r, filter_results_disc_l, filter_results_disc_r):
        self.logger.debug('Enter processcheckimages')
        try:
            if filter_results_l != None:
                outputdata["Lzfilter_grade"] = filter_results_l["zfilter_grade"]
                outputdata["Lzfilter_elapsed"] = filter_results_l["zfilter_test_elapsed_time"]
                outputdata["Lcvfilter_grade"] = filter_results_l["cv_grade"]
                outputdata["Lcvfilter_elapsed"] = filter_results_l["cvfilter_test_elapsed_time"]
                outputdata["Lfrangifilter_grade"] = filter_results_l["frangi_grade"]
                outputdata["Lfrangifilter_elapsed"] = filter_results_l["frangifilter_test_elapsed_time"]
                outputdata["Lfrangifilter_artifacts"] = filter_results_l["frangi_artifacts"]
                outputdata["Loefilter_grade"] = filter_results_l["oe_grade"]
                outputdata["Loefilter_elapsed"] = filter_results_l["oefilter_test_elapsed_time"]
                outputdata["Lcatsfilter_grade"] = filter_results_l["cats_grade"]
                outputdata["Lcatsfilter_elapsed"] = filter_results_l["cats_test_elapsed_time"]
                outputdata["Lcdwfilter_grade"] = filter_results_l["cdw_grade"]
                outputdata["Lcdwfilter_elapsed"] = filter_results_l["cdwfilter_test_elapsed_time"]
                outputdata["Lflaresfilter_grade"] = filter_results_l["flares_grade"]
                outputdata["Lflaresfilter_elapsed"] = filter_results_l["flaresfilter_test_elapsed_time"]

            if filter_results_r != None:
                outputdata["Rzfilter_grade"] = filter_results_r["zfilter_grade"]
                outputdata["Rzfilter_elapsed"] = filter_results_r["zfilter_test_elapsed_time"]
                outputdata["Rcvfilter_grade"] = filter_results_r["cv_grade"]
                outputdata["Rcvfilter_elapsed"] = filter_results_r["cvfilter_test_elapsed_time"]
                outputdata["Rfrangifilter_grade"] = filter_results_r["frangi_grade"]
                outputdata["Rfrangifilter_elapsed"] = filter_results_r["frangifilter_test_elapsed_time"]
                outputdata["Rfrangifilter_artifacts"] = filter_results_r["frangi_artifacts"]
                outputdata["Roefilter_grade"] = filter_results_r["oe_grade"]
                outputdata["Roefilter_elapsed"] = filter_results_r["oefilter_test_elapsed_time"]
                outputdata["Rcatsfilter_grade"] = filter_results_r["cats_grade"]
                outputdata["Rcatsfilter_elapsed"] = filter_results_r["cats_test_elapsed_time"]
                outputdata["Rcdwfilter_grade"] = filter_results_r["cdw_grade"]
                outputdata["Rcdwfilter_elapsed"] = filter_results_r["cdwfilter_test_elapsed_time"]
                outputdata["Rflaresfilter_grade"] = filter_results_r["flares_grade"]
                outputdata["Rflaresfilter_elapsed"] = filter_results_r["flaresfilter_test_elapsed_time"]

            if filter_results_disc_l != None:
                outputdata["Lzfilter_grade_disc"] = filter_results_disc_l["zfilter_grade"]
                outputdata["Lzfilter_elapsed_disc"] = filter_results_disc_l["zfilter_test_elapsed_time"]
                outputdata["Lcvfilter_grade_disc"] = filter_results_disc_l["cv_grade"]
                outputdata["Lcvfilter_elapsed_disc"] = filter_results_disc_l["cvfilter_test_elapsed_time"]
                outputdata["Lfrangifilter_grade_disc"] = filter_results_disc_l["frangi_grade"]
                outputdata["Lfrangifilter_elapsed_disc"] = filter_results_disc_l["frangifilter_test_elapsed_time"]
                outputdata["Lfrangifilter_artifacts_disc"] = filter_results_disc_l["frangi_artifacts"]
                outputdata["Loefilter_grade_disc"] = filter_results_disc_l["oe_grade"]
                outputdata["Loefilter_elapsed_disc"] = filter_results_disc_l["oefilter_test_elapsed_time"]
                outputdata["Lcatsfilter_grade_disc"] = filter_results_disc_l["cats_grade"]
                outputdata["Lcatsfilter_elapsed_disc"] = filter_results_disc_l["cats_test_elapsed_time"]
                outputdata["Lcdwfilter_grade_disc"] = filter_results_disc_l["cdw_grade"]
                outputdata["Lcdwfilter_elapsed_disc"] = filter_results_disc_l["cdwfilter_test_elapsed_time"]
                outputdata["Lflaresfilter_grade_disc"] = filter_results_disc_l["flares_grade"]
                outputdata["Lflaresfilter_elapsed_disc"] = filter_results_disc_l["flaresfilter_test_elapsed_time"]

            if filter_results_disc_r != None:
                outputdata["Rzfilter_grade_disc"] = filter_results_disc_r["zfilter_grade"]
                outputdata["Rzfilter_elapsed_disc"] = filter_results_disc_r["zfilter_test_elapsed_time"]
                outputdata["Rcvfilter_grade_disc"] = filter_results_disc_r["cv_grade"]
                outputdata["Rcvfilter_elapsed_disc"] = filter_results_disc_r["cvfilter_test_elapsed_time"]
                outputdata["Rfrangifilter_grade_disc"] = filter_results_disc_r["frangi_grade"]
                outputdata["Rfrangifilter_elapsed_disc"] = filter_results_disc_r["frangifilter_test_elapsed_time"]
                outputdata["Rfrangifilter_artifacts_disc"] = filter_results_disc_r["frangi_artifacts"]
                outputdata["Roefilter_grade_disc"] = filter_results_disc_r["oe_grade"]
                outputdata["Roefilter_elapsed_disc"] = filter_results_disc_r["oefilter_test_elapsed_time"]
                outputdata["Rcatsfilter_grade_disc"] = filter_results_disc_r["cats_grade"]
                outputdata["Rcatsfilter_elapsed_disc"] = filter_results_disc_r["cats_test_elapsed_time"]
                outputdata["Rcdwfilter_grade_disc"] = filter_results_disc_r["cdw_grade"]
                outputdata["Rcdwfilter_elapsed_disc"] = filter_results_disc_r["cdwfilter_test_elapsed_time"]
                outputdata["Rflaresfilter_grade_disc"] = filter_results_disc_r["flares_grade"]
                outputdata["Rflaresfilter_elapsed_disc"] = filter_results_disc_r["flaresfilter_test_elapsed_time"]
        finally:
            self.logger.debug('Exit processcheckimages')

    def processuploadimages(self, json, settings):
        self.logger.debug('Enter processuploadimages')
        try:
            self.logger.debug('Before numberofimages')
            numberofimages = json['numberofimages']
            self.logger.debug('After numberofimages')
            self.logger.debug('numberofimages: %s', numberofimages)
            failoniiq = False
            if 'failoniiq' in json:
                failoniiq = json['failoniiq']

            maculaImage_l = None
            maculaImage_r = None
            diskImage_l = None
            diskImage_r = None
            maculafilename_l = None
            maculafilename_r = None
            diskfilename_l = None
            diskfilename_r = None

            if numberofimages == 2:
                if 'maculaImage_l' not in json or 'maculaImage_r' not in json:
                    resp = jsonify({'errorcode': ErrorCodes.PROCESS_MUST_PASS_2_MACULA, 'message' : 'Must pass 2 macula images'})
                    return resp
                else:
                    maculaImage_l = json['maculaImage_l']
                    maculaImage_r = json['maculaImage_r']
                    maculafilename_l = json['maculafilename_l']
                    maculafilename_r = json['maculafilename_r']
                    if maculaImage_l == None and maculaImage_r == None:
                        resp = jsonify({'errorcode': ErrorCodes.PROCESS_AT_LEAST_ONE_IMAGE_NOT_NONE, 'message' : 'At least one image must not be none'})
                        return resp
                    elif (maculaImage_l != None and maculafilename_l == '') or (maculaImage_r != None and maculafilename_r == ''):
                        resp = jsonify({'errorcode': ErrorCodes.PROCESS_NO_NAME_FOR_IMAGE, 'message' : 'Image file must have a name'})
                        return resp
            elif numberofimages == 4:
                if 'maculaImage_l' not in json or 'maculaImage_r' not in json or 'diskImage_r' not in json or 'diskImage_l' not in json:
                    resp = jsonify({'errorcode': ErrorCodes.PROCESS_MUST_PASS_2_MACULA_2_DISC, 'message' : 'Must pass 2 macula images and two disk images'})
                    return resp
                else:
                    maculaImage_l = json['maculaImage_l']
                    maculaImage_r = json['maculaImage_r']
                    diskImage_l = json['diskImage_l']
                    diskImage_r = json['diskImage_r']
                    maculafilename_l = json['maculafilename_l']
                    maculafilename_r = json['maculafilename_r']
                    diskfilename_l = json['diskfilename_l']
                    diskfilename_r = json['diskfilename_r']
                    #if (maculaImage_l == None and maculaImage_r == None) or (diskImage_l == None and diskImage_r == None):
                    #    resp = jsonify({'errorcode': ErrorCodes.PROCESS_AT_LEAST_ONE_IMAGE_NOT_NONE, 'message' : 'At least one image must not be none'})
                    #    return resp
                    if (maculaImage_l != None and maculafilename_l == '') or (maculaImage_r != None and maculafilename_r == '') or (diskImage_l != None and diskfilename_l == '') or (diskImage_r != None and diskfilename_r == ''):
                        resp = jsonify({'errorcode': ErrorCodes.PROCESS_NO_NAME_FOR_IMAGE, 'message' : 'Image file must have a name'})
                        return resp
            else:
                resp = jsonify({'errorcode': ErrorCodes.PROCESS_MUST_PASS_2_OR_4_IMAGES, 'message' : 'Must pass 2 or 4 images'})
                return resp

            uploadedSucc = False
            diskfilenamesave_r = None
            diskfilenamesave_l = None
            maculafilenamesave_r = None
            maculafilenamesave_l = None
            maculaImage_r_image = None
            maculaImage_l_image = None
            diskImage_r_image = None
            diskImage_l_image = None

            tempfolder = settings.get('temp_folder')

            parentDir = tempfolder
            self.logger.debug('parentDir: ' + parentDir)

            #parentDir = "c:\\temp\\qq"
            if maculaImage_r and allowed_file(maculafilename_r):
                filename = secure_filename(maculafilename_r)
                maculafilenamesave_r = os.path.join(parentDir, filename);
                maculaImage_r_bytes = maculaImage_r.encode('utf-8')
                maculaImage_r_image = base64.b64decode(maculaImage_r_bytes)
            elif maculaImage_r:
                resp = jsonify({'errorcode': ErrorCodes.PROCESS_IMAGE_FILE_TYPE_NOT_ALLOWED, 'message' : 'Allowed file types are png, jpg, jpeg, gif for file: ' + maculafilename_r})
                return resp

            if maculaImage_l and allowed_file(maculafilename_l):
                filename = secure_filename(maculafilename_l)
                maculafilenamesave_l = os.path.join(parentDir, filename);
                maculaImage_l_bytes = maculaImage_l.encode('utf-8')
                maculaImage_l_image = base64.b64decode(maculaImage_l_bytes)
            elif maculaImage_l:
                resp = jsonify({'errorcode': ErrorCodes.PROCESS_IMAGE_FILE_TYPE_NOT_ALLOWED, 'message' : 'Allowed file types are png, jpg, jpeg, gif for file: ' + maculafilename_l})
                return resp

            if diskImage_r and allowed_file(diskfilename_r):
                filename = secure_filename(diskfilename_r)
                diskfilenamesave_r = os.path.join(parentDir, filename);
                diskImage_r_bytes = diskImage_r.encode('utf-8')
                diskImage_r_image = base64.b64decode(diskImage_r_bytes)
            elif diskImage_r:
                resp = jsonify({'errorcode': ErrorCodes.PROCESS_IMAGE_FILE_TYPE_NOT_ALLOWED, 'message' : 'Allowed file types are png, jpg, jpeg, gif for file: ' + diskfilename_r})
                return resp

            if diskImage_l and allowed_file(diskfilename_l):
                filename = secure_filename(diskfilename_l)
                diskfilenamesave_l = os.path.join(parentDir, filename);
                diskImage_l_bytes = diskImage_l.encode('utf-8')
                diskImage_l_image = base64.b64decode(diskImage_l_bytes)
            elif diskImage_l:
                resp = jsonify({'errorcode': ErrorCodes.PROCESS_IMAGE_FILE_TYPE_NOT_ALLOWED, 'message' : 'Allowed file types are png, jpg, jpeg, gif for file: ' + diskfilename_l})
                return resp

            self.logger.debug('Before saveImages')
            uploadedSucc = self.saveImages(diskfilenamesave_r, diskfilenamesave_l, maculafilenamesave_r, maculafilenamesave_l, maculaImage_r_image, maculaImage_l_image, diskImage_r_image, diskImage_l_image)
            self.logger.debug('After saveImages')
            if uploadedSucc == True:
                resp = jsonify({'errorcode': ErrorCodes.PROCESS_OK, 'failoniiq': failoniiq, 'numberofimages': numberofimages, 'diskfullfilename_l':diskfilenamesave_l, 'diskfullfilename_r':diskfilenamesave_r, 'maculafullfilename_l':maculafilenamesave_l, 'maculafullfilename_r':maculafilenamesave_r, 'message' : 'File successfully uploaded'})
                return resp
            else:
                resp = jsonify({'errorcode': ErrorCodes.PROCESS_FAIL_TO_UPLOAD_FILES, 'message' : 'Failed to upload files'})
                return resp

        except:
            self.logger.debug('Failed to upload images with Exception')
            resp = jsonify({'errorcode': ErrorCodes.PROCESS_FAIL_TO_UPLOAD_FILES, 'message' : 'Failed to upload files'})
            return resp

        finally:
            self.logger.debug('Leave processuploadimages')

    def saveImages(self, diskfilename_r, diskfilename_l, maculafilename_r, maculafilename_l, maculaImage_r_image, maculaImage_l_image, diskImage_r_image, diskImage_l_image):
        self.logger.debug('Enter saveImages')
        fml = None
        fmr = None
        fdl = None
        fdr = None
        try:
            if maculaImage_r_image != None:
                fmr = open(maculafilename_r, 'wb')
                fmr.write(maculaImage_r_image)
                fmr.close()
                fmr = None

            if maculaImage_l_image != None:
                fml = open(maculafilename_l, 'wb')
                fml.write(maculaImage_l_image)
                fml.close()
                fml = None

            if diskImage_r_image != None:
                fdr = open(diskfilename_r, 'wb')
                fdr.write(diskImage_r_image)
                fdr.close()
                fdr = None

            if diskImage_l_image != None:
                fdl = open(diskfilename_l, 'wb')
                fdl.write(diskImage_l_image)
                fdl.close()
                fdl = None

            self.logger.debug('Got files to upload: maculaImage_l-%s maculaImage_r-%s diskImage_l-%s diskImage_r-%s', maculafilename_l, maculafilename_r, diskfilename_l, diskfilename_r)
        except IOError as e:
            print ("I/O error({0}): {1}".format(e.errno, e.strerror))
        except:
            self.logger.debug('Failed to save image with an Exception')
            return False

        finally:
            if fml:
                fml.close()
            if fmr:
                fmr.close()
            if fdl:
                fdl.close()
            if fdr:
                fdr.close()
            self.logger.debug('Leave saveImages')

        return True

    def setconfiguration(self, json):
        self.logger.debug('Enter setconfiguration')
        try:
            resp = jsonify({'errorcode': ErrorCodes.PROCESS_OK})
            return resp

        except:
            self.logger.debug('Failed to set configuration')
            resp = jsonify({'errorcode': ErrorCodes.PROCESS_FAIL_TO_SET_CONFIGURATION, 'message' : 'Failed to set configutastion'})
            return resp

        finally:
            self.logger.debug('Leave setconfiguration')

    def getconfiguration(self):
        self.logger.debug('Enter getconfiguration')
        try:
            with open("./version.yaml", "r") as f:
                version = yaml.load(f)
                major = version['major']
                minor = version['minor']
                patch = version['patch']
                build = version['build']
            with open("./config.yaml", "r") as f:
                config = yaml.load(f)
                GPU = config['GPU']
                encrypted_model = config['encrypted_model']
                model = config['model']

            respDict = {'major': major, 'minor': minor, 'patch': patch, 'build': build, 'GPU': GPU, 'model': model, 'encrypted_model': encrypted_model, 'errorcode': ErrorCodes.PROCESS_OK}
            resp = jsonify(respDict)
            return resp
        except:
            self.logger.debug('Failed to get configuration')
            resp = jsonify({'errorcode': ErrorCodes.PROCESS_FAIL_TO_GET_CONFIGURATION, 'message' : 'Failed to get configutastion'})
            return resp

        finally:
            self.logger.debug('Leave getconfiguration')

    def test(self):
        NNMainServer = NNMainServer()
        outputdata = NNMainServer.processcheckimages(2, None, None, "1.jpg", "2.jpg", True, settings = None)
        print("-----------------------------------------------------")
        print(outputdata)
        print("-----------------------------------------------------")
        outputdata = NNMainServer.processcheckimages(4, "3.jpg", "4.jpg", "1.jpg", "2.jpg", True, settings = None)
        print("-----------------------------------------------------")
        print(outputdata)
        print("-----------------------------------------------------")
