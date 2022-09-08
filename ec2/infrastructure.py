from typing import TypedDict
from aws_cdk import (
    RemovalPolicy,
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
        id: str
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
