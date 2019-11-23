FROM 763104351884.dkr.ecr.us-east-2.amazonaws.com/tensorflow-inference-eia:1.14.0-cpu-py36-ubuntu16.04
RUN apt update
RUN apt-get update && apt-get upgrade -y 

RUN pip3 install matplotlib 
RUN pip3 install pillow
RUN pip3 install boto3
RUN aws s3 cp s3://amazonei-tensorflow/tensorflow/v1.13/ubuntu/archive/tensorflow-1-13-1-ubuntu-ei-1-1-python36.tar.gz . --no-sign-request \
        && tar xvzf tensorflow-1-13-1-ubuntu-ei-1-1-python36.tar.gz \
        && pip3 install tensorflow-1-13-1-ubuntu-ei-1-1-python36/*.whl

COPY . /ei_hello

WORKDIR /ei_hello

ENTRYPOINT ["/bin/bash", "run.sh"]
