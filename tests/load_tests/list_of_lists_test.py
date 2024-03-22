from locust import HttpUser, task


class ScietyLabsListOfListsUser(HttpUser):
    @task
    def user_lists(self):
        self.client.get('/lists/user-lists')

    @task
    def group_lists(self):
        self.client.get('/lists/group-lists')
