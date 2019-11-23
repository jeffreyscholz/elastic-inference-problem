#!~/anaconda3/bin/python

# *****************************************************
#                                                     *
# Copyright 2019 Amazon.com, Inc. or its affiliates.  *
# All Rights Reserved.                                *
#                                                     *
# *****************************************************

import os
import argparse
import requests
import logging
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    logging.error("This utility needs boto3. Please install it first and run the utility again. Command - 'sudo pip install --upgrade boto3'")
    quit()
from distutils.version import StrictVersion

def logErrorAndQuit(msg):
    logging.error(msg)
    quit()

class EIAConfigChecker:
    def __init__(self, region_name, check_inbound_ports, check_outbound_ports,
                 ec2_eia_instances):
        self.check_inbound_ports = check_inbound_ports
        self.check_outbound_ports = check_outbound_ports
        self.ec2_eia_instances = ec2_eia_instances
        self.eia_region_service_name = 'com.amazonaws.' + region_name + '.elastic-inference.runtime'
        # eia policies
        self.eia_trust_policy_arns = []
        # checked vpc
        self.eia_vpces = {}

        # construct clients
        self.ec2_client = boto3.client('ec2', region_name=region_name)
        self.iam_client = boto3.client('iam', region_name=region_name)

    def check(self): 
        # permission policy
        self.check_eia_trust_policy()

        #checkInstance
        self.check_instances()

    def check_instances(self):
        describe_ec2_response = self.ec2_client.describe_instances(
            InstanceIds=self.ec2_eia_instances)
        for _, reservertion in enumerate(
                describe_ec2_response['Reservations']):
            for _, instance in enumerate(reservertion['Instances']):
                self.check_instance(instance)

    def check_ports_with_permission(self, check_ports, ipPermissions):
        checked_ports = []
        for _, ipPermission in enumerate(ipPermissions):
            if ipPermission['IpProtocol'] == 'tcp' or ipPermission['IpProtocol'] == '-1':
                if ipPermission.get('FromPort') is None and ipPermission.get('ToPort') is None:
                    return True
                for port in check_ports:
                    if port not in checked_ports and ipPermission['FromPort'] <= port <= ipPermission['ToPort']:
                        checked_ports.append(port)
        return set(check_ports) == set(checked_ports)

    def check_private_link_security_groups(self, vpc_id, eia_private_link):

        eia_security_groups = []
        eia_valid_security_groups = []
        for _, group in enumerate(eia_private_link['Groups']):
            eia_security_groups.append(group['GroupId'])

        describe_security_groups_response = self.ec2_client.describe_security_groups(
            GroupIds=eia_security_groups)
    
        for _, group in enumerate(describe_security_groups_response['SecurityGroups']):
            if self.check_ports_with_permission(self.check_inbound_ports, group['IpPermissions']):
                eia_valid_security_groups.append(group['GroupId'])

        if len(eia_valid_security_groups) == 0:
            logging.warning(
                "The security groups:" + eia_security_groups.__str__() +
                " has not been configured with correct rules, please enable inbound rule for ports "
                + self.check_inbound_ports.__str__() + " for at least one security group which is used by the instance.")
            return False
        self.eia_vpces[vpc_id]['eia_security_group_ids'] = eia_valid_security_groups
        return True

    def check_private_link(self, vpc_id):
        is_private_link_set_correctly = True
        eia_private_links = self.ec2_client.describe_vpc_endpoints(
            Filters=[{
                'Name': 'service-name',
                'Values': [self.eia_region_service_name]
            }, {
                'Name': 'vpc-id',
                'Values': [vpc_id]
            }])['VpcEndpoints']

        if (len(eia_private_links) == 0):
            logging.error("Please create privateLink VPC endpoint in vpc " + vpc_id + " which is used by the ec2-instance. Ref - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-ei.html. Also, make sure that the endpoint is in available status and PrivateDnsEnabled property is set to true.")
            return False

        #just one eia end point in each vpc    
        if eia_private_links[0]['State'] != 'available':
            logging.error("The vpc endpoint is not in available state. Please wait for 2-3 minutes for the vpc endpoint to be setup.")
            is_private_link_set_correctly = False
        
        if eia_private_links[0]['PrivateDnsEnabled'] != True:
            logging.error("Please make sure the vpc endpoint " +
                  eia_private_links[0]['VpcEndpointId'] +
                  " is in available status and PrivateDnsEnabled is True")
            is_private_link_set_correctly = False

        if self.check_private_link_security_groups(vpc_id, eia_private_links[0]) != True:
            is_private_link_set_correctly = False
        
        #TODO check subnet size
        self.eia_vpces[vpc_id]['eia_subnet_ids'] = eia_private_links[0][
            'SubnetIds']
        return is_private_link_set_correctly

    def check_eia_trust_policy(self):
        attach_policies = []
        try:
            attach_policies = self.iam_client.get_account_authorization_details(
                Filter=['LocalManagedPolicy'])['Policies']
        except:
            logErrorAndQuit("Please use 'aws configure' to configure credentials or update iam policy role to allow reading credentials. Ref - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-ei.html#ei-role-policy")

        #at least one policy to grant permission for eia
        for _, policy in enumerate(attach_policies):
            for _, policy_doc in enumerate(policy['PolicyVersionList']):
                if (policy_doc['IsDefaultVersion'] == True):
                    for _, statement in enumerate(policy_doc['Document']['Statement']):
                        try:
                            if ('elastic-inference:Connect' in statement.get('Action')) and statement.get('Resource') == '*' and statement.get('Effect') == 'Allow':
                                self.eia_trust_policy_arns.append(policy['Arn'])
                            elif '*' in statement.get('Action'):
                                self.eia_trust_policy_arns.append(policy['Arn'])
                        except:
                            None            
        if len(self.eia_trust_policy_arns) == 0:
            logging.warning("The required IAM policy or credentials which grants permissions to connect to the Elastic Inference service appears to be missing, please create a policy and attach it to the EC2 instance. Ref - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-ei.html#ei-role-policy")

    def check_vpc(self, vpc_id, instance_id):
        vpc = self.eia_vpces.get(vpc_id)
        is_vpc_set_correctly = True

        if vpc is None:
            vpc = {'configured': False}
            self.eia_vpces[vpc_id] = vpc

            #vpc dns
            eia_vpc_enable_dns = self.ec2_client.describe_vpc_attribute(
                Attribute='enableDnsSupport',
                VpcId=vpc_id)['EnableDnsSupport']['Value']

            if (eia_vpc_enable_dns != True):
                logging.error("Please set the EnableDnsSupport flag for VPC " + vpc_id + " to True")
                is_vpc_set_correctly = False

            #vpc hostnames
            eia_vpc_enable_hostnames = self.ec2_client.describe_vpc_attribute(
                Attribute='enableDnsHostnames',
                VpcId=vpc_id)['EnableDnsHostnames']['Value']

            if eia_vpc_enable_hostnames != True:
                logging.error("Please set the EnableDnsHostnames flag for VPC " + vpc_id + " to True")
                is_vpc_set_correctly = False

            # check private link in vpc
            if self.check_private_link(vpc_id) != True:
                is_vpc_set_correctly = False

            vpc['configured'] = True

        elif vpc['configured'] == False:
            logging.error("The VPC " + vpc_id + " for instance " + instance_id + 
            " is missing required configuration to enable connectivity between instances and Amazon EI service.")
            is_vpc_set_correctly = False

        return is_vpc_set_correctly

    def check_iam_role(self, iam_role_profile, instance_id):
        matchPolicy = False
        if iam_role_profile is not None:
            iam_role_name = iam_role_profile['Arn'].split("/")[-1]
            iam = boto3.resource('iam')
            instance_profile = iam.InstanceProfile(iam_role_name)
            roles_attribute = instance_profile.roles_attribute
            for role in roles_attribute:

                attach_policies = self.iam_client.list_attached_role_policies(
                RoleName=role['RoleName'])['AttachedPolicies']
                for _, attach_policy in enumerate(attach_policies):
                    if (attach_policy['PolicyArn'] in self.eia_trust_policy_arns) or (attach_policy['PolicyName'] == 'AdministratorAccess'):
                        matchPolicy = True
                        break
                if matchPolicy == False and self.eia_trust_policy_arns:
                    logging.warning(self.eia_trust_policy_arns.__str__() +
                      " has not been attached to role " + iam_role_name +
                      " with which the instance " + instance_id + " is launched.")
        else:
            logging.warning("No iam role was configured with the instance: " + instance_id + ". Please make sure you use an iam role which complies with EI policies - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-ei.html#ei-role-policy OR make sure aws credentials are set using 'aws configure' so that connection to EI service succeeds.")
        return matchPolicy


    def check_instance(self, instance):
        instance_id = instance['InstanceId']
        check_failed = False

        #eia exists
        eia = instance.get('ElasticInferenceAcceleratorAssociations')
        if (eia is None):
            logErrorAndQuit("Cannot detect or reach an accelerator paired with instance " + instance_id + ". Make sure instance is launched with an accelerator attached. Ref - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-ei.html#eia-launch")

        #iam role
        iam_role_profile = instance.get('IamInstanceProfile')
        if self.check_iam_role(iam_role_profile, instance_id) == False:
            check_failed = True
        
        #vpc including privateLink
        instance_vpc_id = instance['VpcId']
        if self.check_vpc(instance_vpc_id, instance_id) == False:
            check_failed = True

        #subnet
        subnet_id = instance['SubnetId']
        if (subnet_id not in self.eia_vpces[instance_vpc_id]['eia_subnet_ids']):
            logging.error("There does not appear to be a VPC endpoint within the subnet where instance "+ instance_id + " is launched. Please use a subnet which is part of a VPC endpoint or update the VPC endpoint to add the desired subnet. Ref - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-ei.html#eia-privatelink")
            check_failed = True

        #securityGroup
        security_group_configured = False
        instance_security_groups = []
        for _, interface in enumerate(instance['NetworkInterfaces']):
            for _, group in enumerate(interface['Groups']):
                instance_security_groups.append(group['GroupId'])
        
        describe_security_groups_response = self.ec2_client.describe_security_groups(
            GroupIds=instance_security_groups)

        for _, group in enumerate(describe_security_groups_response['SecurityGroups']):
            if self.check_ports_with_permission(self.check_outbound_ports, group['IpPermissionsEgress']):
                security_group_configured = True
                break

        if security_group_configured == False:
            logging.warning("Please ensure that the security group associated with the instance allows outbound HTTPS traffic.")       
            check_failed = True

        if check_failed == False:
            print("All the validation checks passed for Amazon EI from this instance - " + instance_id)

