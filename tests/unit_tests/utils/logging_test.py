import logging
import logging.handlers
import sys
from typing import Iterator
from unittest.mock import patch

import pytest

from sciety_labs.utils.logging import get_all_loggers_with_handlers, threaded_logging


@pytest.fixture(name='logger_dict_mock')
def _logger_dict_mock() -> Iterator[dict]:
    with patch.object(logging.root.manager, 'loggerDict', {}) as mock:  # type: ignore
        yield mock


class TestGetAllLoggers:
    def test_should_return_root_logger_and_other_configured_logger_with_handlers(
        self,
        logger_dict_mock: dict
    ):
        assert logging.root.handlers
        logger_with_handlers = logging.Logger('test.with-handlers')
        logger_with_handlers.handlers = logging.root.handlers
        logger_dict_mock[logger_with_handlers.name] = logger_with_handlers
        logger_without_handlers = logging.Logger('test.without-handlers')
        logger_dict_mock[logger_without_handlers.name] = logger_without_handlers
        all_loggers = get_all_loggers_with_handlers()
        assert all_loggers == [logging.root, logger_with_handlers]


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
