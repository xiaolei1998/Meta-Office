import cv2
from time import sleep
import sys
import signal

"""
get dependent package and lib:
1. $ brew install opencv
2. $ pip3 install opencv-python
"""

def handler(signum, frame):
    print("forced shut down")
    sys.exit(0)
#pressing control-c to force shut down cam
signal.signal(signal.SIGINT, handler)

#setting up the camera port
cam = cv2.VideoCapture(0)

while(True):
    #acquisit real-time images
    captured, image = cam.read()

    if captured:
        #save the input to local path
        cv2.imwrite("input_img.png", image)

    sleep(5)


