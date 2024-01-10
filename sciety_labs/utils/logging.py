from collections import defaultdict
from contextlib import AbstractContextManager
import logging
import logging.handlers
import queue
from typing import Optional, Sequence


LOGGER = logging.getLogger(__name__)


def get_all_loggers_with_handlers() -> Sequence[logging.Logger]:
    root_logger = logging.root
    logging_manager: logging.Manager = root_logger.manager
    return (
        [root_logger]
        + [
            logging.getLogger(logger_name)
            for logger_name in logging_manager.loggerDict  # pylint: disable=no-member
            if logging.getLogger(logger_name).handlers
        ]
    )


class ThreadedLogging(AbstractContextManager):
    def __init__(
        self,
        loggers: Optional[Sequence[logging.Logger]] = None
    ):
        if loggers is None:
            loggers = get_all_loggers_with_handlers()
        LOGGER.info('Loggers: %r', loggers)
        self.loggers = loggers
        self.queue_listener: Optional[logging.handlers.QueueListener] = None
        self.original_handlers_list = [logger.handlers for logger in loggers]
        self.handler_by_handler_id = dict[int, logging.Handler]()
        self.logging_queue_by_handler_id = defaultdict[int, queue.Queue[logging.LogRecord]](
            queue.Queue
        )
        self.queue_handler_by_handler_id = dict[int, logging.handlers.QueueHandler]()
        self.queue_listener_by_handler_id = dict[int, logging.handlers.QueueListener]()

    def _get_queue_handler_for_handler(
        self,
        handler: logging.Handler
    ) -> logging.handlers.QueueHandler:
        queue_handler = self.queue_handler_by_handler_id.get(id(handler))
        if queue_handler is not None:
            return queue_handler
        logging_queue = self.logging_queue_by_handler_id[id(handler)]
        queue_handler = logging.handlers.QueueHandler(logging_queue)
        self.queue_handler_by_handler_id[id(handler)] = queue_handler
        return queue_handler

    def _patch_logger_handlers(self, logger: logging.Logger):
        non_queue_handlers = [
            handler
            for handler in logger.handlers
            if not isinstance(
                handler,
                (logging.handlers.QueueHandler, logging.NullHandler)
            )
        ]
        if not non_queue_handlers:
            return
        LOGGER.info(
            'Using queue handler instead of handlers: %r (%d)',
            non_queue_handlers,
            len(non_queue_handlers)
        )
        for handler in non_queue_handlers:
            self.handler_by_handler_id[id(handler)] = handler
        logger.handlers = [
            self._get_queue_handler_for_handler(handler)
            for handler in non_queue_handlers
        ]

    def _patch_loggers(self):
        for logger in self.loggers:
            self._patch_logger_handlers(logger)

    def _create_queue_listeners(self):
        for handler_id, logging_queue in self.logging_queue_by_handler_id.items():
            assert not self.queue_listener_by_handler_id.get(handler_id)
            handler = self.handler_by_handler_id[handler_id]
            queue_listener = logging.handlers.QueueListener(
                logging_queue,
                handler
            )
            self.queue_listener_by_handler_id[handler_id] = queue_listener

    def _start_queue_listeners(self):
        for queue_listener in self.queue_listener_by_handler_id.values():
            queue_listener.start()

    def _stop_queue_listeners(self):
        for queue_listener in self.queue_listener_by_handler_id.values():
            queue_listener.stop()

    def __enter__(self) -> 'ThreadedLogging':
        self._patch_loggers()
        self._create_queue_listeners()
        self._start_queue_listeners()
        return self

    def __exit__(self, *exc_details):
        for logger, original_handlers in zip(self.loggers, self.original_handlers_list):
            logger.handlers = original_handlers
        LOGGER.info('Restored logging handlers')
        self._stop_queue_listeners()
