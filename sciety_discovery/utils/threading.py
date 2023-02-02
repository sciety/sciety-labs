import logging
from threading import Thread
from time import sleep
from typing import Callable


LOGGER = logging.getLogger(__name__)


class UpdateThread(Thread):
    def __init__(
        self,
        update_interval_in_secs: float,
        update_fn: Callable[[], None]
    ):
        super().__init__(daemon=True)
        self.update_interval_in_secs = update_interval_in_secs
        self.update_fn = update_fn

    def run(self):
        LOGGER.info(
            'Update thread running, update_interval_in_secs=%.1f',
            self.update_interval_in_secs
        )
        try:
            while True:
                sleep(self.update_interval_in_secs)
                self.update_fn()
        finally:
            LOGGER.info('Update thread stopped')
