FROM public.ecr.aws/lambda/python:3.11

# Copy dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy function code (IMPORTANT)
COPY lambda_function.py .

# Set Lambda handler
CMD ["lambda_function.lambda_handler"]