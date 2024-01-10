from contextlib import AbstractContextManager
import dataclasses
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


@dataclasses.dataclass(frozen=True)
class _WrappedHandler:
    handler: logging.Handler
    logging_queue: queue.Queue[logging.LogRecord]
    queue_handler: logging.handlers.QueueHandler
    queue_listener: logging.handlers.QueueListener

    @staticmethod
    def for_handler(handler: logging.Handler) -> '_WrappedHandler':
        logging_queue = queue.Queue[logging.LogRecord]()
        queue_handler = logging.handlers.QueueHandler(logging_queue)
        queue_listener = logging.handlers.QueueListener(logging_queue, handler)
        return _WrappedHandler(
            handler=handler,
            logging_queue=logging_queue,
            queue_handler=queue_handler,
            queue_listener=queue_listener
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
        self.wrapped_handler_by_handler_id = dict[int, _WrappedHandler]()

    def _get_wrapped_handler(
        self,
        handler: logging.Handler
    ) -> _WrappedHandler:
        handler_id = id(handler)
        wrapped_handler = self.wrapped_handler_by_handler_id.get(handler_id)
        if wrapped_handler is not None:
            return wrapped_handler
        wrapped_handler = _WrappedHandler.for_handler(handler)
        self.wrapped_handler_by_handler_id[handler_id] = wrapped_handler
        return wrapped_handler

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
        logger.handlers = [
            self._get_wrapped_handler(handler).queue_handler
            for handler in non_queue_handlers
        ]

    def _patch_loggers(self):
        for logger in self.loggers:
            self._patch_logger_handlers(logger)

    def _start_queue_listeners(self):
        for wrapped_handler in self.wrapped_handler_by_handler_id.values():
            wrapped_handler.queue_listener.start()

    def _stop_queue_listeners(self):
        for wrapped_handler in self.wrapped_handler_by_handler_id.values():
            wrapped_handler.queue_listener.stop()

    def __enter__(self) -> 'ThreadedLogging':
        self._patch_loggers()
        self._start_queue_listeners()
        return self

    def __exit__(self, *exc_details):
        for logger, original_handlers in zip(self.loggers, self.original_handlers_list):
            logger.handlers = original_handlers
        LOGGER.info('Restored logging handlers')
        self._stop_queue_listeners()
