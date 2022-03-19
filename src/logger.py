import logging
import os
import sys


def initialize_logger(logger_name, save_path, file_name):
    # Set up logger
    logger = logging.getLogger(name=logger_name)
    logger.setLevel(logging.DEBUG)

    if len(file_name.split(".")) == 1:
        raise Exception("File name has no extension! Provide one (e.g. process.log)")

    fh = logging.FileHandler(filename=os.path.join(save_path, file_name), mode="w")
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.INFO)
    log_format = logging.Formatter("%(levelname)s - %(message)s")

    fh.setFormatter(log_format)
    ch.setFormatter(log_format)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
