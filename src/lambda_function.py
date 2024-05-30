import json
import boto3
import os
import uuid
from datetime import datetime, timedelta
import cgi
from io import BytesIO

CONTENT_TYPE_JSON = 'application/json'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
TIMEZONE_OFFSET = '+08:00'

def parse_multipart(body, boundary):
    environ = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_TYPE': f'multipart/form-data; boundary={boundary}'
    }
    fp = BytesIO(body.encode('utf-8'))
    form = cgi.FieldStorage(fp=fp, environ=environ, keep_blank_values=True)
    
    return {
        'filename': form['file'].filename,
        'fileContent': form['file'].file.read()
    }
    
def lambda_handler(event, context):
    s3 = boto3.client('s3')
    dynamodb = boto3.client('dynamodb')
    bucket_name = os.environ['BUCKET_NAME']
    table_name = os.environ['TABLE_NAME']
    uploader_id = 'richie'

    try:
        # Parse the multipart/form-data
        content_type_header = event['headers']['Content-Type']
        boundary = content_type_header.split('=')[1]
        body = event['body']
        parsed_body = parse_multipart(body, boundary)
        
        original_file_name = parsed_body['filename']
        file_name = original_file_name.split('.')[0]
        file_extension = original_file_name.split('.')[-1]
        file_content = parsed_body['fileContent']
        file_size = len(file_content)

        # Upload file to S3
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)
        
        # Generate file metadata
        now = datetime.now() + timedelta(hours=8)
        formatted_now = now.strftime(TIME_FORMAT) + TIMEZONE_OFFSET
        file_id = uuid.uuid4().hex
        file_path = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': file_name}, ExpiresIn=3600)

        # Save metadata to DynamoDB
        dynamodb.put_item(
            TableName=table_name,
            Item={
                'file_id': {'S': file_id},
                'create_at': {'S': formatted_now},
                'update_at': {'S': formatted_now},
                'file_path': {'S': file_path},
                'file_name': {'S': file_name},
                'file_extension': {'S': file_extension},
                'file_size': {'N': str(file_size)},
                'uploader_id': {'S': uploader_id}
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'message': 'File uploaded and metadata saved successfully',
                'file_id': file_id,
                'request_id': context.aws_request_id,
                'timestamp': formatted_now,
                'S3URL': file_path,
            }),
            'headers': {
                'Content-Type': CONTENT_TYPE_JSON,
                'Access-Control-Allow-Origin': '*'
            }
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'status': 'error',
                'message': 'Internal server error',
                'request_id': context.aws_request_id,
                'timestamp': datetime.now().strftime(TIME_FORMAT) + TIMEZONE_OFFSET
            }),
            'headers': {
                'Content-Type': CONTENT_TYPE_JSON,
                'Access-Control-Allow-Origin': '*'
            }
        }
