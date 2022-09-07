import os
from dotenv import load_dotenv
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Fn,
    CfnTag,
    SecretValue,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_redshift as redshift,
    aws_rds as rds,
    aws_glue as glue
)
from constructs import Construct


load_dotenv()


class ResourceMigrationCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account_id = Fn.ref('AWS::AccountId')

        # The code that defines your stack goes here
        # ====== IAM ======
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


        # ====== EC2 ======
        # VPC
        itada_vpc = ec2.Vpc(
            self,
            'ItadaVpc',
            cidr='10.0.0.0/16',
            max_azs=1
        )
        itada_vpc.apply_removal_policy(RemovalPolicy.DESTROY)

        # Extract subnet information
        pwn_subnet_selection = itada_vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
        )

        public_subnet_selection = itada_vpc.select_subnets(
            subnet_type=ec2.SubnetType.PUBLIC
        )

        # Security group
        # amundsen-alb-sg
        amundsenalb_sg = ec2.SecurityGroup(
            self,
            'AmundsenAlbSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Amundsen ALB',
            security_group_name='amundsen-alb-sg'
        )
        amundsenalb_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(80))
        amundsenalb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(443))

        # amundsen-sg
        amundsen_sg = ec2.SecurityGroup(
            self,
            'AmundsenSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Amundsen EC2',
            security_group_name='amundsen-sg'
        )
        amundsen_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        amundsen_sg.add_ingress_rule(ec2.Peer.security_group_id(amundsenalb_sg.security_group_id), ec2.Port.tcp(80))

        # chart-service-alb-sg
        chartservicealb_sg = ec2.SecurityGroup(
            self,
            'ChartServiceAlbSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Chart Service ALB',
            security_group_name='chart-service-alb-sg'
        )
        chartservicealb_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(80))
        chartservicealb_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(443))

        # chart-service-sg
        chartservice_sg = ec2.SecurityGroup(
            self,
            'ChartServiceSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Chart Service EC2',
            security_group_name='chart-service-sg'
        )
        chartservice_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        chartservice_sg.add_ingress_rule(ec2.Peer.security_group_id(chartservicealb_sg.security_group_id), ec2.Port.tcp(8088))

        # aurora-cluster-sg
        auroracluster_sg = ec2.SecurityGroup(
            self,
            'AuroraClusterSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Aurora Cluster',
            security_group_name='aurora-cluster-sg'
        )
        auroracluster_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        auroracluster_sg.add_ingress_rule(ec2.Peer.security_group_id(itada_vpc.vpc_default_security_group), ec2.Port.tcp(5432))

        # redshift-cluster-sg
        redshiftcluster_sg = ec2.SecurityGroup(
            self,
            'RedshiftClusterSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Redshift Cluster',
            security_group_name='redshift-cluster-sg'
        )
        redshiftcluster_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        redshiftcluster_sg.add_ingress_rule(ec2.Peer.security_group_id(itada_vpc.vpc_default_security_group), ec2.Port.tcp(5439))
        redshiftcluster_sg.add_ingress_rule(ec2.Peer.security_group_id(auroracluster_sg.security_group_id), ec2.Port.tcp(5439))
        redshiftcluster_sg.add_ingress_rule(ec2.Peer.security_group_id(chartservice_sg.security_group_id), ec2.Port.tcp(5439))

        # glue-sg
        glue_sg = ec2.SecurityGroup(
            self,
            'GlueSg',
            vpc=itada_vpc,
            allow_all_outbound=True,
            description='security group for Glue',
            security_group_name='glue-sg'
        )
        glue_sg.apply_removal_policy(RemovalPolicy.DESTROY)
        glue_sg.add_ingress_rule(ec2.Peer.security_group_id(glue_sg.security_group_id), ec2.Port.all_tcp())


        # ====== S3 ======
        # itada-datasource
        s3.Bucket(
            self,
            'ItadaDatasourceBucket',
            bucket_name='itada-datasource',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # metadata-center
        s3.Bucket(
            self,
            'MetadataCenterBucket',
            bucket_name='metadata-center',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # itada-athena-query-result
        s3.Bucket(
            self,
            'ItadaAthenaQueryResultBucket',
            bucket_name='itada-athena-query-result',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )


        # ====== REDSHIFT ======
        # Cluster subnet group
        redshift.CfnClusterSubnetGroup(
            self,
            'RedshiftClusterSubnetGroup',
            description='Group of public subnets for Redshift to deploy',
            subnet_ids=public_subnet_selection.subnet_ids,
            tags=[CfnTag(key='Name', value='redshift-cluster-subnet-group')]
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        redshift_cluster = redshift.CfnCluster(
            self,
            'RedshiftCluster',
            cluster_type='multi-node',
            db_name='dev',
            master_username=os.getenv('DEVELOPREDSHIFT_USERNAME'),
            master_user_password=os.getenv('DEVELOPREDSHIFT_USERPW'),
            node_type='dc2.large',
            cluster_identifier='itada-redshift-cluster',
            cluster_subnet_group_name='redshift-cluster-subnet-group',
            number_of_nodes=1,
            port=5439,
            vpc_security_group_ids=[redshiftcluster_sg.security_group_id]
        )
        redshift_cluster.apply_removal_policy(RemovalPolicy.DESTROY)


        # ====== AURORA ======
        auroracluster_subnet_group = rds.SubnetGroup(
            self,
            'AuroraClusterSubnetGroup',
            description='Group of public subnets for Aurora to deploy',
            vpc=itada_vpc,
            removal_policy=RemovalPolicy.DESTROY,
            subnet_group_name='aurora-cluster-subnet-group',
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        rds.ServerlessCluster(
            self,
            'AuroraCluster',
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=rds.AuroraPostgresEngineVersion.VER_13_6),
            cluster_identifier='itada-aurora-cluster',
            credentials=rds.Credentials.from_password(
                username=os.getenv('AURORACLUSTER_USERNAME'),
                password=SecretValue.unsafe_plain_text(os.getenv('AURORACLUSTER_USERPW'))
            ),
            default_database_name='dev',
            security_groups=[auroracluster_sg],
            enable_data_api=True,
            removal_policy=RemovalPolicy.DESTROY,
            subnet_group=auroracluster_subnet_group,
            vpc=itada_vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )


        # ====== GLUE ======
        # Database
        # csv_upload
        glue.CfnDatabase(
            self,
            'CsvUploadDatabase',
            catalog_id=account_id,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores upload csv data',
                name='csv_upload'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # itada_aws
        glue.CfnDatabase(
            self,
            'ItadaAwsDatabase',
            catalog_id=account_id,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores data in the Cloud',
                name='itada_aws'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # metadata_center
        glue.CfnDatabase(
            self,
            'MetadataCenterDatabase',
            catalog_id=account_id,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores metadata such as lineage and build history',
                name='metadata_center'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # postgres_onprem
        glue.CfnDatabase(
            self,
            'PostgresOnpremDatabase',
            catalog_id=account_id,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                description='Database that stores on-premise data from data source',
                name='postgres_onprem'
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # Connection
        # itada_dpos_db_connection
        pwn_subnet = pwn_subnet_selection.subnets[0]
        glue.CfnConnection(
            self,
            'ItadaDposDbConnection',
            catalog_id=account_id,
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
                    security_group_id_list=[glue_sg.security_group_id],
                ),
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # develop-workdb-connection
        glue.CfnConnection(
            self,
            'DevelopWorkDbConnection',
            catalog_id=account_id,
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
                    security_group_id_list=[glue_sg.security_group_id],
                ),
            )
        ).apply_removal_policy(RemovalPolicy.DESTROY)

        # develop-redshift-connection
        glue.CfnConnection(
            self,
            'DevelopRedshiftConnection',
            catalog_id=account_id,
            connection_input=glue.CfnConnection.ConnectionInputProperty(
                name='develop-redshift-connection',
                connection_type='JDBC',
                connection_properties={
                    'JDBC_CONNECTION_URL': (
                        'jdbc:redshift://' + redshift_cluster.attr_endpoint_address + ':'
                        + redshift_cluster.attr_endpoint_port + '/' + redshift_cluster.db_name
                    ),
                    'JDBC_ENFORCE_SSL': os.getenv('DEVELOPREDSHIFT_ENFORCE_SSL'),
                    'USERNAME': os.getenv('DEVELOPREDSHIFT_USERNAME'),
                    'PASSWORD': os.getenv('DEVELOPREDSHIFT_USERPW')
                },
                physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                    availability_zone=pwn_subnet.availability_zone,
                    subnet_id=pwn_subnet.subnet_id,
                    security_group_id_list=[glue_sg.security_group_id],
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
            role=gluejob_role.role_arn,
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
            role=gluejob_role.role_arn,
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
            role=gluejob_role.role_arn,
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
            role=gluejob_role.role_arn,
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
            role=gluejob_role.role_arn,
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