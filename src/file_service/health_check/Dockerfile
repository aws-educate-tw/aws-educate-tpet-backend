FROM public.ecr.aws/lambda/python:3.11

# Copy function code
COPY . /var/task/

# Set the command to run the Lambda function
CMD ["lambda_function.lambda_handler"]
