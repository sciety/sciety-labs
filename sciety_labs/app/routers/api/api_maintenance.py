import logging

from fastapi import APIRouter

from sciety_labs.app.app_update_manager import AppUpdateManager


LOGGER = logging.getLogger(__name__)


def create_api_maintenance_router(
    app_update_manager: AppUpdateManager
):
    router = APIRouter()

    @router.post('/check-or-reload-data', include_in_schema=False)
    def check_or_reload_data():
        app_update_manager.check_or_reload_data()
        return {'status': 'OK'}

    return router
