FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY train_model.py /app
RUN python train_model.py
COPY app.py /app
CMD ["python", "app.py"]