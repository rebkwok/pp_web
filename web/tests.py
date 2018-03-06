from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('web:home')

    def test_no_login_required(self):
        self.client.get(self.url)
