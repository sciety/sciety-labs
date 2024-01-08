import logging
import logging.handlers
import sys

from sciety_labs.utils.logging import threaded_logging


class TestThreadedLogging:
    def test_should_not_fail_with_logger_without_console_handler(self):
        logger = logging.Logger('test')
        logger.handlers = []
        with threaded_logging(loggers=[logger]):
            logger.info('test')
        assert not logger.handlers

    def test_should_use_queue_logger_with_console_handler(self):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            r'prefix:%(message)s'
        ))
        original_handlers = [console_handler]
        logger = logging.Logger('test')
        logger.handlers = original_handlers
        with threaded_logging(loggers=[logger]):
            assert isinstance(logger.handlers[0], logging.handlers.QueueHandler)
            logger.info('test')
        assert logger.handlers == original_handlers
