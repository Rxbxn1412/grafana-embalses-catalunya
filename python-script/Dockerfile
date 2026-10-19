FROM python:3.11-slim

RUN pip install paho-mqtt requests

COPY sensor.py /app/sensor.py
WORKDIR /app

CMD ["python", "-u", "sensor.py"]