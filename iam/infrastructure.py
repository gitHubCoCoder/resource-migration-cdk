from typing import TypedDict
from aws_cdk import (
    Fn,
    RemovalPolicy,
    aws_iam as iam
)
from constructs import Construct


class IamConfig(TypedDict):
    account_id: str
    ec2instance_role: iam.Role
    lambdafunc_role: iam.Role
    gluejob_role: iam.Role
    stepfunction_role: iam.Role


class Iam(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str
    ):
        super().__init__(scope, id)

        # Managed policy
        amazon_sqs_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AmazonSQSFullAccess'
        )

        amazon_s3_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AmazonS3FullAccess'
        )

        aws_glue_service_role = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='service-role/AWSGlueServiceRole'
        )

        amazon_sns_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AmazonSNSFullAccess'
        )

        amazon_athena_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AmazonAthenaFullAccess'
        )

        secretsmanager_read_write = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='SecretsManagerReadWrite'
        )

        cloudwatch_logs_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='CloudWatchLogsFullAccess'
        )
        
        amazon_rds_data_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AmazonRDSDataFullAccess'
        )

        aws_stepfunctions_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AWSStepFunctionsFullAccess'
        )

        amazon_redshift_data_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AmazonRedshiftDataFullAccess'
        )

        cloudwatch_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='CloudWatchFullAccess'
        )

        aws_glue_service_notebook_role = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='service-role/AWSGlueServiceNotebookRole'
        )

        aws_glue_console_sagemaker_notebook_full_access = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AWSGlueConsoleSageMakerNotebookFullAccess'
        )

        aws_lambda_role = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='service-role/AWSLambdaRole'
        )

        lambda_invoke = iam.Policy(
            self,
            'LambdaInvokePolicy',
            document=iam.PolicyDocument(
                assign_sids=True,
                statements=[
                    iam.PolicyStatement(
                        actions=['lambda:InvokeFunction', 'lambda:InvokeAsync'],
                        effect=iam.Effect.ALLOW,
                        resources=['*']
                    )
                ]
            ),
            policy_name='LambdaInvoke'
        )

        lambda_stop_db = iam.Policy(
            self,
            'LambdaStopDbPolicy',
            document=iam.PolicyDocument(
                assign_sids=True,
                statements=[
                    iam.PolicyStatement(
                        actions=['rds:StopDBCluster', 'rds:StopDBInstance'],
                        effect=iam.Effect.ALLOW,
                        resources=['*']
                    )
                ]
            ),
            policy_name='LambdaStopDB'
        )

        lambda_stop_instance = iam.Policy(
            self,
            'LambdaStopInstancePolicy',
            document=iam.PolicyDocument(
                assign_sids=True,
                statements=[
                    iam.PolicyStatement(
                        actions=['ec2:StopInstances'],
                        effect=iam.Effect.ALLOW,
                        resources=['*']
                    )
                ]
            ),
            policy_name='LambdaStopInstance'
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

        lambdafunc_role = iam.Role(self, 'LambdaFuncRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description='Allows Lambda Function to call AWS services on your behalf.',
            managed_policies=[
                lambda_invoke,
                secretsmanager_read_write,
                amazon_s3_full_access,
                aws_glue_service_role,
                cloudwatch_logs_full_access,
                amazon_rds_data_full_access,
                amazon_sns_full_access,
                aws_stepfunctions_full_access,
                amazon_redshift_data_full_access,
                lambda_stop_db,
                lambda_stop_instance
            ]
        )
        lambdafunc_role.apply_removal_policy(RemovalPolicy.DESTROY)

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

        stepfunction_role = iam.Role(self, "StepFunctionRole",
            assumed_by=iam.ServicePrincipal('states.amazonaws.com'),
            description='Allows Step Function to call AWS services on your behalf.',
            managed_policies=[
                cloudwatch_full_access,
                aws_glue_service_notebook_role,
                aws_glue_service_role,
                aws_glue_console_sagemaker_notebook_full_access,
                aws_lambda_role
            ]
        )
        stepfunction_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # Configuration parameters
        self._config: IamConfig = {
            'account_id': Fn.ref('AWS::AccountId'),
            'ec2instance_role': ec2instance_role,
            'lambdafunc_role': lambdafunc_role,
            'gluejob_role': gluejob_role,
            'stepfunction_role': stepfunction_role
        }

    @property
    def config(self) -> IamConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
