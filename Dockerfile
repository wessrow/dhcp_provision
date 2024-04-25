FROM alpine:3.18.4

# Install python/pip and ssh
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools
RUN apk add --update --no-cache openssh
RUN apk add --update --no-cache openssl

WORKDIR /app

RUN openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 3650 -nodes -subj "/C=XX/ST=Stockholm/L=Stockholm/O=TeliaCygate/OU=Deploy/CN=DHCP_Webhook_Service"

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["gunicorn"]

CMD ["-c", "gunicorn.conf.py", "app:app"]