from math import isnan
from ruuvitag import RuuviDaemon
from influxdb import InfluxDBClient
from paho.mqtt.publish import multiple
import json
import os
import pendulum
import sys

DB_NAME = "homeautomation"
device_id = os.getenv("DEVICE_ID")
INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_USER = os.getenv("INFLUX_USER")
INFLUX_PASS = os.getenv("INFLUX_PASS")


class RuuviLogger(RuuviDaemon):
    def __init__(self, *args, **kwargs):
        super(RuuviLogger, self).__init__(*args, **kwargs)
        self.influx = InfluxDBClient(
            host=INFLUX_HOST,
            port=443,
            username=INFLUX_USER,
            password=INFLUX_PASS,
            database=DB_NAME,
            ssl=True,
            verify_ssl=True,
        )

        # check that we have the correct database
        print(self.influx.get_list_database())
        if DB_NAME not in [x["name"] for x in self.influx.get_list_database()]:
            self.initial_setup()

    def initial_setup(self):
        # Create database in influx
        self.influx.create_database(DB_NAME)

    # Send tag to MQTT server(s)
    def tag_to_mqtt(self, tag):
        data = tag.as_dict()
        data.pop("last_seen")  # This won't work

        msgs = []
        # generate messages
        msgs.append(
            {
                "topic": "sensor/ruuvitag/" + data["address"] + "/value",
                "payload": json.dumps(data),
            }
        )
        # Local MQTT
        multiple(msgs, hostname="mqtt-server", client_id=device_id)
        # Scaleway IoT
        multiple(msgs, hostname="iot.fr-par.scw.cloud", client_id=device_id)

    # send tag to InfluxDB
    def tag_to_influx(self, tag, is_new=False):
        tag_as_dict = tag.as_dict()
        tag_as_dict.pop("last_seen")

        measurement_tags = {
            "address": tag_as_dict.pop("address"),
            "protocol": str(tag_as_dict.pop("protocol")),
            "movement_detected": "true" if tag.movement_detected.is_set() else "false",
        }
        tag.movement_detected.clear()

        self.influx.write_points(
            [
                {
                    "measurement": "device",
                    "time": pendulum.now().isoformat(),
                    "fields": {
                        key: value
                        for key, value in tag_as_dict.items()
                        # Filter out NaN -values, as InfluxDB doesn't like them
                        if not isnan(value)
                    },
                }
            ],
            tags=measurement_tags,
        )

    def callback(self, tag, is_new=False):
        self.tag_to_mqtt(tag)
        self.tag_to_influx(tag, is_new)


if __name__ == "__main__":
    import time

    print("Connecting to %s with user %s" % (INFLUX_HOST, INFLUX_USER))

    if INFLUX_HOST is None:
        print("Influx host not defined, quitting")
        sys.exit(1)

    ruuvilogger = RuuviLogger()
    ruuvilogger.start()

    while ruuvilogger.is_alive():
        time.sleep(1)

    ruuvilogger.stop()

