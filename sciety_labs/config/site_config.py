import os
from typing import NamedTuple, Optional


class SiteConfigEnvironmentVariables:
    COOKIEBOT_IDENTIFIER = 'SCIETY_LABS_COOKIEBOT_IDENTIFIER'


class SiteConfig(NamedTuple):
    cookiebot_identifier: Optional[str] = None


def get_site_config_from_environment_variables() -> SiteConfig:
    return SiteConfig(
        cookiebot_identifier=os.getenv(SiteConfigEnvironmentVariables.COOKIEBOT_IDENTIFIER)
    )
