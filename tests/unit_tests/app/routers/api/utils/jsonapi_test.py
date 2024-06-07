import logging

import fastapi

from sciety_labs.app.routers.api.utils.jsonapi import get_default_jsonapi_error_json_response_dict


LOGGER = logging.getLogger(__name__)


class TestGetDefaultJsonApiErrorJsonResponseDict:
    def test_should_support_generic_exception(self):
        exception = AssertionError('test')
        assert get_default_jsonapi_error_json_response_dict(
            exception
        ) == {
            'errors': [{
                'title': 'AssertionError',
                'detail': 'test',
                'status': '500'
            }]
        }

    def test_should_use_details_from_fastapi_http_exception(self):
        exception = fastapi.exceptions.HTTPException(
            status_code=123,
            detail='Error details 1'
        )
        assert get_default_jsonapi_error_json_response_dict(
            exception
        ) == {
            'errors': [{
                'title': 'HTTPException',
                'detail': 'Error details 1',
                'status': '123'
            }]
        }

    def test_should_use_details_from_fastapi_request_validation_exception(self):
        exception = fastapi.exceptions.RequestValidationError(
            errors=[{'key': 'Error 1'}]
        )
        json_response_dict = get_default_jsonapi_error_json_response_dict(
            exception
        )
        LOGGER.debug('json_response_dict: %r', json_response_dict)
        assert json_response_dict == {
            'errors': [{
                'title': 'RequestValidationError',
                'detail': (
                    'Encountered validation errors. Please check the request.'
                ),
                'status': '400',
                'meta': {
                    'errors': [{'key': 'Error 1'}]
                }
            }]
        }
