import directions
import drivetrain_controls
import arm_controls
import wheelPair
import drivetrain_controls
import turntable
import communications

from jetson-inference.python.examples import detection_camera

print ("imports complete")

objectPickedUp = False

def grabObject():
	return objectPickedUp

def calculateRotationAngle(distInches, turntable):
	return (float)(distInches)/(turntable.tableRadius) * 360

def main():
	
	# HERE - set up communication with Arduino DUE

	# HERE - use list of motors to begin instantiating objects (wheelPairs, turntable, arm, etc.)

	while (not objectPickedUp):
		toMove = detection_camera.main()
		
		#toMove = (100, -52)
		
		if (toMove == None):
			print ("error - check detection_camera.py program")
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
			rotateAmt = calculateRotationAngle(directions.getDistance(pixelsHorizontal)) # fill in the blank here for calculations of degrees to rotate
			
			direction1 = directions(horizontalDirection, rotate, pixelsHorizontal, rotateAmt)
			
			drivetrain_controls.driveToLocation(direction1)
			
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
			
		objectPickedUp = grabObject()

main()
