#include "I2Cdev.h"
#include "MPU6050_6Axis_MotionApps612.h"
#include "MPU6050.h"
#include "Wire.h"
#include <EEPROM.h>


/*function prototype*/
void EEPROM_int16_write_handle(int8_t addr, int16_t num);
int16_t EEPROM_int16_read_handle(int8_t addr);
int16_t MPU6050_Auto_Calibaration(int16_t * , int16_t * ,int16_t *,int16_t * , int16_t * ,int16_t *);
void de_calibration();


#define LED_PIN 13

bool blinkState = false;
// MPU control/status vars
bool dmpReady = false;  // set true if DMP init was successful
uint8_t devStatus;      // return status after each device operation (0 = success, !0 = error)
uint16_t packetSize;    // expected DMP packet size (default is 42 bytes)
uint16_t fifoCount;     // count of all bytes currently in FIFO
uint8_t fifoBuffer[64]; // FIFO storage buffer

// orientation/motion vars
Quaternion q;           // [w, x, y, z]         quaternion container
VectorFloat gravity;    // [x, y, z]            gravity vector
float ypr[3];           // [yaw, pitch, roll]   yaw/pitch/roll container and gravity vector
VectorInt16 accles;
VectorInt16 accles_raw;
VectorInt16 accles_subtract_g;


MPU6050 mpu;

int16_t g_offset[3] = {0};
int16_t a_offset[3] = {0};


void setup() {
  Wire.begin();
  Wire.setClock(400000); // 400kHz I2C clock.
  
  Serial.begin(38400);


  Serial.println(F("Initializing I2C devices..."));

  mpu.initialize();
  /*verify connection*/
  Serial.println(F("Testing device connections..."));
  Serial.println(mpu.testConnection() ? F("MPU6050 connection successful") : F("MPU6050 connection failed"));

  /*load and configure the DMP*/
  Serial.println(F("Initializing DMP..."));
  devStatus = mpu.dmpInitialize();

  /*set the sensensing range for Accel to be +-16g */
  //mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_16);

    /*Auto Calibration*/
    //de_calibration(); //uncomments this if  want to recalibrate
    if(MPU6050_Auto_Calibaration(&g_offset[0],&g_offset[1],&g_offset[2],&a_offset[0],&a_offset[1],&a_offset[2]) == -1){
        Serial.println("Caliberation fail");
        while(1);
    }else{
        Serial.println("Caliberation successful");
    }

  /*read the calibration offset from eeprom*/
  mpu.setXGyroOffset(g_offset[0]);
  mpu.setYGyroOffset(g_offset[1]);
  mpu.setZGyroOffset(g_offset[2]);
  mpu.setXAccelOffset(a_offset[0]);
  mpu.setYAccelOffset(a_offset[1]);
  mpu.setZAccelOffset(a_offset[2]);

  if (devStatus == 0) {
    mpu.CalibrateAccel(6);
    mpu.CalibrateGyro(6);
    Serial.println();
    mpu.PrintActiveOffsets();
    // turn on the DMP, now that it's ready
    Serial.println(F("Enabling DMP..."));
    mpu.setDMPEnabled(true);
    dmpReady = true;
    packetSize = mpu.dmpGetFIFOPacketSize();

    /*
    Digital low pass filter mode = 1 => Sampling rate = 1KHz Period = 0.001sec
    Sample Rate = Gyroscope Output Rate / (1 + SMPLRT_DIV)  = 1kHz / (1 + 400Hz) = 2.49 Hz  : 
     T = 0.4s
    Serial.println(mpu.getDLPFMode()); 
    */

  } else {
    // ERROR!
    // 1 = initial memory load failed
    // 2 = DMP configuration updates failed
    // (if it's going to break, usually the code will be 1)
    Serial.print(F("DMP Initialization failed (code "));
    Serial.print(devStatus);
    Serial.println(F(")"));
  }

  pinMode(LED_PIN, OUTPUT);
}


void loop() {

  if (!dmpReady) return;

  if (mpu.dmpGetCurrentFIFOPacket(fifoBuffer)) { 
    // //get Euler angles in degrees 
    mpu.dmpGetQuaternion(&q, fifoBuffer);
    mpu.dmpGetGravity(&gravity, &q);
    mpu.dmpGetYawPitchRoll(ypr, &q, &gravity);


    Serial.print(ypr[0] * 180 / M_PI);Serial.print(",");
    Serial.print(ypr[1] * 180 / M_PI);Serial.print(",");
    Serial.print(ypr[2] * 180 / M_PI); 
    Serial.println("");


    // blink LED to indicate activity 
    blinkState = !blinkState;
    digitalWrite(LED_PIN, blinkState);

  }
}



