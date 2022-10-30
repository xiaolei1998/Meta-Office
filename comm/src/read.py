from time import sleep
from tkinter import Y
import serial
import io
import numpy as np
import sys
import signal
import socket
import math
import threading
from threading import *  
from queue import Queue
#$ pip3 install filterpy
from filterpy.kalman import KalmanFilter




Data = serial.Serial()
Data.baudrate = 57600
#ls /dev/tty.usb*  to show the connected usb device on MAC
# Data.port = '/dev/cu.usbserial-14220'
Data.port = '/dev/tty.usbserial-1430'

#Data.port = 'COM3'
Data.timeout = 0.01
Data.open()


a_lsb = 16384


#sampling period for MPU -> actually delta_t
# Digital low pass filter mode = 1 => Sampling rate = 1KHz Period = 0.001sec
# Sample Rate = Gyroscope Output Rate / (1 + SMPLRT_DIV)  = 1kHz / (1 + 400Hz) = 2.49 Hz  :  T = 0.4s
sample_period = 0.4


#define the initial velocity, suppose at the begining, MPU is stationary
v_x = 0
v_y = 0
v_z = 0
velos = [0,0,0]

#hold the data for upcoming angle -> it is shared memory between threads, need mutex lock
queue_size = 3000
V_queue = Queue(maxsize = queue_size)

#lock and semaphore for thread communication
lock = threading.Lock()
full  = Semaphore(0)
empty = Semaphore(queue_size)


sio = io.TextIOWrapper(io.BufferedRWPair(Data,Data,1),encoding='ascii',newline = '\r')



"""
get data from serial port(arduino side)
"""
def get_real_velocity():

    global velos
    
    ypr  = []

    signal = sio.readline()
    rowdata = signal
    rowdata = rowdata.strip('\n')
    rowdata = rowdata.strip('\r')
    xyz = rowdata.split(",")

    #check the length of the array to avoid transimission glitch 
    if(len(xyz) !=3 ):
        return [0,0,0]
    else:
        try:
            temp_ypr  = []

            for i in range(3):
                temp_ypr.append(float(xyz[i]))

            ypr  = temp_ypr
            #print(ypr)


            # correlate the angles with velocity
            pitch = ypr[1]
            roll = ypr[2]

            velocity = [0,0]

            if(pitch > 25 and pitch <= 30 ):
                velocity[0] = 1
            elif(pitch > 30 and pitch <=50):
                velocity[0] = 2
            elif(pitch > 50 and pitch <= 90):
                velocity[0] = 3
            elif(pitch < -10 and pitch >= -30 ):
                velocity[0] = -1
            elif(pitch < -30 and pitch >= -50):
                velocity[0] = -2
            elif(pitch < -50 and pitch >= -90):
                velocity[0] = 3
            else:
                velocity[0] = 0

            if(roll > 25 and roll  <= 30 ):
                velocity[1] = 1
            elif(roll > 30 and roll <=50):
                velocity[1] = 2
            elif(roll > 50 and roll <= 90):
                velocity[1] = 3
            elif(roll < -10 and roll >= -30 ):
                velocity[1] = -1
            elif(roll < -30 and roll >= -50):
                velocity[1] = -2
            elif(roll < -50 and roll >= -90):
                velocity[1] = 3
            else:
                velocity[1] = 0

            #print(velocity)

            return velocity
            
        except ValueError:
            return [0,0,0]
        


"""
serialize the input data for Socket
"""  
def serialization_enQueue(velocity):
    global V_queue
    s = str(velocity[0]) + ',' + str(velocity[1]) + ',0'
    # print(s)
    V_queue.put(s);

    
"""
Signal handler -> catch the control c; elegently close the socket
"""
def handler(signum, frame):
    global conn,t1
    print("catched sigint, close socket...")
    conn.sendall("quit".encode())
    conn.close()
    sleep(2) #wait socket to settle down
    sys.exit(0)


"""
Thread for TCP server
"""
def TCPip_socket_server():

    global V_queue, lock
    
    #loop back address 127.0.0.1
    HOST = "127.0.0.1"
    PORT = 8000


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


def main():

    global V_queue,lock,t1

    signal.signal(signal.SIGINT, handler) #set up SIGINT handler to catch control-c to elegently quit

    t1 = threading.Thread(target=TCPip_socket_server) # launch the TCP server to communicate with client
    t1.daemon = True #set t1 as deamon process  -> die with main process together 
    t1.start() #lauch the thread


    while(True):

        velocity = get_real_velocity() #read the data from arduino

        #producer consumer -> produce a message and let consumer(Thread) to sent
        empty.acquire()
        lock.acquire()#mutex protect shared memory 
        serialization_enQueue(velocity)
        lock.release()#mutex protect shared memory 
        full.release()

        #sleep(1)


            
if __name__ == "__main__":
    main()