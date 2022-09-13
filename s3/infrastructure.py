from typing import TypedDict
from aws_cdk import (
    RemovalPolicy,
    aws_s3 as s3
)
from constructs import Construct


class S3Config(TypedDict):
    itada_cdk_scripts: s3.Bucket


class S3(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str
    ):
        super().__init__(scope, id)

        # itada-cdk-scripts
        itada_cdk_scripts = s3.Bucket.from_bucket_name(
            self,
            'ItadaCdkScriptsBucket',
            bucket_name='itada-cdk-scripts'
        )

        # itada-datasource
        s3.Bucket(
            self,
            'ItadaDatasourceBucket',
            bucket_name='itada-datasource-temp',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # metadata-center
        s3.Bucket(
            self,
            'MetadataCenterBucket',
            bucket_name='metadata-center-temp',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # itada-athena-query-result
        s3.Bucket(
            self,
            'ItadaAthenaQueryResultBucket',
            bucket_name='itada-athena-query-result-temp',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Configuration parameters
        self._config: S3Config = {
            'itada_cdk_scripts': itada_cdk_scripts
        }

    @property
    def config(self) -> S3Config:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
