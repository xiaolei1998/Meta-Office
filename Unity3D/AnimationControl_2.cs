using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System;
using System.Globalization;



public class AnimationControl : MonoBehaviour
{
    public Animator myAnimator;
    private static Mutex mutex_mpu; //define a lock, since the structure for this design is multi-threading 
    private static Queue<float[]> motions;
    private float[] velocity;

    private static Mutex mutex_rcnn;
    private static Queue<string> objsDetction;


    public GrabObject grab;

    private Rigidbody rd;
    private float m_Speed = 3f;



    // Start is called before the first frame update
    void Start(){
        Debug.Log("main");

        myAnimator = this.GetComponent<Animator>();
        mutex_mpu = new Mutex();
        mutex_rcnn = new Mutex();

        motions = new Queue <float[]>();
        velocity = new float[3];

        objsDetction = new Queue<string>();

        rd = GetComponent<Rigidbody>();

        //Set up MPU socket client 
        Thread thr = new Thread(startClientSocket_MPU);
        thr.Start();

        //Set up fast rcnn client client 
        Thread thr1 = new Thread(startClientSocket_FasterRCNN);
        thr1.Start();

    }


    // Update is called once per frame
    void Update()
    {
        /*RCNN projection logic here*/
        /*use helper function get_fasterRCNN to process*/
        ////////////////////////////////////////////////
        string obj = get_fasterRCNN();
        if(obj != null)
        {
            /*写decode obj */
            // number: Number of items, Type[i, 0]: what is it, Type[i, 1]: which zone to put (0-3)
            
            Debug.Log(obj);
            
            string[] reading = new string[30];
            int count = 0;
            string temp = "";
            foreach (char c in obj)
            {
                if ((c >= '0' && c <= '9') || c == '.')
                    temp = temp + c;
                else
                {
                    if (temp != "")
                        reading[count++] = temp;
                    temp = "";
                }
            }
            if (temp != "")
                reading[count++] = temp;
            int number = (count - 3) / 6;
            int[,] Type = new int[number, 2];
            double[,] Location = new double[number, 4];
            double[] image = {System.Convert.ToDouble(reading[1]), System.Convert.ToDouble(reading[2])};
            for (int i = 0; i < number; i++)
            {
                Location[i, 0] = System.Convert.ToDouble(reading[i * 4 + 3]);
                Location[i, 1] = System.Convert.ToDouble(reading[i * 4 + 4]);
                Location[i, 2] = System.Convert.ToDouble(reading[i * 4 + 5]);
                Location[i, 3] = System.Convert.ToDouble(reading[i * 4 + 6]);
                Type[i, 1] = 0;
                if (Location[i, 1] + Location[i, 3] > image[0])
                    Type[i, 1] += 2;
                if (Location[i, 0] + Location[i, 2] > image[0])
                    Type[i, 1] += 1;
                Type[i, 0] = int.Parse(reading[count - number + i]);
            }
            /*如果图像里有两个监测到的物体 就是这样的 
            {'instances': Instances(num_instances=2, image_height=1707, image_width=1280, fields=[pred_boxes: Boxes(tensor([[ 736.8550,  160.0862, 1094.8132, 1412.2230],
            [ 294.6116,  605.9538,  600.7311,  925.4279]])), scores: tensor([0.9804, 0.9376]), pred_classes: tensor([3, 1])])}*/
        }

        
        /*MPU control logic here*/
        if(motions.Count != 0){
            mutex_mpu.WaitOne();
            velocity = motions.Dequeue();
            mutex_mpu.ReleaseMutex();

            float forward_back = velocity[0]; //controlled by pitch
            float left_right   = velocity[1]; //controlled by roll
            float up_down   = 0;

            if (Input.GetKey(KeyCode.S)){
                up_down = -1;
            }
            
            if (Input.GetKey(KeyCode.W)){
                up_down = 1;
            }

            /* in the format of [left/right,up/down,forward/back]*/
            Vector3 m_Input = new Vector3(left_right, up_down, forward_back);
            // Debug.Log(left_right);
            
            
            this.transform.Translate(m_Input* Time.deltaTime);  

        }

    }

    /*
    TCP client starts here, behavior of the client is defined here
    */
    void startClientSocket_MPU(){

        Debug.Log("thread");

        /*initialize sockect */
        IPAddress ipAddr = IPAddress.Parse("127.0.0.1"); //loop back address since in same host
        IPEndPoint localEndPoint = new IPEndPoint(ipAddr, 8000); //define the port number
        //bind ip address and port address with socket 
        Socket sender = new Socket(ipAddr.AddressFamily,
                   SocketType.Stream, ProtocolType.Tcp);
        
        //connect to the server 
        sender.Connect(localEndPoint);


        //a buffer to keep data 
        byte[] messageReceive = new byte[1024];

        while(true){

            int byteRecv = sender.Receive(messageReceive);
            string s = Encoding.ASCII.GetString(messageReceive, 0, byteRecv);
            //Debug.Log(s);
            string_proc_MPU(s); //process the incoming data
            Array.Clear(messageReceive, 0, messageReceive.Length); //clear the buffer 
        }
    }


    void startClientSocket_FasterRCNN(){

        Debug.Log("thread_RCNN_Client");

        /*initialize sockect */
        IPAddress ipAddr = IPAddress.Parse("127.0.0.1"); //loop back address since in same host
        IPEndPoint localEndPoint = new IPEndPoint(ipAddr, 8003); //define the port number
        //bind ip address and port address with socket 
        Socket sender = new Socket(ipAddr.AddressFamily,
                   SocketType.Stream, ProtocolType.Tcp);
        
        //connect to the server 
        sender.Connect(localEndPoint);


        //a buffer to keep data 
        byte[] messageReceive = new byte[2048];

        while(true){

            int byteRecv = sender.Receive(messageReceive);
            string s = Encoding.ASCII.GetString(messageReceive, 0, byteRecv);
            Debug.Log(s);
            mutex_rcnn.WaitOne();
            objsDetction.Enqueue(s);
            mutex_rcnn.ReleaseMutex();
            Array.Clear(messageReceive, 0, messageReceive.Length); //clear the buffer 
        }
    }

    string get_fasterRCNN(){
        string tensors = null;

        if(objsDetction.Count != 0){
            mutex_rcnn.WaitOne();
            tensors = objsDetction.Dequeue();
            mutex_rcnn.ReleaseMutex();
        }

        return tensors;
    }

    void string_proc_MPU(String phrase){
        
        //when the data received it 'quit', hanging up all operation
        if(phrase.Equals("quit")){
            // block it self, stop injecting garbage to the system
            Debug.Log("Server disconnected.......");
            while(true);

        }

        string[] datas = phrase.Split(',');

        float[] numeric_data = new float[3];

        //incoming data is fragmented, discard 
        if(datas.Length != 3){
            // Debug.Log("bad frame size");
            return;
        }else{

            for(int i = 0; i<datas.Length; i++){
                try{
                    numeric_data[i] = float.Parse(datas[i], CultureInfo.InvariantCulture.NumberFormat);
                }catch (Exception e){
                    Debug.Log("bad frame cast");
                    //incoming data cannot parse to float, discard
                    return;
                }
            }

            mutex_mpu.WaitOne(); //mutex lock to protect common area
            //put the data to globaly shared memory, wait main thread to consume
            motions.Enqueue(numeric_data);
            mutex_mpu.ReleaseMutex();//mutex lock to protect common area
        }

    }
}