FROM public.ecr.aws/lambda/python:3.11

# 安裝依賴項
COPY requirements.txt /var/task/
RUN pip install -r /var/task/requirements.txt

# 複製函數代碼
COPY lambda_function.py /var/task/
COPY .env /var/task/

# 設定運行 Lambda 函數的命令
CMD ["lambda_function.lambda_handler"]
