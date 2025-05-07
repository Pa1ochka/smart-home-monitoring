FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["sh", "-c", "python data_processor/data_processor.py & python notification_service/notification_service.py & python web_interface/web_interface.py"]