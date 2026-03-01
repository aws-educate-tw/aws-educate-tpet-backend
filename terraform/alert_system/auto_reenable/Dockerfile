FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
COPY auto_reenable/requirements.txt /var/task/
RUN pip install -r /var/task/requirements.txt

# Copy shared utils
COPY shared_layer/utils /var/task/utils

# Copy function code
COPY auto_reenable/ /var/task/

# Set the command to run the Lambda function
CMD ["lambda_function.lambda_handler"]
