import os
from typing import NamedTuple, Optional


class SiteConfigEnvironmentVariables:
    COOKIEBOT_IDENTIFIER = 'SCIETY_LABS_COOKIEBOT_IDENTIFIER'
    GOOGLE_TAG_MANAGER_ID = 'SCIETY_LABS_GOOGLE_TAG_MANAGER_ID'


class SiteConfig(NamedTuple):
    cookiebot_identifier: Optional[str] = None
    google_tag_manager_id: Optional[str] = None


def get_site_config_from_environment_variables() -> SiteConfig:
    return SiteConfig(
        cookiebot_identifier=os.getenv(SiteConfigEnvironmentVariables.COOKIEBOT_IDENTIFIER),
        google_tag_manager_id=os.getenv(SiteConfigEnvironmentVariables.GOOGLE_TAG_MANAGER_ID)
    )
