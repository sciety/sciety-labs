from locust import HttpUser, task

class ScietyLabsHomepageUser(HttpUser):
    @task
    def homepage(self):
        self.client.get('/')
