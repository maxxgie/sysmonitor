"""Central logging setup: console plus rotating log file."""

import logging
import logging.handlers
import os
import sys

from PyQt5.QtCore import QStandardPaths

def _app_data_dir() -> str:
    """Return the path to the application data directory."""
    locations = StandardPaths.standardLocations(QStandardPaths.AppDataLocation)
    if locations:
        dir_path = locations[0]
    else:
        dir_path = os.path.join(os.path.expanduser("~"), "systemmonitor")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def setup_logging(app_name: str = "systemmonitor") -> None:
    """Configure root logger once at strat-up.
    
    writes to console and to a rotating file (1mb, 3 backups) in the user's application data directory. Every 
    logger names its source file
    """

    log_dir =_app_data_dir()

    log_file = os.path.join(
        log_dir,
        app_name,
        f"{app_name}.log")
    

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if not root.handlers:

        console = 
    
        logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(fmt)
        root.addHandler(console)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=1_048_576, 
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

logging.getlogger(__name__).info(
     "Logging initialized: %s",
     log_file
)