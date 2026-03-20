from aws_cdk import Duration, RemovalPolicy, Stack
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_s3 as s3
from constructs import Construct


class StorageStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        self.bucket = s3.Bucket(
            self,
            "VideoAssets",
            bucket_name=None,  # auto-generate
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CleanupVideos",
                    prefix="videos/",
                    expiration=Duration.days(7),
                ),
            ],
        )

        self.table = dynamodb.Table(
            self,
            "ComplianceResults",
            partition_key=dynamodb.Attribute(
                name="request_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )
