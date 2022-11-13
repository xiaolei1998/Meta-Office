from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2 import model_zoo
import numpy as np

import cv2
from time import sleep
import sys
import signal

import numpy as np
import sys
import signal
import socket
import threading
from threading import *  
from queue import Queue
import json


import os


"""
get dependent package and lib:


1. $ brew install opencv
2. $ pip3 install opencv-python



detectron wiki: https://detectron2.readthedocs.io/en/latest/tutorials/install.html 

    enviroment setup 
1. download pytorch and torchvision from https://pytorch.org/
2. download detectron from 
    $ python -m pip install 'git+https://github.com/facebookresearch/detectron2.git' --user

    my enviroment:  
python                    3.9.13               hdfd78df_2
pytorch                   1.13.0                  py3.9_0    pytorch(newest from official web)
"""


#hold the data for upcoming angle -> it is shared memory between threads, need mutex lock
queue_size = 3000
V_queue = Queue(maxsize = queue_size)

#lock and semaphore for thread communication
lock = threading.Lock()
full  = Semaphore(0)
empty = Semaphore(queue_size)


#fork two process one for camera image capture, one for fastRCNN
pid = os.fork()



def handler(signum, frame):
    print("forced shut down")
    sys.exit(0)


#pressing control-c to force shut down cam
signal.signal(signal.SIGINT, handler)


def TCPip_socket_server():

    global V_queue, lock
    
    #loop back address 127.0.0.1
    HOST = "127.0.0.1"
    PORT = 8003


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))  #bind the port and ip with socket 
        s.listen() # start listen
    
        global conn 
        conn,addr = s.accept() #accept connection and put to connected queue

        with conn: #process the connected socket 
            print("Unity 3D is connected\n")

            while True:

                if(False == V_queue.empty()):

                    #producer and consumer arichtecture -> consume a message
                    # get the produced string
                    full.acquire()
                    lock.acquire() #mutex protect shared memory 

                    tcp_packet = V_queue.get() 
                    # print(tcp_packet)

                    lock.release() #mutex protect shared memory 
                    empty.release()   

                    # conn.sendall(tcp_packet.encode()) # send to the client(unity 3d)
                    conn.send(tcp_packet.encode()) # send to the client(unity 3d)



if pid > 0:
    #Parent Process
    cam = cv2.VideoCapture(0)

    while(True):
        #acquisit real-time images
        captured, image = cam.read()

        if captured:
            #save the input to local path
            cv2.imwrite("/Users/Michelle/Desktop/CEG5205/project/meta/visualPerception/input_img.jpg", image)

        sleep(3)

else:
    #child process 

    #multithreading for tcp-communication
    t1 = threading.Thread(target=TCPip_socket_server) # launch the TCP server to communicate with client
    t1.daemon = True #set t1 as deamon process  -> die with main process together 
    t1.start() #lauch the thread


    while(True):

        cfg1 = get_cfg()

        cfg1.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml")) #backbone is using R50 FPN

        cfg1.MODEL.DEVICE = "cpu"

        cfg1.MODEL.ROI_HEADS.NUM_CLASSES = 5    #number of classes + 1, we have 4 classes apple;banana;mug;bottle

        cfg1.MODEL.WEIGHTS = "/Users/Michelle/Desktop/CEG5205/project/meta/visualPerception/model_final.pth"  #point to local weight file 
        # cfg1.MODEL.WEIGHTS = "model_final.pth"  #point to local weight file 

        cfg1.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7 

        predictor = DefaultPredictor(cfg1)

        im = cv2.imread("/Users/Michelle/Desktop/CEG5205/project/meta/visualPerception/input_img.jpg")
        outputs = predictor(im)


        empty.acquire()
        lock.acquire()#mutex protect shared memory 
        V_queue.put(str(outputs))
        lock.release()#mutex protect shared memory 
        full.release()

        print(outputs)

        # print(type(outputs))

