import re
import requests


class ResponseWrapper:
    def __init__(self, response: requests.Response) -> None:
        self.response = response

    def get_article_card_count(self) -> int:
        return len(re.findall(r'<article[^>]*>', self.response.text))
