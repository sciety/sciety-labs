import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.utils.threading import UpdateThread


LOGGER = logging.getLogger(__name__)


def run_and_wait_for_async_function(async_function):
    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(1) as pool:
            return pool.submit(
                lambda: asyncio.run_coroutine_threadsafe(async_function(), loop=loop)
            ).result()
    except RuntimeError:
        return asyncio.run(async_function())


class AppUpdateManager:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.app_providers_and_models = app_providers_and_models

    def check_or_reload_data(
        self,
        preload_only: bool = False,
        delete_expired: bool = True
    ):
        LOGGER.info('Updating: preload_only=%r, delete_expired=%r', preload_only, delete_expired)
        if not preload_only:
            self.app_providers_and_models.sciety_event_provider.refresh()
        # Note: this may still use a cache
        _sciety_event_dict_list = (
            self.app_providers_and_models.sciety_event_provider.get_sciety_event_dict_list()
        )
        self.app_providers_and_models.lists_model.apply_events(_sciety_event_dict_list)
        self.app_providers_and_models.evaluation_stats_model.apply_events(_sciety_event_dict_list)
        if preload_only:
            self.app_providers_and_models.google_sheet_article_image_provider.preload()
            self.app_providers_and_models.google_sheet_list_image_provider.preload()
        else:
            self.app_providers_and_models.google_sheet_article_image_provider.refresh()
            self.app_providers_and_models.google_sheet_list_image_provider.refresh()
        if delete_expired:
            LOGGER.info('Deleting expired requests-cache responses')
            self.app_providers_and_models.cached_requests_session.cache.delete(expired=True)
            LOGGER.info('Deleting expired aiohttp-client-cache responses')
            run_and_wait_for_async_function(
                self.app_providers_and_models
                .async_cached_client_session
                .cache
                .delete_expired_responses
            )
        LOGGER.info('Update done')

    def check_or_reload_data_no_fail(self):
        try:
            self.check_or_reload_data()
        except InterruptedError:
            LOGGER.info('Updates interrupted, app closed?')
            raise
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error('Caught error handling update: %s', exc, exc_info=1)

    def start(self, update_interval_in_secs: float):
        UpdateThread(
            update_interval_in_secs=update_interval_in_secs,
            update_fn=self.check_or_reload_data_no_fail
        ).start()