int16_t MPU6050_Auto_Calibaration(int16_t * p_offsetgX, int16_t * p_offsetgY,int16_t * p_offsetgZ,
                                  int16_t * p_offsetaX, int16_t * p_offsetaY,int16_t * p_offsetaZ){
    /*Mega has the EEPROM from 0 to 4k, 
    reserve the first 1+3*2 = 7 bytes to store calibaration 
    offset for gyro reading */

    /*
    | byte 0-1 | byte 2-3 | byte 4-5   | byte 6-7|
    | Gx os    | Gy os    | Gz os      | flag    |
    | byte 8-9 | byte 10-11 | byte 11-12 |
    | ax os    | ay os    | az os        |

    flag = 0x46 = 'F'
    flag = 0x54 = 'T'
    */
    if(EEPROM_int16_read_handle(0x06) == 0x46){
        /* calibaration parameters are invalid*/
        for(int i = 20; i >0; i=i-10){

            Serial.print("Calibration will start in ");
            Serial.print(i); Serial.println("s");
            Serial.println("Please adjust MPU to horizontal rest.");
            Serial.println("*************************************");
            delay(10000);//wait 10 sec.
        }
        Serial.println("***************Calibration starts*******************");
        
        int cali_times = 30;
        int16_t offsetgX,offsetgY,offsetgZ,offsetaX,offsetaY,offsetaZ;
        int16_t gx,gy,gz,ax,ay,az;
        for(int i = 0; i < cali_times; i++){
            mpu.getRotation(&gx,&gy,&gz);
            offsetgX += gx;
            offsetgY += gy;
            offsetgZ += gz;

            mpu.getAcceleration(&ax,&ay,&az);
            offsetaX += ax;
            offsetaY += ay;
            offsetaZ += az;
        }

        offsetaX /= cali_times;
        offsetaY /= cali_times;
        offsetaZ /= cali_times;
        offsetgX /= cali_times;
        offsetgY /= cali_times;
        offsetgZ /= cali_times;

        
 
        Serial.print("Gyro X offset: ");Serial.println(offsetgX);
        Serial.print("Gyro Y offset: ");Serial.println(offsetgY);
        Serial.print("Gyro Z offset: ");Serial.println(offsetgZ);

        Serial.print("accel X offset: ");Serial.println(offsetaX);
        Serial.print("accel Y offset: ");Serial.println(offsetaY);
        Serial.print("accel Z offset: ");Serial.println(offsetaZ);


        EEPROM_int16_write_handle(0,offsetgX); //write to Gx
        EEPROM_int16_write_handle(2,offsetgY); //write to Gy
        EEPROM_int16_write_handle(4,offsetgZ); //write to Gz
        EEPROM_int16_write_handle(6,0x54); //write to flag
        EEPROM_int16_write_handle(8,offsetaX);
        EEPROM_int16_write_handle(10,offsetaY);
        EEPROM_int16_write_handle(12,offsetaZ);

        *p_offsetgX = offsetgX;
        *p_offsetgY = offsetgY;
        *p_offsetgZ = offsetgZ;

        *p_offsetaX = offsetaX;
        *p_offsetaY = offsetaY;
        *p_offsetaZ = offsetaZ;

        Serial.println("***************Calibration Finishes*****************");

        return 0;
        
    }else if(EEPROM_int16_read_handle(0x06) == 0x54){
    
        *p_offsetgX = EEPROM_int16_read_handle(0);
        *p_offsetgY = EEPROM_int16_read_handle(2);
        *p_offsetgZ = EEPROM_int16_read_handle(4);
        *p_offsetaX = EEPROM_int16_read_handle(8);
        *p_offsetaY = EEPROM_int16_read_handle(10);
        *p_offsetaZ = EEPROM_int16_read_handle(12);

        return 0;
    }

    Serial.println("Calibration issues....");
    return -1;
}

void de_calibration(){
    EEPROM_int16_write_handle(0x06,0x46);
}

void EEPROM_int16_write_handle(int8_t addr, int16_t num){
    EEPROM.write(addr, num >> 8);
    EEPROM.write(addr+1, num & 0xFF);
}

int16_t EEPROM_int16_read_handle(int8_t addr){
    byte b1 = EEPROM.read(addr);
    byte b2 = EEPROM.read(addr+1);
    return (b1 << 8) + b2;
}

