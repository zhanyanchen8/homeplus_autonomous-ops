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

import sys
sys.path.append("/home/arl/Documents/homeplus_autonomous-ops/")
import directions
import drivetrain_controls
import arm_controls
import wheel_pair
import turntable

from threading import Event
import threading

cameraEvent = threading.Event()
cameraEvent.clear()

controlsEvent = threading.Event()
controlsEvent.clear()

global toMove
toMove = (0,0)

wp1 = wheel_pair.wheel_pair(1, 3, 2)
wp2 = wheel_pair.wheel_pair(2, 4, 2)

"""
STARTS UP OBJECT DETECTOIN MODULE FROM THE JETSON
currently programmed to return values should the object detected be a bottle (class 44)
by resetting the value for toMove

threaded with main() to provide synchronous operation of both threads
and prevent any overloads of system memory on the Jetson

More Information/Cloning GitHub Repository: https://github.com/dusty-nv/jetson-inference
"""
def camera_detection():
	
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
				print(detection)
				
				print(detection.Center)
				screen_center = (640/2, 480/2)
				
				# determine and change toMove value if bottle (ClassID 44) is found
				if (detection.ClassID == 44 and detection.Confidence > 0.6):
					global toMove
					toMove = (detection.Center[0] - screen_center[0], detection.Center[1] - screen_center[1])		
			
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

t1 = threading.Thread(target=camera_detection, args=())


# DISREGARD TWO FUNCTIONS BELOW - WERE USED FOR TESTING PURPOSES
"""
def calculateRotationAngle(distInches, turntable):
	return (float)(distInches)/(turntable.tableRadius) * 360

def getDistance(px):
	distanceAway = 5 # get distance sensor data from camera, convert to inches as necessary
	pixelsPerInch = ((float)(640))/distanceAway
	distanceToMove = px/pixelsPerInch
		
	return distanceToMove
"""
#

"""
MAIN METHOD USED TO OPERATE THE CONTROLS OF THE ROBOT

uses determined values to move from camera_detection() to send to
Arduino via respective objects and R2 communication protocol
"""
def main():
	
	# integrate nunchuk movement here
	# wait for confirmation from Arduino that procedure complete
	
	objectPickedUp = False
	
	t1.start()
	
	while (not cameraEvent.isSet()):
		pass
		
	while (cameraEvent.isSet()):
		
		while (cameraEvent.isSet() and not controlsEvent.isSet()):
			pass
		
		if (controlsEvent.isSet()):
			
			global toMove
			
			if (toMove == None):                                                             
				break
			
			else: 
				
				# horizontal movement using the drivetrain
				horizontalDirection = ""
				rotateDirection = ""
				if (toMove[0] < 0):
					horizontalDirection = "LEFT"
					rotateDirection = "LEFT"
				else:
					horizontalDirection = "RIGHT"
					rotateDirection = "RIGHT"
				
				pixelsHorizontal = abs(toMove[0])
				
				rotateAmt = 0
				direction1 = directions.Directions(horizontalDirection, rotateDirection, pixelsHorizontal, rotateAmt)
				
				drivetrain_controls.driveToLocation(wp1, wp2, direction1)
				
				"""
				# integrate movements together through concurrency
				# manipulate arm
				verticalDirection = ""
				if (toMove[1] < 0):
					verticalDirection = "UP"
				else:
					verticalDirection = "DOWN"
				
				pixelsVertical = abs(toMove[1])
				
				directions2 = directions(verticalDirection, rotate, pixelsVertical)
				
				arm_controls.levelClaw()
				arm_controls.moveToCenter(directions2)
				"""
				
				objectPickedUp = False
			
			controlsEvent.clear()
			cameraEvent.set()
			
	t1.join()

main()
