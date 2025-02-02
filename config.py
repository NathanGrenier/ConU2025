import logging
import os
import time

import influxdb_client
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "./data"
STATIONS_FILE_PATH = f"{DATA_PATH}/stations.csv"
AIR_QUALITY_FILE_PATH = f"{DATA_PATH}/air/air_quality_2022-2024.csv"
VIOLATIONS_FILE_PATH = f"{DATA_PATH}/violations.csv"
STATIONS_FILE_PATH = f"{DATA_PATH}/stations.csv"

DUMP_PATH = f"{DATA_PATH}/dump"
CLEANED_AIR_QUALITY_FILE_PATH = f"{DUMP_PATH}/cleaned_air_quality.csv"
CLEANED_VIOLATIONS_FILE_PATH = f"{DUMP_PATH}/cleaned_violations.csv"
CLEANED_STATIONS_FILE_PATH = f"{DUMP_PATH}/cleaned_stations.csv"


INFLUXDB_BUCKET = "my-bucket"
# INFLUXDB_BUCKET_AIR_QUALITY = "air-quality"
# INFLUXDB_BUCKET_VIOLATIONS = "violations"
# INFLUXDB_BUCKET_STATIONS = "stations"


url = os.getenv("INFLUX_DB_URL")
token = os.getenv("INFLUX_DB_TOKEN")
org = os.getenv("INFLUX_DB_ORG")
influxdbClient = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "db",
    "user": "postgres",
    "password": "postgres",
}


def timingDecorator(func):
    def wrapper(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        endTime = time.time()
        logger.debug(f"{func.__name__}() took {endTime - startTime:.2f} seconds")
        return result

    return wrapper


LOG_COLORS = {
    "DEBUG": "\033[94m",  # Blue
    "INFO": "\033[92m",  # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",  # Red
    "CRITICAL": "\033[95m",  # Magenta
    "RESET": "\033[0m",  # Reset color
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_color = LOG_COLORS.get(record.levelname, LOG_COLORS["RESET"])
        record.levelname = f"{log_color}{record.levelname}{LOG_COLORS['RESET']}"
        return super().format(record)


def configureLogger(name, LEVEL=logging.WARNING):
    """
    Configure logger settings.

    Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure the logger
    logger = logging.getLogger(name)
    logger.setLevel(LEVEL)

    # Create console handler and set level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LEVEL)

    formatter = ColoredFormatter(
        "[%(levelname)s] %(asctime)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    # Add handler to the logger
    logger.addHandler(console_handler)

    return logger


logger = logging.getLogger("logger")
if not logger.handlers:
    logger = configureLogger("logger", LEVEL=logging.DEBUG)
