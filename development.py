import os
from dotenv import load_dotenv
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_glue as glue
)
from constructs import Construct
from iam.infrastructure import Iam
from ec2.infrastructure import Ec2
from s3.infrastructure import S3
from redshift.infrastructure import Redshift


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
        


        # ====== GLUE ======
        # Database
        # csv_upload
        glue.CfnDatabase(
            self,
            'CsvUploadDatabase',
            catalog_id=iam_config['account_id'],
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores upload csv data',
                name='csv_upload'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # itada_aws
        glue.CfnDatabase(
            self,
            'ItadaAwsDatabase',
            catalog_id=iam_config['account_id'],
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores data in the Cloud',
                name='itada_aws'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # metadata_center
        glue.CfnDatabase(
            self,
            'MetadataCenterDatabase',
            catalog_id=iam_config['account_id'],
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores metadata such as lineage and build history',
                name='metadata_center'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # postgres_onprem
        glue.CfnDatabase(
            self,
            'PostgresOnpremDatabase',
            catalog_id=iam_config['account_id'],
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores on-premise data from data source',
                name='postgres_onprem'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # Connection
        # itada_dpos_db_connection
        pwn_subnet = ec2_config['pwn_subnets'].subnets[0]
        glue.CfnConnection(
            self,
            'ItadaDposDbConnection',
            catalog_id=iam_config['account_id'],
            connection_input=glue.CfnConnection.ConnectionInputProperty(
                name='itada_dpos_db_connection',
                connection_type='JDBC',
                connection_properties={
                    'JDBC_CONNECTION_URL': os.getenv('ITADADPOSDB_CONNECTION_URL'),
                    'JDBC_ENFORCE_SSL': os.getenv('ITADADPOSDB_ENFORCE_SSL'),
                    'USERNAME': os.getenv('ITADADPOSDB_USERNAME'),
                    'PASSWORD': os.getenv('ITADADPOSDB_USERPW')
                },
                physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                    availability_zone=pwn_subnet.availability_zone,
                    subnet_id=pwn_subnet.subnet_id,
                    security_group_id_list=[ec2_config['glue_sg'].security_group_id],
                ),
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # develop-workdb-connection
        glue.CfnConnection(
            self,
            'DevelopWorkDbConnection',
            catalog_id=iam_config['account_id'],
            connection_input=glue.CfnConnection.ConnectionInputProperty(
                name='develop-workdb-connection',
                connection_type='JDBC',
                connection_properties={
                    'JDBC_CONNECTION_URL': os.getenv('DEVELOPDWORKDB_CONNECTION_URL'),
                    'JDBC_ENFORCE_SSL': os.getenv('DEVELOPDWORKDB_ENFORCE_SSL'),
                    'USERNAME': os.getenv('DEVELOPDWORKDB_USERNAME'),
                    'PASSWORD': os.getenv('DEVELOPDWORKDB_USERPW')
                },
                physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                    availability_zone=pwn_subnet.availability_zone,
                    subnet_id=pwn_subnet.subnet_id,
                    security_group_id_list=[ec2_config['glue_sg'].security_group_id],
                ),
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # develop-redshift-connection
        glue.CfnConnection(
            self,
            'DevelopRedshiftConnection',
            catalog_id=iam_config['account_id'],
            connection_input=glue.CfnConnection.ConnectionInputProperty(
                name='develop-redshift-connection',
                connection_type='JDBC',
                connection_properties={
                    'JDBC_CONNECTION_URL': (
                        'jdbc:redshift://' + redshift_config['attr_endpoint_address'] + ':'
                        + redshift_config['attr_endpoint_port'] + '/' + redshift_config['db_name']
                    ),
                    'JDBC_ENFORCE_SSL': os.getenv('DEVELOPREDSHIFT_ENFORCE_SSL'),
                    'USERNAME': os.getenv('DEVELOPREDSHIFT_USERNAME'),
                    'PASSWORD': os.getenv('DEVELOPREDSHIFT_USERPW')
                },
                physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                    availability_zone=pwn_subnet.availability_zone,
                    subnet_id=pwn_subnet.subnet_id,
                    security_group_id_list=[ec2_config['glue_sg'].security_group_id],
                ),
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # Job
        # work_db shared arguments
        job_shared_args = {
            '--extra-py-files': 's3://itada-datasource/python-libs/data_lineage.zip,s3://itada-datasource/python-libs/etl_utils.zip',
            '--class': 'GlueApp',
            '--BUCKET_NAME': 'itada-datasource',
            '--CLIENT_ID': 'ae59c4e9-0032-4122-a6ad-0f9484c71736'
        }

        # itada_work_db_raw
        glue.CfnJob(
            self,
            'ItadaWorkDbRaw',
            command=glue.CfnJob.JobCommandProperty(
                name='glueetl',
                python_version='3',
                script_location=os.getenv('ITADAWORKDBRAW_JOB_SCRIPT')
            ),
            role=iam_config['gluejob_role_arn'],
            default_arguments={
                **job_shared_args,
                '--DATASOURCE_NAME': 'postgres_onprem',
                '--DATA_CATALOG_PREFIX': 'work_db_public_',
                '--RAW_PATH': 's3://itada-datasource/work_db/raw',
                '--STAGING_PATH': 's3://itada-datasource/work_db/staging'
            },
            description='Glue Job to extract work_db raw data',
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=1
            ),
            glue_version='3.0',
            max_retries=0,
            name='itada_work_db_raw',
            number_of_workers=2,
            worker_type='G.1X'
        )

        # itada_work_db_clean
        glue.CfnJob(
            self,
            'ItadaWorkDbClean',
            command=glue.CfnJob.JobCommandProperty(
                name='glueetl',
                python_version='3',
                script_location=os.getenv('ITADAWORKDBCLEAN_JOB_SCRIPT')
            ),
            role=iam_config['gluejob_role_arn'],
            default_arguments={
                **job_shared_args,
                '--ITADA_CLEAN_PATH': 's3://itada-datasource/work_db/clean/',
                '--ITADA_RAW_PATH': 's3://itada-datasource/work_db/raw/',
                '--SELECTED_COLUMN': 'company_id',
                '--STAGE': 'clean'
            },
            description='Glue Job to clean work_db raw data',
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=1
            ),
            glue_version='3.0',
            max_retries=0,
            name='itada_work_db_clean',
            number_of_workers=2,
            worker_type='G.1X'
        )

        # itada_work_db_transformation
        glue.CfnJob(
            self,
            'ItadaWorkDbTransformation',
            command=glue.CfnJob.JobCommandProperty(
                name='glueetl',
                python_version='3',
                script_location=os.getenv('ITADAWORKDBTRANSFORMATION_JOB_SCRIPT')
            ),
            role=iam_config['gluejob_role_arn'],
            default_arguments={
                **job_shared_args,
                '--ITADA_CLEAN_PATH': 's3://itada-datasource/work_db/clean/',
                '--ITADA_TRANSFORMATION_PATH': 's3://itada-datasource/work_db/transformation/',
                '--STAGE': 'transformation'
            },
            description='Glue Job to transform work_db cleaned data',
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=1
            ),
            glue_version='3.0',
            max_retries=0,
            name='itada_work_db_transformation',
            number_of_workers=2,
            worker_type='G.1X'
        )

        # itada_dpos_db_raw
        glue.CfnJob(
            self,
            'ItadaDposDbRaw',
            command=glue.CfnJob.JobCommandProperty(
                name='glueetl',
                python_version='3',
                script_location=os.getenv('ITADADPOSDBRAW_JOB_SCRIPT')
            ),
            role=iam_config['gluejob_role_arn'],
            default_arguments={
                **job_shared_args,
                '--DATASOURCE_NAME': 'postgres_onprem',
                '--DATA_CATALOG_PREFIX': 'dpos_db_public_',
                '--RAW_PATH': 's3://itada-datasource/dpos_db/raw',
                '--STAGING_PATH': 's3://itada-datasource/dpos_db/staging'
            },
            description='Glue Job to extract dpos_db raw data',
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=1
            ),
            glue_version='3.0',
            max_retries=0,
            name='itada_dpos_db_raw',
            number_of_workers=2,
            worker_type='G.1X'
        )

        # itada_dpos_db_clean
        glue.CfnJob(
            self,
            'ItadaDposDbClean',
            command=glue.CfnJob.JobCommandProperty(
                name='glueetl',
                python_version='3',
                script_location=os.getenv('ITADADPOSDBCLEAN_JOB_SCRIPT')
            ),
            role=iam_config['gluejob_role_arn'],
            default_arguments={
                **job_shared_args,
                '--ITADA_CLEAN_PATH': 's3://itada-datasource/work_db/clean/',
                '--ITADA_RAW_PATH': 's3://itada-datasource/work_db/raw/',
                '--SELECTED_COLUMN': 'company_id',
                '--STAGE': 'clean'
            },
            description='Glue Job to clean dpos_db raw data',
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=1
            ),
            glue_version='3.0',
            max_retries=0,
            name='itada_dpos_db_clean',
            number_of_workers=2,
            worker_type='G.1X'
        )