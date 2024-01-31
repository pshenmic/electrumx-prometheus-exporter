FROM python:3.10-alpine AS builder

WORKDIR /app

COPY requirements.txt /app
RUN pip3 install -r requirements.txt

COPY electrumx-prometheus-exporter.py /app

ENTRYPOINT ["python3"]
CMD ["electrumx-prometheus-exporter.py"]
