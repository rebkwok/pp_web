from model_mommy import mommy

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test import RequestFactory
from django.utils.html import strip_tags

from accounts.models import OnlineDisclaimer


def set_up_fb():
    fbapp = mommy.make_recipe('entries.fb_app')
    site = Site.objects.get_current()
    fbapp.sites.add(site.id)


class TestSetupMixin(object):

    @classmethod
    def setUpTestData(cls):
        set_up_fb()
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            username='test', email='test@test.com', password='test'
        )
        mommy.make(OnlineDisclaimer, user=cls.user)

        cls.user_no_disclaimer = User.objects.create_user(
            username='test_no_disc', email='test@test.com', password='test'
        )
        cls.url = None  # test class needs to define this


class TestSetupLoginRequiredMixin(TestSetupMixin):

    def test_login_required(self):
        resp = self.client.get(self.url)
        redirected_url = reverse('account_login') + "?next={}".format(self.url)

        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)


def format_content(content):
    # strip tags, \n, \t and extra whitespace from content
    return ' '.join(
        strip_tags(content).replace('\n', '').replace('\t', '').split()
    )

