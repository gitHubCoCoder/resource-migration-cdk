import os
from dotenv import load_dotenv
from aws_cdk import (
    Stack
)
from constructs import Construct
from iam.infrastructure import Iam
from ec2.infrastructure import Ec2
from s3.infrastructure import S3
from redshift.infrastructure import Redshift
from aurora.infrastructure import Aurora
from glue.infrastructure import Glue


load_dotenv()


class Itada(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        # ====== IAM ======
        iam_config = Iam(self, 'Iam').config

        # ====== EC2 ======
        ec2_config = Ec2(self, 'Ec2').config

        # ====== S3 ======
        s3_config = S3(self, 'S3').config

        # ====== REDSHIFT ======
        redshift_config = Redshift(
            self, 'Redshift',
            subnet_ids=ec2_config['public_subnets'].subnet_ids,
            vpc_security_group_ids=[ec2_config['redshiftcluster_sg'].security_group_id]
        ).config

        # ====== AURORA ======
        aurora_config = Aurora(
            self,
            'Aurora',
            vpc=ec2_config['itada_vpc'],
            security_groups=[ec2_config['auroracluster_sg']]
        )

        # ====== GLUE ======
        glue_config = Glue(
            self,
            'Glue',
            catalog_id=iam_config['account_id'],
            pwn_subnet=ec2_config['pwn_subnets'].subnets[0],
            glue_sg_id_list=[ec2_config['glue_sg'].security_group_id],
            rs_attr_endpoint_address=redshift_config['attr_endpoint_address'],
            rs_attr_endpoint_port=redshift_config['attr_endpoint_port'],
            rs_db_name=redshift_config['db_name'],
            gluejob_role_arn=iam_config['gluejob_role_arn']
        )
