from aws_cdk import CfnOutput, Duration, Stack
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_ecs_patterns as ecs_patterns
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_secretsmanager as secretsmanager
from constructs import Construct


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.IVpc,
        bucket: s3.IBucket,
        table: dynamodb.ITable,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        secret = secretsmanager.Secret.from_secret_name_v2(
            self, "TwelveLabsKey", "twelvelabs-api-key"
        )

        task_def = ecs.FargateTaskDefinition(
            self,
            "AppTask",
            cpu=1024,
            memory_limit_mib=4096,
            ephemeral_storage_gib=40,
        )

        task_def.add_container(
            "App",
            image=ecs.ContainerImage.from_asset("../app"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="compliance-app"),
            environment={
                "S3_BUCKET": bucket.bucket_name,
                "DYNAMODB_TABLE": table.table_name,
                "AWS_REGION": self.region,
                "TWELVELABS_INDEX_NAME": "ad-compliance",
            },
            secrets={
                "TWELVELABS_API_KEY": ecs.Secret.from_secrets_manager(secret),
            },
            port_mappings=[ecs.PortMapping(container_port=8501)],
        )

        bucket.grant_read_write(task_def.task_role)
        table.grant_read_write_data(task_def.task_role)

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "AppService",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            listener_port=80,
            public_load_balancer=True,
            assign_public_ip=False,
            health_check_grace_period=Duration.seconds(60),
            open_listener=False,  # Do NOT add 0.0.0.0/0 rule
        )

        # Restrict ALB SG: allow only CloudFront origin-facing IPs
        alb_sg = service.load_balancer.connections.security_groups[0]
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.prefix_list("pl-3b927c52"),  # CloudFront origin-facing (us-east-1)
            connection=ec2.Port.tcp(80),
            description="Allow inbound HTTP from CloudFront only",
        )

        service.target_group.configure_health_check(
            path="/_stcore/health",
            healthy_http_codes="200",
        )

        service.service.auto_scale_task_count(
            min_capacity=1, max_capacity=5
        ).scale_on_cpu_utilization("CpuScaling", target_utilization_percent=70)

        self.alb = service.load_balancer

        CfnOutput(self, "AlbDns", value=service.load_balancer.load_balancer_dns_name)
