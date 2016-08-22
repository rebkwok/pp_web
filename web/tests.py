from model_mommy import mommy

from django.test import TestCase
from django.contrib.sites.models import Site
from django.core import management
from django.core.urlresolvers import reverse

from allauth.socialaccount.models import SocialApp


def set_up_fb():
    fbapp = mommy.make_recipe('entries.fb_app')
    site = Site.objects.get_current()
    fbapp.sites.add(site.id)


class HomeViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('web:home')
        set_up_fb()


    def test_no_login_required(self):
        self.client.get(self.url)


class ManagementCommandsTests(TestCase):

    def test_setup_fb(self):
        self.assertEquals(SocialApp.objects.all().count(), 0)
        management.call_command('setup_fb')
        self.assertEquals(SocialApp.objects.all().count(), 1)
