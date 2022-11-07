import cv2
import numpy as np

from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2 import model_zoo

"""
detectron wiki: https://detectron2.readthedocs.io/en/latest/tutorials/install.html 

    enviroment setup 
1. download pytorch and torchvision from https://pytorch.org/
2. download detectron from 
    $ python -m pip install 'git+https://github.com/facebookresearch/detectron2.git' --user

    my enviroment:  
python                    3.9.13               hdfd78df_2
pytorch                   1.13.0                  py3.9_0    pytorch(newest from official web)
"""


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
print(outputs)