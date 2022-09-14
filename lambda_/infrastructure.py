import os
from typing import List, TypedDict
from aws_cdk import (
    RemovalPolicy,
    Duration,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_s3 as s3
)
from constructs import Construct


class LambdaConfig(TypedDict):
    pass


class Lambda(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        cdkscripts_bucket: s3.Bucket,
        lambdafunc_role: iam.Role,
        security_groups: List[ec2.SecurityGroup],
        vpc: ec2.Vpc
    ):
        super().__init__(scope, id)

        lambda_func_configs = {
            'TriggerCsvUploadSfLambdaFunc': {
                'description': '',
                'runtime': lambda_.Runtime.PYTHON_3_8,
                'function_name': 'trigger-csv-upload-sf',
                'timeout_secs': 60
            },
            'AuroraSyncFunc': {
                'description': '',
                'runtime': lambda_.Runtime.PYTHON_3_7,
                'function_name': 'aurora-sync',
                'timeout_secs': 183
            },
            'QueryDataLineageFunc': {
                'description': 'An Amazon SNS trigger that logs the message pushed to the SNS topic.',
                'runtime': lambda_.Runtime.PYTHON_3_7,
                'function_name': 'query-data-lineage',
                'timeout_secs': 210
            },
            'ResourceCleanupFunc': {
                'description': '',
                'runtime': lambda_.Runtime.PYTHON_3_9,
                'function_name': 'resource-cleanup',
                'timeout_secs': 3
            },
            'ReloadAppBackendDataFunc': {
                'description': '',
                'runtime': lambda_.Runtime.PYTHON_3_8,
                'function_name': 'reload-app-backend-data',
                'timeout_secs': 3
            },
            'DevelopPostgresRawDataValidationFunc': {
                'description': '',
                'runtime': lambda_.Runtime.PYTHON_3_7,
                'function_name': 'develop-postgres-raw-data-validation',
                'timeout_secs': 900
            },
            'DevelopRedshiftFunc': {
                'description': '',
                'runtime': lambda_.Runtime.PYTHON_3_7,
                'function_name': 'develop-redshift',
                'timeout_secs': 140
            },
            'CsvUploadCrawlerFunc': {
                'description': '',
                'runtime': lambda_.Runtime.PYTHON_3_8,
                'function_name': 'csv-upload-crawler',
                'timeout_secs': 60
            }
        }

        for lambda_func_id, lambda_func_props in lambda_func_configs.items():
            lambda_.Function(
                self,
                lambda_func_id,
                code=lambda_.Code.from_bucket(
                    bucket=cdkscripts_bucket,
                    key=f'lambda_funcs/{lambda_func_props["function_name"]}.py'
                ),
                handler='lambda_function.lambda_handler',
                runtime=lambda_func_props['runtime'],
                description=lambda_func_props['description'],
                environment={},
                function_name=lambda_func_props['function_name'],
                role=lambdafunc_role,
                security_groups=security_groups,
                timeout=Duration.seconds(lambda_func_props['timeout_secs']),
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
                )
            ).apply_removal_policy(RemovalPolicy.DESTROY)
        
        # Configuration parameters
        self._config: LambdaConfig = {}

    @property
    def config(self) -> LambdaConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
