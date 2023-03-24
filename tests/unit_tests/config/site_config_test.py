import pytest

from sciety_labs.config.site_config import (
    SiteConfigEnvironmentVariables,
    get_site_config_from_environment_variables
)


@pytest.mark.usefixtures('env_mock')
class TestGetSiteConfigFromEnvironmentVariables:
    def test_should_return_none_values_if_not_configured(self):
        site_config = get_site_config_from_environment_variables()
        assert site_config.cookiebot_identifier is None
        assert site_config.google_tag_manager_id is None

    def test_should_return_read_cookiebot_identifier_from_env_var(self, env_mock: dict):
        env_mock[SiteConfigEnvironmentVariables.COOKIEBOT_IDENTIFIER] = 'cookiebot_1'
        site_config = get_site_config_from_environment_variables()
        assert site_config.cookiebot_identifier == 'cookiebot_1'

    def test_should_return_read_google_tag_manager_id_from_env_var(self, env_mock: dict):
        env_mock[SiteConfigEnvironmentVariables.GOOGLE_TAG_MANAGER_ID] = 'gtm_1'
        site_config = get_site_config_from_environment_variables()
        assert site_config.google_tag_manager_id == 'gtm_1'
