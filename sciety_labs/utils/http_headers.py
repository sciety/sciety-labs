from typing import Mapping, Optional


def get_merged_headers(
    app_headers: Mapping[str, str],
    headers: Optional[Mapping[str, str]] = None
) -> Mapping[str, str]:
    if headers:
        return {
            **headers,
            **app_headers
        }
    return app_headers