def get_instance_id_from_metadata():
    ids = []
    try:
        instance_id = requests.get('http://169.254.169.254/latest/meta-data/instance-id').text
        ids.append(instance_id)
    except:
        ids =[]
    return ids

def get_region_from_metadata():
    try:
        region = requests.get('http://169.254.169.254/latest/meta-data/placement/availability-zone').text[:-1]
        return region
    except:
        return None   

if __name__ == "__main__":
    #check boto3 version
    if StrictVersion(boto3.__version__)<StrictVersion('1.9.71'):
        logErrorAndQuit("Minimum boto3 version required is 1.9.71. Found version - " + boto3.__version__ + ". Please update it using command - 'sudo pip install --upgrade boto3'")
    
    #parse args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--instance-ids',
        nargs='+',
        dest='instances',
        help='list of instance id of ec2 instance to diagnose',
        required=False)

    parser.add_argument(
        '--region',
        dest='region',
        help='region name in which instance is launched',
        required=False)

    check_inbound_ports = [443]
    check_outbound_ports = [443]
    
    args = parser.parse_args()
    
    #get region name
    region_name = args.region 
    if region_name is None:
        region_name = get_region_from_metadata()
        if region_name is None:
            region_name = boto3.session.Session().region_name
    
    if region_name is None:
        logErrorAndQuit("If running this command outside an ec2 instance, "+ 
        "region name must be set either by env var 'AWS_DEFAULT_REGION' or aws config, or passed in arguments --region")

    instance_ids = args.instances
    if(instance_ids is None):
        instance_ids = get_instance_id_from_metadata()
    if(len(instance_ids)==0):
        logErrorAndQuit("If running this command outside an ec2 instance, "+ 
        "please pass instance ids by arguments --instance-ids")

    checker = EIAConfigChecker(region_name, check_inbound_ports,
                               check_outbound_ports, instance_ids)
    checker.check()
