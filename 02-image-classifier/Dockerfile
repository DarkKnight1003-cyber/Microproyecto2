FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt /app
RUN pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu
RUN pip install -r ./requirements.txt
COPY app.py /app
CMD ["python", "app.py"]