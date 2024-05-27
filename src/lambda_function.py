import json
import boto3
import os

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    file_name = json.loads(event['body'])['filename']

    try:
        presigned_url = s3.generate_presigned_url('put_object',
                                                  Params={'Bucket': bucket_name, 'Key': file_name},
                                                  ExpiresIn=3600)
        return {
            'statusCode': 200,
            'body': json.dumps({'uploadURL': presigned_url}),
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
