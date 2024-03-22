from locust import HttpUser, task


class ScietyLabsListUser(HttpUser):
    @task
    def user_list(self):
        self.client.get('/lists/by-id/454ba80f-e0bc-47ed-ba76-c8f872c303d2')

    @task
    def group_list(self):
        self.client.get('/lists/by-id/f1561c0f-d247-4e03-934d-52ad9e0aed2f')
