from typing import TypedDict, List
from aws_cdk import (
    RemovalPolicy,
    Duration,
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_certificatemanager as certmanager,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_targets,
    aws_route53_targets as route53_targets
)
from constructs import Construct


class AlbConfig(TypedDict):
    pass


class Alb(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        hosted_zone_vpcs: List[ec2.Vpc],
        alb_vpc: ec2.Vpc,
        amundsen_instance = ec2.Instance,
        amundsenalb_sg: ec2.SecurityGroup,
        chartservice_instance = ec2.Instance,
        chartservicealb_sg: ec2.SecurityGroup
    ):
        super().__init__(scope, id)

        # Hosted zone
        metasolutions_hosted_zone = route53.HostedZone(
            self,
            'MetasolutionsHostedZone',
            vpcs=hosted_zone_vpcs,
            zone_name='metasolutions.ai'
        )

        metasolutions_hosted_zone.apply_removal_policy(RemovalPolicy.DESTROY)

        # Certificate
        metasolutions_certificate = certmanager.Certificate(
            self,
            'MetasolutionsCertificate',
            domain_name='metasolutions.ai',
            subject_alternative_names=['*.metasolutions.ai', 'metasolutions.ai', 'www.metasolutions.ai'],
            validation=certmanager.CertificateValidation.from_dns(
                hosted_zone=metasolutions_hosted_zone
            )
        )
        metasolutions_certificate.apply_removal_policy(RemovalPolicy.DESTROY)

        metasolutions_listener_certificate = elbv2.ListenerCertificate.from_arn(metasolutions_certificate.certificate_arn)
        
        alb_configs = {
            'Amundsen': {
                'tg': {
                    'name': 'itada-ec2-target-group',
                    'instance_target': amundsen_instance,
                    'port': 80,
                    'healthcheck_path': '/healthcheck'
                },
                'alb': {
                    'security_group': amundsenalb_sg,
                    'name': 'dataplatform-alb',
                },
                'route53_record': {
                    'id': 'Metasolutions',
                    'name': 'metasolutions.ai' 
                }
            },
            'ChartService': {
                'tg': {
                    'name': 'chart-tg',
                    'instance_target': chartservice_instance,
                    'port': 8088,
                    'healthcheck_path': '/health'
                },
                'alb': {
                    'security_group': chartservicealb_sg,
                    'name': 'chart-service-alb',
                },
                'route53_record': {
                    'id': 'ChartMetasolutions',
                    'name': 'chart.metasolutions.ai'
                }
            }
        }
        
        for alb_id, alb_props in alb_configs.items():
            # Target group
            tg = elbv2.ApplicationTargetGroup(
                self,
                alb_id + 'Tg',
                port=alb_props['tg']['port'],
                protocol=elbv2.ApplicationProtocol.HTTP,
                protocol_version=elbv2.ApplicationProtocolVersion.HTTP1,
                targets=[
                    elbv2_targets.InstanceTarget(alb_props['tg']['instance_target'])
                ],
                health_check=elbv2.HealthCheck(
                    path=alb_props['tg']['healthcheck_path']
                ),
                target_group_name=alb_props['tg']['name'],
                vpc=alb_vpc
            )

            # Elastic load balancer
            alb = elbv2.ApplicationLoadBalancer(
                self,
                alb_id + 'Alb',
                security_group=alb_props['alb']['security_group'],
                vpc=alb_vpc,
                load_balancer_name=alb_props['alb']['name'],
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PUBLIC
                )
            )
            alb.apply_removal_policy(RemovalPolicy.DESTROY)

            alb.add_listener(
                'HTTPS : 443',
                certificates=[metasolutions_listener_certificate],
                default_action=elbv2.ListenerAction.forward([tg]),
                port=443,
                ssl_policy=elbv2.SslPolicy.RECOMMENDED
            )

            alb.add_listener(
                'HTTPS : 80',
                default_action=elbv2.ListenerAction.redirect(port='443'),
                port=80
            )

            route53.ARecord(
                self,
                alb_props['route53_record']['id'] + 'ARecord',
                target=route53.RecordTarget(
                    alias_target=route53_targets.LoadBalancerTarget(alb)
                ),
                zone=metasolutions_hosted_zone,
                delete_existing=True,
                record_name=alb_props['route53_record']['name']
            ).apply_removal_policy(RemovalPolicy.DESTROY)

            route53.AaaaRecord(
                self,
                alb_props['route53_record']['id'] + 'AaaaRecord',
                target=route53.RecordTarget(
                    alias_target=route53_targets.LoadBalancerTarget(alb)
                ),
                zone=metasolutions_hosted_zone,
                delete_existing=True,
                record_name=alb_props['route53_record']['name']
            ).apply_removal_policy(RemovalPolicy.DESTROY)

        # Configuration parameters
        self._config: AlbConfig = {}

    @property
    def config(self) -> AlbConfig:
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
