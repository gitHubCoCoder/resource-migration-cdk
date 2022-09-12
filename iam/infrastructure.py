from typing import TypedDict
from aws_cdk import (
    Fn,
    RemovalPolicy,
    aws_iam as iam
)
from constructs import Construct


class IamConfig(TypedDict):
    account_id: str
    gluejob_role: iam.Role
    ec2instance_role: iam.Role


class Iam(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str
    ):
        super().__init__(scope, id)

        # Managed policy
        amazon_sqs_full_access = iam.ManagedPolicy.from_managed_policy_name(
            self,
            'AmazonSQSFullAccess',
            managed_policy_name='AmazonSQSFullAccess'
        )

        amazon_s3_full_access = iam.ManagedPolicy.from_managed_policy_name(
            self,
            'AmazonS3FullAccess',
            managed_policy_name='AmazonS3FullAccess'
        )

        aws_glue_service_role = iam.ManagedPolicy.from_managed_policy_name(
            self,
            'AWSGlueServiceRole',
            managed_policy_name='AWSGlueServiceRole'
        )

        amazon_sns_full_access = iam.ManagedPolicy.from_managed_policy_name(
            self,
            'AmazonSNSFullAccess',
            managed_policy_name='AmazonSNSFullAccess'
        )

        amazon_athena_full_access = iam.ManagedPolicy.from_managed_policy_name(
            self,
            'AmazonAthenaFullAccess',
            managed_policy_name='AmazonAthenaFullAccess'
        )

        # Role
        ec2instance_role = iam.Role(self, 'Ec2InstanceRole',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            description='Allows EC2 to call AWS services on your behalf.',
            managed_policies=[
                aws_glue_service_role,
                amazon_s3_full_access,
                amazon_athena_full_access
            ]
        )
        ec2instance_role.apply_removal_policy(RemovalPolicy.DESTROY)

        gluejob_role = iam.Role(self, "GlueJobRole",
            assumed_by=iam.ServicePrincipal('glue.amazonaws.com'),
            description='Allows Glue to call AWS services on your behalf.',
            managed_policies=[
                amazon_sqs_full_access,
                amazon_s3_full_access,
                aws_glue_service_role,
                amazon_sns_full_access
            ]
        )
        gluejob_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # Configuration parameters
        self._config: IamConfig = {
            'account_id': Fn.ref('AWS::AccountId'),
            'gluejob_role': gluejob_role,
            'ec2instance_role': ec2instance_role
        }

    @property
    def config(self) -> IamConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
