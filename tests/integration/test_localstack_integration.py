import json
import os
import uuid

import boto3
import pytest

ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def sqs():
    return boto3.client("sqs", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)


@pytest.fixture
def events():
    return boto3.client("events", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)


def test_sqs_create_send_receive_delete(sqs):
    queue_name = f"test-queue-{uuid.uuid4().hex[:8]}"
    dlq_name = f"test-dlq-{uuid.uuid4().hex[:8]}"

    dlq = sqs.create_queue(QueueName=dlq_name)
    dlq_arn = sqs.get_queue_attributes(
        QueueUrl=dlq["QueueUrl"], AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    queue = sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "3"}
            )
        },
    )
    queue_url = queue["QueueUrl"]

    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"test": "data"}))

    received = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
    assert len(received.get("Messages", [])) == 1

    msg = json.loads(received["Messages"][0]["Body"])
    assert msg["test"] == "data"

    receipt = received["Messages"][0]["ReceiptHandle"]
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)

    sqs.delete_queue(QueueUrl=queue_url)
    sqs.delete_queue(QueueUrl=dlq["QueueUrl"])


def test_sqs_dlq_message_lands_after_max_receives(sqs):
    queue_name = f"test-dlq-flow-{uuid.uuid4().hex[:8]}"
    dlq_name = f"test-dlq-target-{uuid.uuid4().hex[:8]}"

    dlq = sqs.create_queue(QueueName=dlq_name)
    dlq_arn = sqs.get_queue_attributes(
        QueueUrl=dlq["QueueUrl"], AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    queue = sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "1"}
            )
        },
    )
    queue_url = queue["QueueUrl"]
    dlq_url = dlq["QueueUrl"]

    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"msg": "fail-me"}))

    for _ in range(2):
        received = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, VisibilityTimeout=0
        )
        if received.get("Messages"):
            sqs.change_message_visibility(
                QueueUrl=queue_url,
                ReceiptHandle=received["Messages"][0]["ReceiptHandle"],
                VisibilityTimeout=0,
            )

    dlq_msgs = sqs.receive_message(QueueUrl=dlq_url, MaxNumberOfMessages=1)
    assert len(dlq_msgs.get("Messages", [])) == 1

    sqs.delete_queue(QueueUrl=queue_url)
    sqs.delete_queue(QueueUrl=dlq_url)


def test_eventbridge_put_and_bus(events):
    bus_name = f"test-bus-{uuid.uuid4().hex[:8]}"

    events.create_event_bus(Name=bus_name)

    response = events.put_events(
        Entries=[
            {
                "EventBusName": bus_name,
                "Source": "test.source",
                "DetailType": "TestEvent",
                "Detail": json.dumps({"key": "value"}),
            }
        ]
    )
    assert response.get("FailedEntryCount", -1) == 0
    assert len(response.get("Entries", [])) > 0
    assert "EventId" in response["Entries"][0]

    events.delete_event_bus(Name=bus_name)


def test_eventbridge_rule_routes_to_sqs(sqs, events):
    bus_name = f"test-rule-bus-{uuid.uuid4().hex[:8]}"
    queue_name = f"test-rule-queue-{uuid.uuid4().hex[:8]}"

    events.create_event_bus(Name=bus_name)

    queue = sqs.create_queue(QueueName=queue_name)
    queue_arn = sqs.get_queue_attributes(
        QueueUrl=queue["QueueUrl"], AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    rule_name = "test-rule"
    events.put_rule(
        Name=rule_name,
        EventBusName=bus_name,
        EventPattern=json.dumps({"source": ["test.source"]}),
    )

    sqs.set_queue_attributes(
        QueueUrl=queue["QueueUrl"],
        Attributes={
            "Policy": json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "events.amazonaws.com"},
                            "Action": "sqs:SendMessage",
                            "Resource": queue_arn,
                        }
                    ],
                }
            )
        },
    )

    events.put_targets(
        Rule=rule_name,
        EventBusName=bus_name,
        Targets=[{"Id": "sqs-target", "Arn": queue_arn}],
    )

    events.put_events(
        Entries=[
            {
                "EventBusName": bus_name,
                "Source": "test.source",
                "DetailType": "TestEvent",
                "Detail": json.dumps({"hello": "world"}),
            }
        ]
    )

    import time

    time.sleep(2)

    received = sqs.receive_message(QueueUrl=queue["QueueUrl"], MaxNumberOfMessages=1)
    assert len(received.get("Messages", [])) == 1

    body = json.loads(received["Messages"][0]["Body"])
    assert body["source"] == "test.source"

    events.remove_targets(Rule=rule_name, EventBusName=bus_name, Ids=["sqs-target"])
    events.delete_rule(Name=rule_name, EventBusName=bus_name)
    events.delete_event_bus(Name=bus_name)
    sqs.delete_queue(QueueUrl=queue["QueueUrl"])
