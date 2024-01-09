from contextlib import AbstractContextManager
import logging
import logging.handlers
import queue
from typing import List, Optional, Sequence


LOGGER = logging.getLogger(__name__)


def get_all_loggers() -> Sequence[logging.Logger]:
    root_logger = logging.root
    logging_manager: logging.Manager = root_logger.manager
    return (
        [root_logger]
        + [
            logging.getLogger(logger_name)
            for logger_name in logging_manager.loggerDict  # pylint: disable=no-member
        ]
    )


class threaded_logging(AbstractContextManager):  # pylint: disable=invalid-name
    def __init__(
        self,
        loggers: Optional[Sequence[logging.Logger]] = None
    ):
        if loggers is None:
            loggers = get_all_loggers()
        LOGGER.info('Loggers: %r', loggers)
        self.loggers = loggers
        self.queue_listener: Optional[logging.handlers.QueueListener] = None
        self.original_handlers_list = [logger.handlers for logger in loggers]
        self.logging_queue = queue.Queue[logging.LogRecord](-1)
        self.queue_handler = logging.handlers.QueueHandler(self.logging_queue)

    def __enter__(self) -> 'threaded_logging':
        assert self.queue_listener is None
        all_handlers: List[logging.Handler] = []
        for logger in self.loggers:
            non_queue_handlers = [
                handler
                for handler in logger.handlers
                if not isinstance(
                    handler,
                    (logging.handlers.QueueHandler, logging.NullHandler)
                )
            ]
            if not non_queue_handlers:
                continue
            LOGGER.info(
                'Using queue handler instead of handlers: %r (%d)',
                non_queue_handlers,
                len(non_queue_handlers)
            )
            logger.handlers = [self.queue_handler]
            all_handlers.extend(non_queue_handlers)
        if all_handlers:
            self.queue_listener = logging.handlers.QueueListener(
                self.logging_queue,
                *all_handlers
            )
            self.queue_listener.start()
        return self

    def __exit__(self, *exc_details):
        for logger, original_handlers in zip(self.loggers, self.original_handlers_list):
            logger.handlers = original_handlers
        LOGGER.info('Restored logging handlers')
        if self.queue_listener is not None:
            self.queue_listener.stop()
