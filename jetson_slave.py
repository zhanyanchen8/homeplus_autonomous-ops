#!/usr/bin/python
#
# Copyright (c) 2019, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
# https://rawgit.com/dusty-nv/jetson-inference/python/docs/html/python/jetson.inference.html

import jetson.inference
import jetson.utils
import argparse
import time
import serial

import sys
sys.path.append("/home/arl/Documents/homeplus_autonomous-ops/")
import communications as comms

from threading import Thread, Event
import threading

cameraEvent = threading.Event()
cameraEvent.clear()

controlsEvent = threading.Event()
controlsEvent.clear()

sendEvent = threading.Event()
sendEvent.clear()

global boxDim
boxDim = (0, 0)

global center
center = (-1, -1)

global classDesc
classDesc = ""

"""
STARTS UP OBJECT DETECTION MODULE FROM THE JETSON

Take in an <i>object</i> set and uses camera_detection to determine
if a particular objects has been found or not

More Information/Cloning GitHub Repository: https://github.com/dusty-nv/jetson-inference
"""
def camera_detection(objects):	
	
	while (not controlsEvent.isSet()):
		
		cameraEvent.set()
	
		# parse the command line
		parser = argparse.ArgumentParser(description="Locate objects in a live camera stream using an object detection DNN.", 
								   formatter_class=argparse.RawTextHelpFormatter, epilog=jetson.inference.detectNet.Usage())

		parser.add_argument("--network", type=str, default="ssd-mobilenet-v1", help="pre-trained model to load, see below for options")
		parser.add_argument("--threshold", type=float, default=0.5, help="minimum detection threshold to use")
		parser.add_argument("--camera", type=str, default="/dev/video0", help="index of the MIPI CSI camera to use (NULL for CSI camera 0)\nor for VL42 cameras the /dev/video node to use.\nby default, MIPI CSI camera 0 will be used.")
		parser.add_argument("--width", type=int, default=640, help="desired width of camera stream (default is 640 pixels)")
		parser.add_argument("--height", type=int, default=480, help="desired height of camera stream (default is 480 pixels)")

		opt, argv = parser.parse_known_args()

		# load the object detection network
		net = jetson.inference.detectNet(opt.network, argv, opt.threshold)

		# create the camera and display
		camera = jetson.utils.gstCamera(opt.width, opt.height, opt.camera)
		display = jetson.utils.glDisplay()

		# process frames until user exits
		
		while display.IsOpen():
			
			# capture the image
			img, width, height = camera.CaptureRGBA()

			# detect objects in the image (with overlay)
			detections = net.Detect(img, width, height)
			
			for detection in detections:
				#print(detection)
				print(net.GetClassDesc(detection.ClassID))
				
				if (net.GetClassDesc(detection.ClassID) in objects and detection.Confidence > 0.7):
					global center
					global boxDim
					global classDesc
					boxDim = (detection.Width, detection.Height)
					center = (detection.Center[0], detection.Center[1])
					classDesc = net.GetClassDesc(detection.ClassID)
					controlsEvent.set()
					cameraEvent.clear()
					time.sleep(1)
					
			# render the image
			display.RenderOnce(img, width, height)

			# update the title bar
			display.SetTitle("{:s} | Network {:.0f} FPS".format(opt.network, 1000.0 / net.GetNetworkTime()))

			# synchronize with the GPU
			if len(detections) > 0:
				jetson.utils.cudaDeviceSynchronize()

"""

read input from Arduino

"""
def readInput():
	with serial.Serial('/dev/ttyACM0', 9600, timeout=10) as ser:
		objects = ser.readline().decode('ASCII')
		return objects

def checkStatus():
	if (readInput() == "request"):
		sendEvent.set()

"""

to write data back to the Arduino

"""
def sendBack(writeBack):
	ser = serial.Serial('/dev/ttyACM0', 9600)
	ser.write(writeBack)
	sendEvent.clear()
	print (writeBack + "\nevent sent")
	
"""
MAIN METHOD USED TO OPERATE THE CONTROLS OF THE ROBOT

takes in string of objects to find from Arduino via Serial and 
returns to Arduino center, width, and height of detected bounding box
"""
def begin_detecting():
	
	# parse through string detailing objects to find, saving each in a set	
	toFind = set()
	# objects = readInput()
	objects="bottle,cup,"
	
	i = 0
	
	while (not (i == len(objects) - 1)):
		endIndex = objects.find(",", i)
		if (endIndex == -1):
			break
		print (objects[i:endIndex])
		toFind.add(objects[i:endIndex])
		i = endIndex + 1;	
	
	print ("end parsing, about to find")
	
	t1 = threading.Thread(target=camera_detection, args=(toFind,))
	t2 = threading.Thread(target=checkStatus, args=())
	t1.start()
	t2.start()
	
	while (not cameraEvent.isSet()):
		pass
		
	while (cameraEvent.isSet()):
		
		while (cameraEvent.isSet() and not controlsEvent.isSet()):
			pass
		
		if (controlsEvent.isSet()):
			global center
			global boxDim
			global classDesc
			
			# size and location
			print (center)
			print (boxDim)
			
			if (sendEvent.isSet()):
				#pass encoding via center of bounding box, width, height after 5 detections OR default values after 3 minutes
				writeBack = classDesc + ";" + (str)(center) + ";" + (str)(boxDim[0]) + ";" + (str)(boxDim[1]) + ";"
				sendBack(writeBack)
			
			controlsEvent.clear()
			cameraEvent.set()
			
	t2.join()
	t1.join()
	
begin_detecting()
	

