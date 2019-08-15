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

global toMove
toMove = None
global detection

def calcMvt (detection, screen_center):
	move_x = detection.Center[0] - screen_center[0]
	move_y = detection.Center[1] - screen_center[1]
	
	return (move_x, move_y)

def getDetection ():
	return detection

def getDirections ():
	return toMove

def main():
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

		# print the detections
		print("detected {:d} objects in image".format(len(detections)))

		for detection in detections:
			print(detection)
			print(net.GetClassDesc(detection.ClassID))
			
			print(detection.Center)
			screen_center = (640/2, 480/2)
			
			toMove = calcMvt (detection, screen_center)
			
			print((str)(toMove[0]) + " " + (str)(toMove[1]))

		# render the image
		display.RenderOnce(img, width, height)

		# update the title bar
		display.SetTitle("{:s} | Network {:.0f} FPS".format(opt.network, 1000.0 / net.GetNetworkTime()))

		# synchronize with the GPU
		if len(detections) > 0:
			jetson.utils.cudaDeviceSynchronize()

		# print out performance info
		net.PrintProfilerTimes()

# main()