FROM python:3.11.4-slim

COPY app /app
WORKDIR /app


RUN pip3 install --no-cache-dir -r requirements.txt

CMD [ "python", "./main.py" ]