FROM python:3-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get -y install build-essential build-essential libssl-dev libffi-dev python-dev libglib2.0-dev git && rm -rf /var/lib/apt/lists/*
# Make this its own layer, it's a slog to install and doesn't really need changes
RUN pip install --no-cache-dir git+https://github.com/kipe/ruuvitag.git
RUN pip install --no-cache-dir paho-mqtt influxdb pendulum

COPY . .

CMD [ "python", "./ruuvilogger.py" ]
