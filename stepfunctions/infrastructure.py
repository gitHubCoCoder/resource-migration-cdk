from typing import TypedDict
from aws_cdk import (
    RemovalPolicy,
    aws_logs as logs,
    aws_stepfunctions as stepfunctions
)
from constructs import Construct


class StepfunctionsConfig(TypedDict):
    pass


class Stepfunctions(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        stepfunction_role_arn: str
    ):
        super().__init__(scope, id)

        step_func_configs = {
            'CsvUploadStateMachine': {
                'function_name': 'csv-upload-state-machine'
            },
            'DevelopItadaStateMachine': {
                'function_name': 'csv-upload-state-machine'
            }
        }

        for step_func_id, step_func_props in step_func_configs.items():
            log_group = logs.LogGroup(
                self,
                step_func_id + 'LogGroup',
                log_group_name=f'/aws/vendedlogs/states/{step_func_props["function_name"]}-Logs',
                removal_policy=RemovalPolicy.DESTROY,
                retention=logs.RetentionDays.ONE_WEEK
            )

            st_machine = stepfunctions.CfnStateMachine(
                self,
                step_func_id + 'StepFunc',
                role_arn=stepfunction_role_arn,
                definition_s3_location=stepfunctions.CfnStateMachine.S3LocationProperty(
                    bucket='itada-cdk-scripts',
                    key=f'step_funcs/{step_func_props["function_name"]}.json'
                ),
                logging_configuration=stepfunctions.CfnStateMachine.LoggingConfigurationProperty(
                    destinations=[
                        stepfunctions.CfnStateMachine.LogDestinationProperty(
                            cloud_watch_logs_log_group=stepfunctions.CfnStateMachine.CloudWatchLogsLogGroupProperty(
                                log_group_arn=log_group.log_group_arn
                            )
                        )
                    ],
                    include_execution_data=True,
                    level='ALL'
                ),
                state_machine_name=step_func_props['function_name'],
                state_machine_type='STANDARD'
            )
            st_machine.apply_removal_policy(RemovalPolicy.DESTROY)

        # Configuration parameters
        self._config: StepfunctionsConfig = {}

    @property
    def config(self) -> StepfunctionsConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
