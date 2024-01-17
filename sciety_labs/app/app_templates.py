from fastapi.templating import Jinja2Templates

import markupsafe

import bleach
from sciety_labs.config.site_config import SiteConfig


from sciety_labs.utils.datetime import (
    get_date_as_display_format,
    get_date_as_isoformat,
    get_timestamp_as_isoformat
)
from sciety_labs.utils.fastapi import (
    get_likely_client_ip_for_request
)


ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'bold',
    'code',
    'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
    'h1', 'h2', 'h3', 'p', 'img', 'video', 'div',
    'p', 'br', 'span', 'hr', 'src', 'class',
    'section', 'sub', 'sup'
]


def get_sanitized_string_as_safe_markup(text: str) -> markupsafe.Markup:
    return markupsafe.Markup(bleach.clean(text, tags=ALLOWED_TAGS))


def get_app_templates(site_config: SiteConfig) -> Jinja2Templates:
    templates = Jinja2Templates(directory='templates')
    templates.env.filters['sanitize'] = get_sanitized_string_as_safe_markup
    templates.env.filters['date_isoformat'] = get_date_as_isoformat
    templates.env.filters['date_display_format'] = get_date_as_display_format
    templates.env.filters['timestamp_isoformat'] = get_timestamp_as_isoformat
    templates.env.filters['likely_client_ip_for_request'] = get_likely_client_ip_for_request
    templates.env.globals['site_config'] = site_config
    return templates
