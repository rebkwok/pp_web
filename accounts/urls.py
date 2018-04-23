from django.urls import path
from accounts.views import ProfileUpdateView, profile, \
    DisclaimerCreateView, subscribe_view, \
    SignedDataPrivacyCreateView


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
        'data-privacy-review/', SignedDataPrivacyCreateView.as_view(),
         name='data_privacy_review'
    ),
    path('mailing-list/', subscribe_view, name='subscribe'),

    path('', profile)
]
