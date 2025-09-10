import logging
import os

from config.costanti_globali import OUTPUT_DIR


def setup_logger(nome_file="arricchimento.log"):
    log_file = os.path.join(OUTPUT_DIR, nome_file)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
