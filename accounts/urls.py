from django.urls import path
from accounts.views import ProfileUpdateView, profile, \
    DisclaimerCreateView, data_protection, subscribe_view


app_name = 'accounts'


urlpatterns = [
    path('profile/', profile, name='profile'),
    path(
        'profile/update/', ProfileUpdateView.as_view(),
        name='update_profile'
    ),
    path(
        'waiver/', DisclaimerCreateView.as_view(),
        name='disclaimer_form'
    ),
    path(
        'data-protection-statement/', data_protection,
        name='data_protection'
    ),
    path('mailing-list/', subscribe_view, name='subscribe'),

    path('', profile)
]


