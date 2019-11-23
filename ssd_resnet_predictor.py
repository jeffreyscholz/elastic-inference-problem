from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import numpy as np
import tensorflow as tf
import matplotlib.image as mpimg
from tensorflow.contrib.ei.python.predictor.ei_predictor import EIPredictor

tf.app.flags.DEFINE_string('image', '', 'path to image in JPEG format')
FLAGS = tf.app.flags.FLAGS

coco_classes_txt = "https://raw.githubusercontent.com/amikelive/coco-labels/master/coco-labels-paper.txt"
local_coco_classes_txt = "coco-labels-paper.txt"
# it's a file like object and works just like a file
os.system("curl -o %s -O %s"%(local_coco_classes_txt, coco_classes_txt))
NUM_PREDICTIONS = 5
with open(local_coco_classes_txt) as f:
  classes = ["No Class"] + [line.strip() for line in f.readlines()]


def get_output(eia_predictor, test_input):
  pred = None
  for curpred in range(NUM_PREDICTIONS):
    pred = eia_predictor(test_input)

  num_detections = int(pred["num_detections"])
  print("%d detection[s]" % (num_detections))
  detection_classes = pred["detection_classes"][0][:num_detections]
  print([classes[int(i)] for i in detection_classes])


def main(_):

  img = mpimg.imread(FLAGS.image)
  img = np.expand_dims(img, axis=0)
  ssd_resnet_input = {'inputs': img}

  print('Running SSD Resnet on EIPredictor using specified input and outputs')
  eia_predictor = EIPredictor(
      model_dir='ssd_resnet50_v1_coco/1/',
      input_names={"inputs": "image_tensor:0"},
      output_names={"detection_classes": "detection_classes:0", "num_detections": "num_detections:0",
                    "detection_boxes": "detection_boxes:0"},
  )
  get_output(eia_predictor, ssd_resnet_input)

  print('Running SSD Resnet on EIPredictor using default Signature Def')
  eia_predictor = EIPredictor(
      model_dir='ssd_resnet50_v1_coco/1/',
  )
  get_output(eia_predictor, ssd_resnet_input)


if __name__ == "__main__":
  tf.app.run()
