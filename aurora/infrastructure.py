import os
from typing import TypedDict, List
from aws_cdk import (
    RemovalPolicy,
    SecretValue,
    aws_ec2 as ec2,
    aws_rds as rds
)
from constructs import Construct


class AuroraConfig(TypedDict):
    pass


class Aurora(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        vpc: ec2.Vpc,
        security_groups: List[ec2.SecurityGroup]
    ):
        super().__init__(scope, id)

        auroracluster_subnet_group = rds.SubnetGroup(
            self,
            'AuroraClusterSubnetGroup',
            description='Group of public subnets for Aurora to deploy',
            vpc=vpc,
            removal_policy=RemovalPolicy.DESTROY,
            subnet_group_name='aurora-cluster-subnet-group',
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        rds.ServerlessCluster(
            self,
            'AuroraCluster',
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=rds.AuroraPostgresEngineVersion.VER_13_6),
            cluster_identifier='itada-aurora-cluster',
            credentials=rds.Credentials.from_password(
                username=os.getenv('AURORACLUSTER_USERNAME'),
                password=SecretValue.unsafe_plain_text(os.getenv('AURORACLUSTER_USERPW'))
            ),
            default_database_name='dev',
            security_groups= security_groups,
            enable_data_api=True,
            removal_policy=RemovalPolicy.DESTROY,
            subnet_group=auroracluster_subnet_group,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        # Configuration parameters
        self._config: AuroraConfig = {}

    @property
    def config(self) -> AuroraConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
