Run the dockerfile locally on an EC2 machine (it must be set up with Elastic Inference already) first

download the tensorflow model 

```bash
curl -O https://s3-us-west-2.amazonaws.com/aws-tf-serving-ei-example/ssd_resnet.zip
unzip ssd_resnet.zip -d .
```


```bash
DOCKER_BUILDKIT=1 docker build . -t ei-hello
docker run -it ei-hello
```

The docker file runs `run.sh` which runs the EIValidation check (this script was taken from the Amazon Deep Learning AMI) and then runs the 3dogs example from the AWS documentation.

Expected output is as follows:

```
All the validation checks passed for Amazon EI from this instance - i-xxxxxxxxxxxxxxxxx
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:526: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
  _np_qint8 = np.dtype([("qint8", np.int8, 1)])
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:527: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
  _np_quint8 = np.dtype([("quint8", np.uint8, 1)])
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:528: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
  _np_qint16 = np.dtype([("qint16", np.int16, 1)])
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:529: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
  _np_quint16 = np.dtype([("quint16", np.uint16, 1)])
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:530: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
  _np_qint32 = np.dtype([("qint32", np.int32, 1)])
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:535: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
  np_resource = np.dtype([("resource", np.ubyte, 1)])
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   702  100   702    0     0   3378      0 --:--:-- --:--:-- --:--:--  3391
Running SSD Resnet on EIPredictor using specified input and outputs
2019-11-22 23:34:29.794091: I tensorflow/core/platform/profile_utils/cpu_utils.cc:94] CPU Frequency: 2900100000 Hz
2019-11-22 23:34:29.794326: I tensorflow/compiler/xla/service/service.cc:150] XLA service 0x408a8c0 executing computations on platform Host. Devices:
2019-11-22 23:34:29.794357: I tensorflow/compiler/xla/service/service.cc:158]   StreamExecutor device (0): <undefined>, <undefined>
WARNING:tensorflow:From /usr/local/lib/python3.6/site-packages/tensorflow/contrib/ei/python/predictor/ei_predictor.py:187: load (from tensorflow.python.saved_model.loader_impl) is deprecated and will be removed in a future version.
Instructions for updating:
This function will only be available through the v1 compatibility library as tf.compat.v1.saved_model.loader.load or tf.compat.v1.saved_model.load. There will be a new function for importing SavedModels in Tensorflow 2.0.
Using Amazon Elastic Inference Client Library Version: 1.2.12
Number of Elastic Inference Accelerators Available: 1
Elastic Inference Accelerator ID: eia-8c9c06565c1c49819ea391c017c9b6b2
Elastic Inference Accelerator Type: eia1.medium

You can run the dockerfile locally on an EC2 machine (it must be set up with Elastic Inference already)
3 detection[s]
['dog', 'dog', 'dog']
You can run the dockerfile locally on an EC2 machine (it must be set up with Elastic Inference already)
Running SSD Resnet on EIPredictor using default Signature Def
Using DEFAULT_SERVING_SIGNATURE_DEF_KEY .....
3 detection[s]
['dog', 'dog', 'dog']
```

Note that the first line says _All the validation checks passed for Amazon EI from this instance_.

Now push this to a docker registry to run from AWS Batch

```bash
$(aws ecr get-login --no-include-email --region us-east-2)
docker tag ei-hello:latest xxxxxxxxxxxx.dkr.ecr.us-east-2.amazonaws.com/ei-hello:latest
docker push xxxxxxxxxxxx.dkr.ecr.us-east-2.amazonaws.com/ei-hello:latest
```

Output is as follows (see the cloudfront logs). *Note that the validation checks passed*

```
23:47:29
All the validation checks passed for Amazon EI from this instance - i-07bd9e4bbf1c54108
23:47:29
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:526: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
23:47:29
_np_qint8 = np.dtype([("qint8", np.int8, 1)])
23:47:29
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:527: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
23:47:29
_np_quint8 = np.dtype([("quint8", np.uint8, 1)])
23:47:29
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:528: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
23:47:29
_np_qint16 = np.dtype([("qint16", np.int16, 1)])
23:47:29
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:529: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
23:47:29
_np_quint16 = np.dtype([("quint16", np.uint16, 1)])
23:47:29
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:530: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
23:47:29
_np_qint32 = np.dtype([("qint32", np.int32, 1)])
23:47:29
/usr/local/lib/python3.6/site-packages/tensorflow/python/framework/dtypes.py:535: FutureWarning: Passing (type, 1) or '1type' as a synonym of type is deprecated; in a future version of numpy, it will be understood as (type, (1,)) / '(1,)type'.
23:47:29
np_resource = np.dtype([("resource", np.ubyte, 1)])
23:47:31
% Total % Received % Xferd Average Speed Time Time Time Current
23:47:31
Dload Upload Total Spent Left Speed
23:47:31
0 0 0 0 0 0 0 0 --:--:-- --:--:-- --:--:-- 0 100 702 100 702 0 0 3086 0 --:--:-- --:--:-- --:--:-- 3078 100 702 100 702 0 0 3085 0 --:--:-- --:--:-- --:--:-- 3078
23:47:31
Running SSD Resnet on EIPredictor using specified input and outputs
23:47:31
2019-11-22 23:47:31.324060: I tensorflow/core/platform/profile_utils/cpu_utils.cc:94] CPU Frequency: 2900100000 Hz
23:47:31
2019-11-22 23:47:31.324324: I tensorflow/compiler/xla/service/service.cc:150] XLA service 0x405ff70 executing computations on platform Host. Devices:
23:47:31
2019-11-22 23:47:31.324359: I tensorflow/compiler/xla/service/service.cc:158] StreamExecutor device (0): <undefined>, <undefined>
23:47:31
WARNING:tensorflow:From /usr/local/lib/python3.6/site-packages/tensorflow/contrib/ei/python/predictor/ei_predictor.py:187: load (from tensorflow.python.saved_model.loader_impl) is deprecated and will be removed in a future version.
23:47:31
Instructions for updating:
23:47:31
This function will only be available through the v1 compatibility library as tf.compat.v1.saved_model.loader.load or tf.compat.v1.saved_model.load. There will be a new function for importing SavedModels in Tensorflow 2.0.
23:47:33
[Fri Nov 22 23:47:33 2019, 793876us] Error during accelerator discovery
23:47:33
[Fri Nov 22 23:47:33 2019, 793995us] Failed to detect any accelerator
23:47:33
[Fri Nov 22 23:47:33 2019, 794020us] Warning - Preconditions not met for reaching Accelerator
23:47:33
Endpoint: runtime.elastic-inference.us-east-2.amazonaws.com:443
23:47:33
Accelerator ID:
23:47:33
Region: us-east-2
23:47:33
*** Aborted at 1574466453 (unix time) try "date -d @1574466453" if you are using GNU date ***
23:47:33
PC: @ 0x0 (unknown)
23:47:37
run.sh: line 2: 11 Segmentation fault (core dumped) python3 ssd_resnet_predictor.py --image 3dogs.jpg
```
