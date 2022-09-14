from dotenv import load_dotenv
from aws_cdk import (
    Stack,
)
from constructs import Construct
from iam.infrastructure import Iam
from ec2.infrastructure import Ec2
from alb.infrastructure import Alb
from s3.infrastructure import S3
from redshift.infrastructure import Redshift
from aurora.infrastructure import Aurora
from lambda_.infrastructure import Lambda
from glue.infrastructure import Glue
from stepfunctions.infrastructure import Stepfunctions
 

load_dotenv()


class Itada(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        # ====== IAM ======
        iam_config = Iam(self, 'Iam').config

        # ====== EC2 ======
        ec2_config = Ec2(self, 'Ec2', iam_config['ec2instance_role']).config

        # ====== ALB ======
        alb_config = Alb(
            self,
            'Alb',
            hosted_zone_vpcs=[ec2_config['itada_vpc']],
            alb_vpc=ec2_config['itada_vpc'],
            amundsen_instance=ec2_config['amundsen_instance'],
            amundsenalb_sg=ec2_config['amundsenalb_sg'],
            chartservice_instance=ec2_config['chartservice_instance'],
            chartservicealb_sg=ec2_config['chartservicealb_sg']
        ).config

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

        # ====== LAMBDA ======
        lambda_config = Lambda(
            self,
            'Lambda',
            cdkscripts_bucket=s3_config['itada_cdk_scripts'],
            lambdafunc_role=iam_config['lambdafunc_role'],
            security_groups=[ec2_config['default_sg']],
            vpc=ec2_config['itada_vpc']
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
            gluejob_role_arn=iam_config['gluejob_role'].role_arn
        )

        # ====== STEPFUNCTIONS ======
        stepfunctions_config = Stepfunctions(
            self,
            'Stepfunctions',
            stepfunction_role_arn=iam_config['stepfunction_role'].role_arn
        )