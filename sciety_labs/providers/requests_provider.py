from typing import Optional

import requests


class RequestsProvider:
    def __init__(
        self,
        requests_session: Optional[requests.Session] = None
    ) -> None:
        self.headers: dict = {}
        if requests_session is None:
            requests_session = requests.Session()
        self.requests_session = requests_session
        self.timeout: float = 5 * 60
