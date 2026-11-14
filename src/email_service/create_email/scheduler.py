import json
import os
import uuid
from datetime import timedelta

import boto3
import time_util

SCHEDULE_GROUP_NAME = os.getenv("SCHEDULE_GROUP_NAME")
SCHEDULER_ROLE_ARN = os.getenv("SCHEDULER_ROLE_ARN")
DISPATCH_SCHEDULED_RUN_LAMBDA_ARN = os.getenv("DISPATCH_SCHEDULED_RUN_LAMBDA_ARN")

scheduler_client = boto3.client("scheduler")


def create_run_schedule(run_id: str, scheduled_at: str) -> str:
    """Invoke dispatch_scheduled_run once, one minute after the planned send time."""
    if not all(
        (
            SCHEDULE_GROUP_NAME,
            SCHEDULER_ROLE_ARN,
            DISPATCH_SCHEDULED_RUN_LAMBDA_ARN,
        )
    ):
        raise ValueError("Scheduled email Scheduler configuration is missing")

    trigger_at = time_util.parse_iso8601_to_datetime(scheduled_at) + timedelta(
        minutes=1
    )
    response = scheduler_client.create_schedule(
        Name=f"scheduled-run-{run_id}",
        GroupName=SCHEDULE_GROUP_NAME,
        # Keep retried requests idempotent if writing the returned ARN fails.
        ClientToken=uuid.uuid5(
            uuid.NAMESPACE_URL, f"{SCHEDULE_GROUP_NAME}/{run_id}/{scheduled_at}"
        ).hex,
        ScheduleExpression=f"at({trigger_at.strftime('%Y-%m-%dT%H:%M:%S')})",
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        ActionAfterCompletion="DELETE",
        State="ENABLED",
        Target={
            "Arn": DISPATCH_SCHEDULED_RUN_LAMBDA_ARN,
            "RoleArn": SCHEDULER_ROLE_ARN,
            "Input": json.dumps({"run_id": run_id}),
            "RetryPolicy": {"MaximumRetryAttempts": 0},
        },
    )
    return response["ScheduleArn"]
