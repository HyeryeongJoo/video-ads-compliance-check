from aws_cdk import CfnOutput, Stack
import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_cloudfront_origins as origins
import aws_cdk.aws_elasticloadbalancingv2 as elbv2
from constructs import Construct


class CdnStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        alb: elbv2.IApplicationLoadBalancer,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        origin = origins.HttpOrigin(
            alb.load_balancer_dns_name,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        )

        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
            comment="Video Ad Compliance System",
        )

        CfnOutput(
            self,
            "AppUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="CloudFront HTTPS URL",
        )
