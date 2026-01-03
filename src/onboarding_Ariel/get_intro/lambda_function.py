import json


def lambda_handler(event, context):
    newbie_name = event.get("pathParameters", {}).get("newbie_name", "Ariel")

    response_body = {
        "name": newbie_name,
        "introduction": "Hi! I'm Ariel, part of the 8th Tech cohort, and I will be joining the TPET team as a backend developer. I enjoy listening to K-pop and playing the piano. Looking forward to working with everyone!",
        "onboarding_path": f"/onboarding/{newbie_name}",
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }
