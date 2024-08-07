

from typing import Set

import pytest

from requests import Session

from sciety_labs.app.routers.api.papers.typing import (
    PaperSearchResponseDict,
    ClassificationResponseDict
)


BIOPHYISICS_DOI_1 = '10.1101/2022.02.23.481615'


class Categories:
    BIOPHYSICS = 'Biophysics'


NON_BIORXIV_MEDRXIV_GROUP_TITLE_1 = 'PsyArXiv'
NON_BIORXIV_MEDRXIV_DOI_WITH_GROUP_TITLE_1 = '10.31234/osf.io/2hv6x'


@pytest.fixture(name='classification_list_response_dict', scope='session')
def _classification_list_response_dict(
    regression_test_session: Session
) -> ClassificationResponseDict:
    response = regression_test_session.get(
        '/api/papers/v1/preprints/classifications'
    )
    response.raise_for_status()
    response_json: ClassificationResponseDict = response.json()
    return response_json


def get_category_set(
    classification_list_response_dict: ClassificationResponseDict
) -> Set[str]:
    return {
        classification['attributes']['display_name']
        for classification in classification_list_response_dict['data']
        if classification['type'] == 'category'
    }


class TestApiClassifcationList:
    def test_should_return_non_empty_list(
        self,
        classification_list_response_dict: ClassificationResponseDict
    ):
        assert len(classification_list_response_dict['data']) > 0

    def test_should_contain_biophysics(
        self,
        classification_list_response_dict: ClassificationResponseDict
    ):
        category_set = get_category_set(classification_list_response_dict)
        assert Categories.BIOPHYSICS in category_set

    def test_should_not_contain_non_biorxiv_medrxiv_group_title(
        self,
        classification_list_response_dict: ClassificationResponseDict
    ):
        category_set = get_category_set(classification_list_response_dict)
        assert NON_BIORXIV_MEDRXIV_GROUP_TITLE_1 not in category_set


class TestApiPreprints:
    def test_should_list_preprints_for_valid_category(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/api/papers/v1/preprints',
            params={'filter[category]': Categories.BIOPHYSICS}
        )
        response.raise_for_status()
        response_json: PaperSearchResponseDict = response.json()
        assert len(response_json['data']) > 0

    def test_should_return_empty_list_for_non_biorxiv_medrxiv_group_title(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            '/api/papers/v1/preprints',
            params={'filter[category]': NON_BIORXIV_MEDRXIV_GROUP_TITLE_1}
        )
        response.raise_for_status()
        response_json: PaperSearchResponseDict = response.json()
        assert len(response_json['data']) == 0


class TestApiClassificationsByDoi:
    def test_should_list_classifications_by_doi(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/api/papers/v1/preprints/classifications/by/doi/{BIOPHYISICS_DOI_1}'
        )
        response.raise_for_status()
        response_json: ClassificationResponseDict = response.json()
        assert len(response_json['data']) > 0
        assert response_json['data'] == [
            {
                'type': 'category',
                'id': Categories.BIOPHYSICS,
                'attributes': {
                    'display_name': Categories.BIOPHYSICS,
                    'source_id': 'crossref_group_title'
                }
            }
        ]

    def test_should_return_empty_list_for_non_biorxiv_medrxiv_doi_with_group_title(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            (
                '/api/papers/v1/preprints/classifications/by/doi/'
                + NON_BIORXIV_MEDRXIV_DOI_WITH_GROUP_TITLE_1
            )
        )
        response.raise_for_status()
        response_json: ClassificationResponseDict = response.json()
        assert len(response_json['data']) == 0
