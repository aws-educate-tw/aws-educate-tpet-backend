import logging
import os
from datetime import datetime

import boto3
from utils import IncidentState

logger = logging.getLogger()

class IncidentRepository:
    """Repository for managing incident data in DynamoDB"""

    def __init__(self, table_name=None):
        """
        Initialize the incident repository.

        Args:
            table_name: DynamoDB table name. If None, uses INCIDENT_TABLE env var.
        """
        dynamodb = boto3.resource("dynamodb")
        self.table_name = table_name or os.environ["INCIDENT_TABLE"]
        self.table = dynamodb.Table(self.table_name)
        logger.info("Initialized IncidentRepository with table: %s", self.table_name)

    def get_incident(self, alarm_name):
        """
        Get an incident by alarm name.

        Args:
            alarm_name: Name of the alarm

        Returns:
            dict: Incident item or None if not found
        """
        try:
            resp = self.table.get_item(Key={"alarm_key": alarm_name})
            item = resp.get("Item")
            logger.info(
                "Retrieved incident for %s: %s",
                alarm_name,
                "found" if item else "not found",
            )
            return item
        except Exception as e:
            logger.error("Failed to get incident %s: %s", alarm_name, e)
            raise

    def create_incident(self, alarm_name, slack_channel, slack_ts, incident_state):
        """
        Create a new incident.

        Args:
            alarm_name: Name of the alarm
            slack_channel: Slack channel where message was posted
            slack_ts: Slack message timestamp
            incident_state: Initial state of the incident
        """
        now = datetime.utcnow().isoformat()

        try:
            self.table.put_item(
                Item={
                    "alarm_key": alarm_name,
                    "slack_channel": slack_channel,
                    "slack_ts": slack_ts,
                    "last_state": incident_state,
                    "incident_open": True,
                    "updated_at": now,
                }
            )
            logger.info("Created new incident for %s", alarm_name)
        except Exception as e:
            logger.error("Failed to create incident %s: %s", alarm_name, e)
            raise

    def update_incident_state(self, alarm_name, incident_state):
        """
        Update the state of an incident.

        Args:
            alarm_name: Name of the alarm
            incident_state: New state of the incident
        """
        now = datetime.utcnow().isoformat()

        try:
            self.table.update_item(
                Key={"alarm_key": alarm_name},
                UpdateExpression="SET last_state = :s, updated_at = :t",
                ExpressionAttributeValues={":s": incident_state, ":t": now},
            )
            logger.info("Updated incident state for %s to %s", alarm_name, incident_state)
        except Exception as e:
            logger.error("Failed to update incident state %s: %s", alarm_name, e)
            raise

    def close_incident(self, alarm_name, incident_state=IncidentState.RESOLVED.value):
        """
        Close an incident.

        Args:
            alarm_name: Name of the alarm
            incident_state: Final state of the incident (default: RESOLVED)
        """
        now = datetime.utcnow().isoformat()

        try:
            self.table.update_item(
                Key={"alarm_key": alarm_name},
                UpdateExpression="SET incident_open = :c, last_state = :s, updated_at = :t",
                ExpressionAttributeValues={
                    ":c": False,
                    ":s": incident_state,
                    ":t": now,
                },
            )
            logger.info("Closed incident for %s", alarm_name)
        except Exception as e:
            logger.error("Failed to close incident %s: %s", alarm_name, e)
            raise
