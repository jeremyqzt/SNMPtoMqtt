FROM python:3

WORKDIR /root/

COPY certs certs/

COPY templates templates/

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./server.py" ]