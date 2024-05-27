import json
import boto3
import os

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']

    try:
        # Extract the file name from headers
        file_name = event['headers']['filename']
        
        # Extract file content from body (binary data)
        file_content = event['body'].encode('utf-8')

        # Upload the file to S3
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)

        # Construct the S3 URL for the uploaded file
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"
        
        return {
            'statusCode': 200,
            'body': json.dumps({'s3URL': s3_url}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    except KeyError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f"Missing key: {str(e)}"}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
