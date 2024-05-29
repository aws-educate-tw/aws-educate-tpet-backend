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
    # Implement parsing of multipart/form-data here
    
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

        # Check and update DynamoDB table
        response = dynamodb.query(
            TableName=table_name,
            IndexName='file_name_index',
            KeyConditionExpression='file_name = :file_name',
            ExpressionAttributeValues={':file_name': {'S': file_name}}
        )
        file_exists = bool(response['Items'])

        if file_exists:
            file_id = response['Items'][0]['file_id']['S']
            s3.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)
            update_expression = 'SET update_at = :update_at, file_size = :file_size, file_path = :file_path'
        else:
            file_id = uuid.uuid4().hex
            s3.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)
            update_expression = 'SET create_at = :create_at, update_at = :update_at, file_path = :file_path, file_name = :file_name, file_extension = :file_extension, file_size = :file_size, uploader_id = :uploader_id'

        # Common update parameters
        now = datetime.now() + timedelta(hours=8)
        formatted_now = now.strftime(TIME_FORMAT) + TIMEZONE_OFFSET

        expression_attribute_values = {
            ':update_at': {'S': formatted_now},
            ':file_size': {'N': str(file_size)},
            ':file_path': {'S': s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': file_name}, ExpiresIn=3600)}
        }

        if not file_exists:
            expression_attribute_values.update({
                ':create_at': {'S': formatted_now},
                ':file_name': {'S': file_name},
                ':file_extension': {'S': file_extension},
                ':uploader_id': {'S': uploader_id}
            })

        dynamodb.update_item(
            TableName=table_name,
            Key={'file_id': {'S': file_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'message': 'File uploaded and metadata saved successfully',
                'request_id': context.aws_request_id,
                'timestamp': formatted_now,
                'S3URL': s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': file_name}, ExpiresIn=3600)
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
