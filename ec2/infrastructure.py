from email.policy import default
import os
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
    default_sg: ec2.SecurityGroup
    amundsenalb_sg: ec2.SecurityGroup
    amundsen_sg: ec2.SecurityGroup
    chartservicealb_sg: ec2.SecurityGroup
    chartservice_sg: ec2.SecurityGroup
    auroracluster_sg: ec2.SecurityGroup
    redshiftcluster_sg: ec2.SecurityGroup
    glue_sg: ec2.SecurityGroup
    amundsen_instance: ec2.Instance
    chartservice_instance: ec2.Instance


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
            max_azs=2
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
        # default-sg
        default_sg = ec2.SecurityGroup.from_security_group_id(
            self,
            'DefaultSg',
            security_group_id=itada_vpc.vpc_default_security_group
        )

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
        amundsenalb_conn = ec2.Connections(
            security_groups=[amundsenalb_sg]
        )
        amundsenalb_conn.allow_from_any_ipv4(port_range=ec2.Port.tcp(80))
        amundsenalb_conn.allow_from_any_ipv4(port_range=ec2.Port.tcp(443))
        amundsenalb_conn.allow_from(other=ec2.Peer.any_ipv6(), port_range=ec2.Port.tcp(80))
        amundsenalb_conn.allow_from(other=ec2.Peer.any_ipv6(), port_range=ec2.Port.tcp(443))

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
        amundsen_conn = ec2.Connections(
            default_port=ec2.Port.tcp(80),
            security_groups=[amundsen_sg]
        )
        amundsen_conn.allow_default_port_from(other=ec2.Peer.security_group_id(amundsenalb_sg.security_group_id))

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
        chartservicealb_conn = ec2.Connections(
            security_groups=[chartservicealb_sg]
        )
        chartservicealb_conn.allow_from_any_ipv4(port_range=ec2.Port.tcp(80))
        chartservicealb_conn.allow_from_any_ipv4(port_range=ec2.Port.tcp(443))
        chartservicealb_conn.allow_from(other=ec2.Peer.any_ipv6(), port_range=ec2.Port.tcp(80))
        chartservicealb_conn.allow_from(other=ec2.Peer.any_ipv6(), port_range=ec2.Port.tcp(443))

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
        chartservice_conn = ec2.Connections(
            default_port=ec2.Port.tcp(8088),
            security_groups=[chartservice_sg]
        )
        chartservice_conn.allow_default_port_from(other=ec2.Peer.security_group_id(chartservicealb_sg.security_group_id))

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
        auroracluster_conn = ec2.Connections(
            default_port=ec2.Port.tcp(5432),
            security_groups=[auroracluster_sg]
        )
        auroracluster_conn.allow_default_port_from(other=ec2.Peer.security_group_id(itada_vpc.vpc_default_security_group))

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
        redshiftcluster_conn = ec2.Connections(
            default_port=ec2.Port.tcp(5439),
            security_groups=[redshiftcluster_sg]
        )
        redshiftcluster_conn.allow_default_port_from(other=ec2.Peer.security_group_id(itada_vpc.vpc_default_security_group))
        redshiftcluster_conn.allow_default_port_from(other=ec2.Peer.security_group_id(auroracluster_sg.security_group_id))
        redshiftcluster_conn.allow_default_port_from(other=ec2.Peer.security_group_id(chartservice_sg.security_group_id))

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
        glue_conn = ec2.Connections(
            security_groups=[glue_sg]
        )
        glue_conn.allow_internally(
            port_range=ec2.Port.all_tcp()
        )

        # Instances
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
                    'machine_image': ec2.MachineImage.generic_linux(
                        ami_map={
                            'ap-southeast-1': 'ami-0443cb4c104c2b7ec',
                            'ap-southeast-2': 'ami-00246527dcee8c2ed'
                        }
                    )
                }
            },
            'ChartService': {
                'ChartServiceKey': {
                    'key_name': 'chart_service_key'
                },
                'ChartServiceInstance': {
                    'machine_image': ec2.MachineImage.generic_linux(
                        ami_map={
                            'ap-southeast-1': 'ami-03343aa326f22d76c',
                            'ap-southeast-2': 'ami-02c498b3f4289451e'
                        }
                    )
                }
            }
        }

        returned_instance_dict = {}

        for instance_name, props in instance_configs.items():
            key_props = props[instance_name + 'Key']
            instance_props = props[instance_name + 'Instance']

            ec2.CfnKeyPair(
                self,
                instance_name + 'Key',
                key_name=key_props['key_name'],
                key_type='rsa'
            )

            returned_instance_dict[instance_name] = ec2.Instance(
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
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PUBLIC
                )
            )

        # Configuration parameters
        self._config: Ec2Config = {
            'itada_vpc': itada_vpc,
            'pwn_subnets': pwn_subnets,
            'public_subnets': public_subnets,
            'default_sg': default_sg,
            'amundsenalb_sg': amundsenalb_sg,
            'amundsen_sg': amundsen_sg,
            'chartservicealb_sg': chartservicealb_sg,
            'chartservice_sg': chartservice_sg,
            'auroracluster_sg': auroracluster_sg,
            'redshiftcluster_sg': redshiftcluster_sg,
            'glue_sg': glue_sg,
            'amundsen_instance': returned_instance_dict['Amundsen'],
            'chartservice_instance': returned_instance_dict['ChartService']
        }

    @property
    def config(self) -> Ec2Config:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
