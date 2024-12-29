import json
import logging

import boto3

# Initialize AWS Lambda client and logger
lambda_client = boto3.client("lambda")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_prewarm_functions():
    """
    Fetch all Lambda functions and filter those with the tag: Prewarm=true.
    This function supports pagination to handle a large number of Lambda functions.

    Returns:
        list: A list of function names that require prewarming.
    """
    try:
        functions = []
        next_marker = None  # Marker for pagination

        # Iterate through all pages of Lambda functions
        while True:
            if next_marker:
                response = lambda_client.list_functions(Marker=next_marker)
            else:
                response = lambda_client.list_functions()

            # Check each function's tags to identify prewarm candidates
            for func in response["Functions"]:
                function_name = func["FunctionName"]
                function_arn = func["FunctionArn"]

                # Retrieve tags for the current function
                tags = lambda_client.list_tags(Resource=function_arn)
                if tags.get("Tags", {}).get("Prewarm") == "true":
                    functions.append(function_name)

            # Check if there are more pages
            next_marker = response.get("NextMarker")
            if not next_marker:
                break

        logger.info("Found %d functions to prewarm: %s", len(functions), functions)
        return functions
    except Exception as e:
        logger.error("Error while fetching functions: %s", e)
        raise


def invoke_lambda(function_name):
    """
    Trigger a specified Lambda function to keep it warm.

    Args:
        function_name (str): The name of the Lambda function to prewarm.
    """
    try:
        # Use Event invocation type to avoid blocking
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",  # Asynchronous invocation to reduce latency
            Payload=json.dumps({"action": "prewarm"}),  # Send a custom prewarm signal
        )
        logger.info("Successfully prewarmed %s", function_name)
    except Exception as e:
        logger.error("Failed to prewarm %s: %s", function_name, e)


def lambda_handler(event, context):
    """
    Entry point for the Lambda function. Retrieves the list of Lambda functions to prewarm
    and invokes them asynchronously.

    Args:
        event (dict): AWS event data (not used in this implementation).
        context (object): AWS Lambda context object (not used in this implementation).

    Returns:
        dict: A status object with the results of the prewarm operation.
    """
    logger.info("Starting prewarmer...")
    try:
        # Step 1: Get the list of functions to prewarm
        prewarm_functions = get_prewarm_functions()

        # Step 2: Invoke each function asynchronously
        for function_name in prewarm_functions:
            invoke_lambda(function_name)

        logger.info("Prewarm process completed.")
        return {"status": "SUCCESS", "prewarmed_functions": prewarm_functions}
    except Exception as e:
        logger.error("Prewarmer encountered an error: %s", e)
        return {"status": "ERROR", "message": str(e)}
