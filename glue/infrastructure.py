import os
from typing import TypedDict, List
from aws_cdk import (
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_glue as glue
)
from constructs import Construct


class GlueConfig(TypedDict):
    pass


class Glue(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        catalog_id: str,
        pwn_subnet: ec2.Subnet,
        glue_sg_id_list: List[str],
        rs_attr_endpoint_address: str,
        rs_attr_endpoint_port: str,
        rs_db_name: str,
        gluejob_role_arn: str
    ):
        super().__init__(scope, id)

        # Database
        db_configs = {
            'CsvUploadDatabase': {
                'database_input': {
                    'description': 'Database that stores upload csv data',
                    'name': 'csv_upload'
                }
            },
            'ItadaAwsDatabase': {
                'database_input': {
                    'description': 'Database that stores data in the Cloud',
                    'name': 'itada_aws'
                }
            },
            'MetadataCenterDatabase': {
                'database_input': {
                    'description': 'Database that stores metadata such as lineage and build history',
                    'name': 'metadata_center'
                }
            },
            'PostgresOnpremDatabase': {
                'database_input': {
                    'description': 'Database that stores on-premise data from data source',
                    'name': 'postgres_onprem'
                }
            }
        }

        for db_id, db_props in db_configs.items():
            glue.CfnDatabase(
                self,
                db_id,
                catalog_id=catalog_id,
                database_input=glue.CfnDatabase.DatabaseInputProperty(**db_props['database_input'])
            ).apply_removal_policy(RemovalPolicy.DESTROY)

        # Connection
        conn_configs = {
            'ItadaDposDbConnection': {
                'connection_input': {
                    'name': 'itada_dpos_db_connection',
                    'connection_properties': {
                        'JDBC_CONNECTION_URL': os.getenv('ITADADPOSDB_CONNECTION_URL'),
                        'JDBC_ENFORCE_SSL': os.getenv('ITADADPOSDB_ENFORCE_SSL'),
                        'USERNAME': os.getenv('ITADADPOSDB_USERNAME'),
                        'PASSWORD': os.getenv('ITADADPOSDB_USERPW')
                    }
                }
            },
            'DevelopWorkDbConnection': {
                'connection_input': {
                    'name': 'develop-workdb-connection',
                    'connection_properties': {
                        'JDBC_CONNECTION_URL': os.getenv('DEVELOPDWORKDB_CONNECTION_URL'),
                        'JDBC_ENFORCE_SSL': os.getenv('DEVELOPDWORKDB_ENFORCE_SSL'),
                        'USERNAME': os.getenv('DEVELOPDWORKDB_USERNAME'),
                        'PASSWORD': os.getenv('DEVELOPDWORKDB_USERPW')
                    }
                }
            },
            'DevelopRedshiftConnection': {
                'connection_input': {
                    'name': 'develop-redshift-connection',
                    'connection_properties': {
                        'JDBC_CONNECTION_URL': (
                            'jdbc:redshift://' + rs_attr_endpoint_address + ':'
                            + rs_attr_endpoint_port + '/' + rs_db_name
                        ),
                        'JDBC_ENFORCE_SSL': os.getenv('DEVELOPREDSHIFT_ENFORCE_SSL'),
                        'USERNAME': os.getenv('DEVELOPREDSHIFT_USERNAME'),
                        'PASSWORD': os.getenv('DEVELOPREDSHIFT_USERPW')
                    }
                }
            },
        }

        for conn_id, conn_props in conn_configs.items():
            glue.CfnConnection(
                self,
                conn_id,
                catalog_id=catalog_id,
                connection_input=glue.CfnConnection.ConnectionInputProperty(
                    **conn_props['connection_input'],
                    connection_type='JDBC',
                    physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                        availability_zone=pwn_subnet.availability_zone,
                        subnet_id=pwn_subnet.subnet_id,
                        security_group_id_list=glue_sg_id_list #[ec2_config['glue_sg'].security_group_id],
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

        work_db_job_configs = {
            'ItadaWorkDbStaging': {
                'command': {
                    'script_location': os.getenv('ITADAWORKDBSTAGING_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--CONNECTION_NAME': 'develop-workdb-connection',
                    '--DATASOURCE_NAME': 'postgres_onprem',
                    '--DATA_CATALOG_PREFIX': 'work_db_public_',
                    '--LAST_BUILD_DATE_PATH': 'work_db/staging/last_build_date',
                    '--STAGING_PATH': 's3://itada-datasource/work_db/staging',
                    '--additional-python-modules': 'psycopg2-binary'
                },
                'description': 'Glue Job to extract work_db source data to staging',
                'name': 'itada_work_db_staging'
            },
            'ItadaWorkDbRaw': {
                'command': {
                    'script_location': os.getenv('ITADAWORKDBRAW_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--DATASOURCE_NAME': 'postgres_onprem',
                    '--DATA_CATALOG_PREFIX': 'work_db_public_',
                    '--RAW_PATH': 's3://itada-datasource/work_db/raw',
                    '--STAGING_PATH': 's3://itada-datasource/work_db/staging'
                },
                'description': 'Glue Job to upsert work_db raw data from staging',
                'name': 'itada_work_db_raw'
            },
            'ItadaWorkDbClean': {
                'command': {
                    'script_location': os.getenv('ITADAWORKDBCLEAN_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--ITADA_CLEAN_PATH': 's3://itada-datasource/work_db/clean/',
                    '--ITADA_RAW_PATH': 's3://itada-datasource/work_db/raw/',
                    '--SELECTED_COLUMN': 'company_id',
                    '--STAGE': 'clean'
                },
                'description': 'Glue Job to clean work_db raw data',
                'name': 'itada_work_db_clean'
            },
            'ItadaWorkDbTransformation': {
                'command': {
                    'script_location': os.getenv('ITADAWORKDBTRANSFORMATION_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--ITADA_CLEAN_PATH': 's3://itada-datasource/work_db/clean/',
                    '--ITADA_TRANSFORMATION_PATH': 's3://itada-datasource/work_db/transformation/',
                    '--STAGE': 'transformation'
                },
                'description': 'Glue Job to transform work_db cleaned data',
                'name': 'itada_work_db_transformation'
            }
        }

        for work_db_job_id, work_db_job_props in work_db_job_configs.items():
            glue.CfnJob(
                self,
                work_db_job_id,
                command=glue.CfnJob.JobCommandProperty(
                    name='glueetl',
                    python_version='3',
                    script_location=work_db_job_props['command']['script_location']
                ),
                role=gluejob_role_arn,
                default_arguments={
                    **job_shared_args,
                    **work_db_job_props['default_arguments']
                },
                description=work_db_job_props['description'],
                execution_property=glue.CfnJob.ExecutionPropertyProperty(
                    max_concurrent_runs=1
                ),
                glue_version='3.0',
                max_retries=0,
                name=work_db_job_props['name'],
                number_of_workers=2,
                worker_type='G.1X'
            ).apply_removal_policy(RemovalPolicy.DESTROY)

        dpos_db_job_configs = {
            'ItadaDposDbStaging': {
                'command': {
                    'script_location': os.getenv('ITADADPOSDBSTAGING_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--CONNECTION_NAME': 'itada_dpos_db_connection',
                    '--DATASOURCE_NAME': 'postgres_onprem',
                    '--DATA_CATALOG_PREFIX': 'dpos_db_public_',
                    '--LAST_BUILD_DATE_PATH': 'dpos_db/staging/last_build_date',
                    '--STAGING_PATH': 's3://itada-datasource/dpos_db/staging',
                    '--additional-python-modules': 'psycopg2-binary'
                },
                'description': 'Glue Job to extract dpos_db source data to staging',
                'name': 'itada_dpos_db_staging'
            },
            'ItadaDposDbRaw': {
                'command': {
                    'script_location': os.getenv('ITADADPOSDBRAW_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--DATASOURCE_NAME': 'postgres_onprem',
                    '--DATA_CATALOG_PREFIX': 'dpos_db_public_',
                    '--RAW_PATH': 's3://itada-datasource/dpos_db/raw',
                    '--STAGING_PATH': 's3://itada-datasource/dpos_db/staging'
                },
                'description': 'Glue Job to extract dpos_db raw data',
                'name': 'itada_dpos_db_raw'
            },
            'ItadaDposDbClean': {
                'command': {
                    'script_location': os.getenv('ITADADPOSDBCLEAN_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--ITADA_CLEAN_PATH': 's3://itada-datasource/dpos_db/clean/',
                    '--ITADA_RAW_PATH': 's3://itada-datasource/dpos_db/raw/',
                    '--STAGE': 'clean'
                },
                'description': 'Glue Job to clean dpos_db raw data',
                'name': 'itada_dpos_db_clean'
            },
            'ItadaDposDbTransformation': {
                'command': {
                    'script_location': os.getenv('ITADADPOSDBTRANSFORMATION_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--ITADA_CLEAN_PATH': 's3://itada-datasource/dpos_db/clean/',
                    '--ITADA_TRANSFORMATION_PATH': 's3://itada-datasource/dpos_db/transformation/'
                },
                'description': 'Glue Job to transform dpos_db cleaned data',
                'name': 'itada_dpos_db_transformation'
            }
        }

        for dpos_db_job_id, dpos_db_job_props in dpos_db_job_configs.items():
            glue.CfnJob(
                self,
                dpos_db_job_id,
                command=glue.CfnJob.JobCommandProperty(
                    name='glueetl',
                    python_version='3',
                    script_location=dpos_db_job_props['command']['script_location']
                ),
                role=gluejob_role_arn,
                default_arguments={
                    **job_shared_args,
                    **dpos_db_job_props['default_arguments']
                },
                description=dpos_db_job_props['description'],
                execution_property=glue.CfnJob.ExecutionPropertyProperty(
                    max_concurrent_runs=1
                ),
                glue_version='3.0',
                max_retries=0,
                name=dpos_db_job_props['name'],
                number_of_workers=2,
                worker_type='G.1X'
            ).apply_removal_policy(RemovalPolicy.DESTROY)
        
        # Aside jobs
        aside_job_configs = {
            # itada_upload_csv_to_parquet
            'ItadaUploadCsvToParquet': {
                'command': {
                    'script_location': os.getenv('ITADAUPLOADCSVTOPARQUET_JOB_SCRIPT')
                },
                'default_arguments': {
                    '--BUCKET_NAME': 'itada-datasource',
                    '--CSV_PATH': 'upload/raw/csv/',
                    '--PARQUET_PATH': 'upload/raw/parquet/',
                    '--class': 'GlueApp'
                },
                'description': 'Glue Job to convert upload csv file into parquet file',
                'name': 'itada_upload_csv_to_parquet'
            }
        }

        for aside_job_id, aside_job_props in aside_job_configs.items():
            glue.CfnJob(
                self,
                aside_job_id,
                command=glue.CfnJob.JobCommandProperty(
                    name='glueetl',
                    python_version='3',
                    script_location=aside_job_props['command']['script_location']
                ),
                role=gluejob_role_arn,
                default_arguments=aside_job_props['default_arguments'],
                description=aside_job_props['description'],
                execution_property=glue.CfnJob.ExecutionPropertyProperty(
                    max_concurrent_runs=1
                ),
                glue_version='3.0',
                max_retries=0,
                name=aside_job_props['name'],
                number_of_workers=2,
                worker_type='G.1X'
            ).apply_removal_policy(RemovalPolicy.DESTROY)

        # Configuration parameters
        self._config: GlueConfig = {}

    @property
    def config(self) -> GlueConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
