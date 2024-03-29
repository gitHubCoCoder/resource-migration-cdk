import aws_cdk as core
import aws_cdk.assertions as assertions

from development import Itada

# example tests. To run these tests, uncomment this file along with the example
# resource in resource_migration_cdk/resource_migration_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Itada(app, "itada")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
