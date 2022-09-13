from email.policy import default
import os
from typing import TypedDict
from aws_cdk import (
    RemovalPolicy,
    aws_iam as iam,
    aws_ec2 as ec2
)
from constructs import Construct


class StepfunctionsConfig(TypedDict):
    pass


class Stepfunctions(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str
    ):
        super().__init__(scope, id)

        # Configuration parameters
        self._config: StepfunctionsConfig = {}

    @property
    def config(self) -> StepfunctionsConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
