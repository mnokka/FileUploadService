FROM python:3.11

WORKDIR /app

COPY app.py .
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir -p uploads data
COPY templates /app/templates
#RUN apt-get update && apt-get install -y gzip

EXPOSE 5000

CMD ["python", "app.py"]