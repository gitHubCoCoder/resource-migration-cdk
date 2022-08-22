import aws_cdk as core
import aws_cdk.assertions as assertions

from resource_migration_cdk.resource_migration_cdk_stack import ResourceMigrationCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in resource_migration_cdk/resource_migration_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ResourceMigrationCdkStack(app, "resource-migration-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
