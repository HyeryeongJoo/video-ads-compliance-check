#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.network_stack import NetworkStack
from stacks.storage_stack import StorageStack
from stacks.compute_stack import ComputeStack
from stacks.cdn_stack import CdnStack

app = cdk.App()

env = cdk.Environment(region="us-east-1")

network = NetworkStack(app, "ComplianceNetwork", env=env)
storage = StorageStack(app, "ComplianceStorage", env=env)
compute = ComputeStack(
    app,
    "ComplianceCompute",
    vpc=network.vpc,
    bucket=storage.bucket,
    table=storage.table,
    env=env,
)
cdn = CdnStack(
    app,
    "ComplianceCdn",
    alb=compute.alb,
    env=env,
)

app.synth()
