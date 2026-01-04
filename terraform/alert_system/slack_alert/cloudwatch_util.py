import json
import logging
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
cloudwatch = boto3.client("cloudwatch")


class CloudWatchError(Exception):
    """Custom exception for CloudWatch operations"""

    def __init__(self, message, status_code=500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_metric_chart(trigger_info):
    """
    Generate CloudWatch metric chart image data

    Args:
        trigger_info (dict): Alarm trigger information containing metric details

    Returns:
        dict: Chart data with 'data', 'filename', 'title' keys, or None if failed

    Raises:
        CloudWatchError: If required parameters are missing or API call fails
    """
    try:
        # Validate required parameters
        metric_name = trigger_info.get("MetricName")
        namespace = trigger_info.get("Namespace")

        if not metric_name or not namespace:
            error_msg = f"Missing required metric info: metric={metric_name}, namespace={namespace}"
            logger.warning(error_msg)
            raise CloudWatchError(error_msg, status_code=400)

        # Extract optional parameters with defaults
        dimensions = trigger_info.get("Dimensions", [])
        statistic = trigger_info.get("Statistic", "Average")
        period = trigger_info.get("Period", 300)

        logger.info(f"Fetching metric: {namespace}/{metric_name}")
        logger.info(f"Dimensions: {dimensions}")

        # Normalize statistic to proper case
        stat_mapping = {
            "AVERAGE": "Average",
            "SUM": "Sum",
            "MINIMUM": "Minimum",
            "MAXIMUM": "Maximum",
            "SAMPLECOUNT": "SampleCount",
        }
        normalized_stat = stat_mapping.get(statistic.upper(), statistic)

        # Build metric in simple array format - dimensions as alternating key/value pairs
        metric = [namespace, metric_name]

        # Add dimensions as alternating name/value pairs
        for dim in dimensions:
            if not isinstance(dim, dict) or "name" not in dim or "value" not in dim:
                logger.warning(f"Invalid dimension format: {dim}")
                continue
            metric.append(dim["name"])
            metric.append(dim["value"])

        # Add stat and period at the end as a dict
        metric.append({"stat": normalized_stat, "period": period})

        logger.info(f"Metric array: {metric}")

        # Build widget configuration
        widget = {
            "metrics": [metric],
            "view": "timeSeries",
            "stacked": False,
            "region": os.environ.get("AWS_REGION", "us-east-1"),
            "title": f"{metric_name} Metric",
            "period": period,
            "width": 800,
            "height": 400,
            "start": "-PT3H",
            "end": "PT0H",
            "yAxis": {"left": {"min": 0}},
        }

        # Add threshold annotation if available in trigger_info
        threshold = trigger_info.get("Threshold")
        if threshold is not None:
            try:
                threshold_value = float(threshold)
                widget["annotations"] = {
                    "horizontal": [
                        {
                            "label": f"Threshold ({threshold_value})",
                            "value": threshold_value,
                            "color": "#d13212",
                        }
                    ]
                }
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid threshold value: {threshold}, error: {e}")

        logger.info(f"Widget structure: {json.dumps(widget, indent=2)}")

        # Get metric widget image from CloudWatch
        logger.info("Fetching metric widget image from CloudWatch...")
        try:
            response = cloudwatch.get_metric_widget_image(
                MetricWidget=json.dumps(widget)
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"CloudWatch API error [{error_code}]: {error_msg}")

            if error_code == "InvalidParameterValue":
                raise CloudWatchError(f"Invalid metric parameters: {error_msg}", status_code=400) from e
            elif error_code == "ResourceNotFoundException":
                raise CloudWatchError(f"Metric not found: {error_msg}", status_code=404) from e
            elif error_code == "Throttling":
                raise CloudWatchError(f"API rate limit exceeded: {error_msg}", status_code=429) from e
            else:
                raise CloudWatchError(f"CloudWatch API error: {error_msg}", status_code=500) from e
        except BotoCoreError as e:
            logger.error(f"AWS SDK error: {e}")
            raise CloudWatchError(f"AWS SDK error: {str(e)}", status_code=500) from e
        
        # Validate response
        if "MetricWidgetImage" not in response:
            raise CloudWatchError(
                "No image data returned from CloudWatch", status_code=500
            )

        image_data = response["MetricWidgetImage"]

        if not image_data:
            raise CloudWatchError(
                "Empty image data returned from CloudWatch", status_code=500
            )

        logger.info(f"Successfully generated metric chart: {len(image_data)} bytes")

        # Return image data and metadata for later upload
        return {
            "data": image_data,
            "filename": f"{metric_name}_chart.png",
            "title": f"CloudWatch Metric: {metric_name}",
        }
        
    except CloudWatchError:
        # Re-raise CloudWatchError as-is
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error generating metric chart: {e}", exc_info=True)
        raise CloudWatchError(f"Unexpected error: {str(e)}", status_code=500) from e
