import starlette.responses


class AtomResponse(starlette.responses.Response):
    media_type = "application/atom+xml;charset=utf-8"
