import logging

from api_helpers.config import config

logging.basicConfig(
    format="%(asctime)s | %(levelname)-2s - %(message)s",
    level=config.log_level,
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)

logger = logging.getLogger(__name__)


def print_information(msg):
    logger.info(msg)


def print_warning(msg):
    logger.warning(msg)


def print_error(msg):
    logger.error(msg)


def print_debug(msg):
    logger.debug(msg)


def print_critical(msg):
    logger.critical(msg)


# Aliases
I = print_information
W = print_warning
E = print_error
D = print_debug
C = print_critical

I("Logging configuration initialized with level: {}".format(config.log_level))
D("Logging configuration initialized with level: {}".format(config.log_level))
