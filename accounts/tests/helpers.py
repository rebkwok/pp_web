from importlib import import_module
from model_mommy import mommy

from django.contrib.auth.models import User
from django.conf import settings
from django.test import RequestFactory
from django.utils.html import strip_tags

from accounts.models import DataPrivacyPolicy, OnlineDisclaimer, SignedDataPrivacy
from accounts.utils import has_active_data_privacy_agreement


def make_data_privacy_agreement(user):
    if not has_active_data_privacy_agreement(user):
        if DataPrivacyPolicy.current_version() == 0:
            mommy.make(
                DataPrivacyPolicy, content='Foo', version=1
            )
        mommy.make(
            SignedDataPrivacy, user=user,
            version=DataPrivacyPolicy.current_version()
        )


def _create_session():
    # create session
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    engine = import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore()
    store.save()
    return store


def setup_view(view, request, *args, **kwargs):
    """
    Mimic as_view() returned callable, but returns view instance.
    args and kwargs are the same you would pass to ``reverse()``
    """
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view


class TestSetupMixin(object):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            username='test', email='test@test.com', password='test'
        )
        mommy.make(OnlineDisclaimer, user=cls.user)
        make_data_privacy_agreement(cls.user)


def format_content(content):
    # strip tags, \n, \t and extra whitespace from content
    return ' '.join(
        strip_tags(content).replace('\n', '').replace('\t', '').split()
    )

