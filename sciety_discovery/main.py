import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


LOGGER = logging.getLogger(__name__)


STATIC_USER_LISTS = [{
    'list_id': 'b8575203-b305-4ede-8b6f-5850a22b1d3b',
    'list_title': '@BiophysicsColab',
    'list_description': 'Articles that have been saved by @BiophysicsColab',
    'avatar_url': 'https://pbs.twimg.com/profile_images/1417582635040317442/jYHfOlh6_normal.jpg',
    'article_count': 82,
    'last_updated_date_isoformat': '2022-11-30',
    'last_updated_date_display_format': 'Nov 30, 2022'
}, {
    'list_id': 'e60ede07-a07e-41c4-9e29-9257c0c8bbf3',
    'list_title': '@AvasthiReading',
    'list_description': 'Articles that have been saved by @AvasthiReading',
    'avatar_url': 'https://pbs.twimg.com/profile_images/1417079202973638657/VrQKBTkw_normal.jpg',
    'article_count': 137,
    'last_updated_date_isoformat': '2022-10-19',
    'last_updated_date_display_format': 'Oct 19, 2022'
}, {
    'list_id': '3e0572d3-be24-4728-852a-8337feba0966',
    'list_title': '@maria_eichel',
    'list_description': 'Articles that have been saved by @maria_eichel',
    'avatar_url': 'https://pbs.twimg.com/profile_images/1584205611247583234/aN5oC7iZ_normal.jpg',
    'article_count': 18,
    'last_updated_date_isoformat': '2022-10-19',
    'last_updated_date_display_format': 'Oct 19, 2022'
}]


def create_app():
    templates = Jinja2Templates(directory="templates")

    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static", html=False), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            "index.html", {
                "request": request,
                "user_lists": STATIC_USER_LISTS
            }
        )

    return app
