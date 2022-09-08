import os
from typing import TypedDict
from aws_cdk import (
    RemovalPolicy,
    CfnTag,
    aws_redshift as redshift
)
from constructs import Construct


class RedshiftConfig(TypedDict):
    attr_endpoint_address: str
    attr_endpoint_port: str
    db_name: str


class Redshift(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        subnet_ids,
        vpc_security_group_ids
    ):
        super().__init__(scope, id)

        # Cluster subnet group
        redshift.CfnClusterSubnetGroup(
            self,
            'RedshiftClusterSubnetGroup',
            description='Group of public subnets for Redshift to deploy',
            subnet_ids=subnet_ids,
            tags=[CfnTag(key='Name', value='redshift-cluster-subnet-group')]
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        redshift_cluster = redshift.CfnCluster(
            self,
            'RedshiftCluster',
            cluster_type='multi-node',
            db_name='dev',
            master_username=os.getenv('DEVELOPREDSHIFT_USERNAME'),
            master_user_password=os.getenv('DEVELOPREDSHIFT_USERPW'),
            node_type='dc2.large',
            cluster_identifier='itada-redshift-cluster',
            cluster_subnet_group_name='redshift-cluster-subnet-group',
            number_of_nodes=1,
            port=5439,
            vpc_security_group_ids= vpc_security_group_ids
        )
        redshift_cluster.apply_removal_policy(RemovalPolicy.DESTROY)

        # Configuration parameters
        self._config: RedshiftConfig = {
            'attr_endpoint_address': redshift_cluster.attr_endpoint_address,
            'attr_endpoint_port': redshift_cluster.attr_endpoint_port,
            'db_name': redshift_cluster.db_name
        }

    @property
    def config(self) -> RedshiftConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
