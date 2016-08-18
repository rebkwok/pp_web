from django.conf.urls import url
from accounts.views import ProfileUpdateView, profile, CustomLoginView, \
    DisclaimerCreateView, data_protection, subscribe_view

urlpatterns = [
    url(r'^profile/$', profile, name='profile'),
    url(
        r'^profile/update/$', ProfileUpdateView.as_view(),
        name='update_profile'
    ),
    url(
        r'^disclaimer/$', DisclaimerCreateView.as_view(),
        name='disclaimer_form'
    ),
    url(
        r'^data-protection-statement/$', data_protection,
        name='data_protection'
    ),
    url(r'^mailing-list/$', subscribe_view, name='subscribe'),

    url(r'^$', profile)
]


