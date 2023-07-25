import os

import pytz

# Postgres Config
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USERNAME = os.getenv("DB_USERNAME", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_IP = os.getenv("DB_IP", "localhost")
DB_PORT = os.getenv("DB_PORT", 5432)

# Rabbit Config
RABBIT_USER = os.getenv("RABBIT_USER")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD")
RABBIT_HOST_IP = os.getenv("RABBIT_HOST_IP")
RABBIT_PORT = os.getenv("RABBIT_PORT", 5672)
RABBIT_VHOST = os.getenv("RABBIT_VHOST")
RABBIT_CONNECTION_TIMEOUT = os.getenv(
    "RABBIT_CONNECTION_TIMEOUT", 60 * 60 * 6
)  # six hours


def tz_is_valid(tz):
    ALL_TIMEZONES = set(pytz.all_timezones)
    return tz in ALL_TIMEZONES


tz = os.getenv("TIMEZONE", "")
TIMEZONE = tz if tz_is_valid(tz) else "Africa/Nairobi"
