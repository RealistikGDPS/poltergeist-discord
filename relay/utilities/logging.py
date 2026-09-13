import logging.config
from logging import Logger

import yaml


def configure_from_yaml(*, path: str | None = None) -> None:
    if path is None:
        path = "logging.yaml"

    with open(path) as file:
        config = yaml.safe_load(file)

    logging.config.dictConfig(config)


def get_logger(name: str) -> Logger:
    return logging.getLogger(name)
