from typing import TypedDict
from aws_cdk import (
    Fn,
    aws_iam as iam
)
from constructs import Construct


class IamConfig(TypedDict):
    account_id: str
    gluejob_role_arn: str


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

        # Role
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

        # Configuration parameters
        self._config: IamConfig = {
            'account_id': Fn.ref('AWS::AccountId'),
            'gluejob_role_arn': gluejob_role.role_arn
        }

    @property
    def config(self) -> IamConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
