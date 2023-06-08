from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.utils.threading import UpdateThread


class AppUpdateManager:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.app_providers_and_models = app_providers_and_models

    def check_or_reload_data(self):
        # Note: this may still use a cache
        _sciety_event_dict_list = (
            self.app_providers_and_models.sciety_event_provider.get_sciety_event_dict_list()
        )
        self.app_providers_and_models.lists_model.apply_events(_sciety_event_dict_list)
        self.app_providers_and_models.evaluation_stats_model.apply_events(_sciety_event_dict_list)
        self.app_providers_and_models.google_sheet_article_image_provider.refresh()
        self.app_providers_and_models.google_sheet_list_image_provider.refresh()

    def start(self, update_interval_in_secs: float):
        UpdateThread(
            update_interval_in_secs=update_interval_in_secs,
            update_fn=self.check_or_reload_data
        ).start()