import json
import logging

import fastapi

from sciety_labs.app.routers.api.utils.jsonapi import get_default_jsonapi_error_json_response


LOGGER = logging.getLogger(__name__)


class TestGetDefaultJsonApiErrorJsonResponse:
    def test_should_support_generic_exception(self):
        exception = AssertionError('test')
        json_response = get_default_jsonapi_error_json_response(
            exception
        )
        assert json_response.status_code == 500
        assert json.loads(json_response.body) == {
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
        json_response = get_default_jsonapi_error_json_response(
            exception
        )
        assert json_response.status_code == 123
        assert json.loads(json_response.body) == {
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
        json_response = get_default_jsonapi_error_json_response(
            exception
        )
        LOGGER.debug('json_response: %r', json_response)
        assert json_response.status_code == 400
        assert json.loads(json_response.body) == {
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
