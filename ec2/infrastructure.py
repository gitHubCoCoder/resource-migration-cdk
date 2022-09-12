from typing import TypedDict
from aws_cdk import (
    RemovalPolicy,
    aws_iam as iam,
    aws_ec2 as ec2
)
from constructs import Construct


class Ec2Config(TypedDict):
    itada_vpc: ec2.Vpc
    pwn_subnets: ec2.SelectedSubnets
    public_subnets: ec2.SelectedSubnets
    amundsenalb_sg: ec2.SecurityGroup
    amundsen_sg: ec2.SecurityGroup
    chartservicealb_sg: ec2.SecurityGroup
    chartservice_sg: ec2.SecurityGroup
    auroracluster_sg: ec2.SecurityGroup
    redshiftcluster_sg: ec2.SecurityGroup
    glue_sg: ec2.SecurityGroup


class Ec2(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        ec2instance_role: iam.Role
    ):
        super().__init__(scope, id)

        # VPC
        itada_vpc = ec2.Vpc(
            self,
            'ItadaVpc',
            cidr='10.0.0.0/16',
            max_azs=1
        )
        itada_vpc.apply_removal_policy(RemovalPolicy.DESTROY)

        # Extract subnet information
        pwn_subnets = itada_vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
        )

        public_subnets = itada_vpc.select_subnets(
            subnet_type=ec2.SubnetType.PUBLIC
        )

        # Security group
        # amundsen-alb-sg
        amundsenalb_sg = ec2.SecurityGroup(
            self,
            'AmundsenAlbSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Amundsen ALB',
            security_group_name='amundsen-alb-sg'
        )
        amundsenalb_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(80))
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(443))

        # amundsen-sg
        amundsen_sg = ec2.SecurityGroup(
            self,
            'AmundsenSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Amundsen EC2',
            security_group_name='amundsen-sg'
        )
        amundsen_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        amundsen_sg.add_ingress_rule(ec2.Peer.security_group_id(amundsenalb_sg.security_group_id), ec2.Port.tcp(80))

        # chart-service-alb-sg
        chartservicealb_sg = ec2.SecurityGroup(
            self,
            'ChartServiceAlbSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Chart Service ALB',
            security_group_name='chart-service-alb-sg'
        )
        chartservicealb_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(80))
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(443))

        # chart-service-sg
        chartservice_sg = ec2.SecurityGroup(
            self,
            'ChartServiceSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Chart Service EC2',
            security_group_name='chart-service-sg'
        )
        chartservice_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        chartservice_sg.add_ingress_rule(ec2.Peer.security_group_id(chartservicealb_sg.security_group_id), ec2.Port.tcp(8088))

        # aurora-cluster-sg
        auroracluster_sg = ec2.SecurityGroup(
            self,
            'AuroraClusterSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Aurora Cluster',
            security_group_name='aurora-cluster-sg'
        )
        auroracluster_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        auroracluster_sg.add_ingress_rule(ec2.Peer.security_group_id(itada_vpc.vpc_default_security_group), ec2.Port.tcp(5432))

        # redshift-cluster-sg
        redshiftcluster_sg = ec2.SecurityGroup(
            self,
            'RedshiftClusterSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Redshift Cluster',
            security_group_name='redshift-cluster-sg'
        )
        redshiftcluster_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        redshiftcluster_sg.add_ingress_rule(ec2.Peer.security_group_id(itada_vpc.vpc_default_security_group), ec2.Port.tcp(5439))
        redshiftcluster_sg.add_ingress_rule(ec2.Peer.security_group_id(auroracluster_sg.security_group_id), ec2.Port.tcp(5439))
        redshiftcluster_sg.add_ingress_rule(ec2.Peer.security_group_id(chartservice_sg.security_group_id), ec2.Port.tcp(5439))

        # glue-sg
        glue_sg = ec2.SecurityGroup(
            self,
            'GlueSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Glue',
            security_group_name='glue-sg'
        )
        glue_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        glue_sg.add_ingress_rule(ec2.Peer.security_group_id(glue_sg.security_group_id), ec2.Port.all_tcp())

        # Instances
        # Bootstrapwithdocker userdata
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            'sudo apt-get update',
            'sudo apt-get install \
                ca-certificates \
                curl \
                gnupg \
                lsb-release -y',
            'sudo mkdir -p /etc/apt/keyrings',
            'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
            'echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
            $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
            'sudo apt-get update',
            'sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y',
            'sudo apt-get update',
            'sudo apt-get install docker-compose-plugin -y'
        )

        ebs_volumes = [
            ec2.BlockDevice(
                device_name="/dev/sda1",
                volume=ec2.BlockDeviceVolume.ebs(
                    30,
                    delete_on_termination=False,
                    volume_type=ec2.EbsDeviceVolumeType.GP2
                )
            )
        ]

        instance_configs = {
            'Amundsen': {
                'AmundsenKey': {
                    'key_name': 'amundsen_key'
                },
                'AmundsenInstance': {
                    'machine_image': ec2.MachineImage.lookup(
                        name='ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-20220419'
                    )
                }
            },
            'ChartService': {
                'ChartServiceKey': {
                    'key_name': 'chart_service_key'
                },
                'ChartServiceInstance': {
                    'machine_image': ec2.MachineImage.lookup(
                        name='ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20220609'
                    )
                }
            }
        }

        for instance_name, props in instance_configs.items():
            key_props = props[instance_name + 'Key']
            instance_props = props[instance_name + 'Instance']

            ec2.CfnKeyPair(
                self,
                instance_name + 'Key',
                key_name=key_props['key_name'],
                key_type='rsa'
            )

            ec2.Instance(
                self,
                instance_name + 'Instance',
                vpc=itada_vpc,
                instance_type=ec2.InstanceType('r5a.large'),
                machine_image=instance_props['machine_image'],
                allow_all_outbound=True,
                availability_zone=public_subnets.subnets[0].availability_zone,
                block_devices=ebs_volumes,
                instance_name=instance_name,
                key_name=key_props['key_name'],
                role=ec2instance_role,
                security_group=amundsen_sg,
                user_data=user_data,
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PUBLIC
                )
            )

        # Configuration parameters
        self._config: Ec2Config = {
            'itada_vpc': itada_vpc,
            'pwn_subnets': pwn_subnets,
            'public_subnets': public_subnets,
            'amundsenalb_sg': amundsenalb_sg,
            'amundsen_sg': amundsen_sg,
            'chartservicealb_sg': chartservicealb_sg,
            'chartservice_sg': chartservice_sg,
            'auroracluster_sg': auroracluster_sg,
            'redshiftcluster_sg': redshiftcluster_sg,
            'glue_sg': glue_sg
        }

    @property
    def config(self) -> Ec2Config:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
