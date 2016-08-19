from django.conf.urls import url
from django.views.generic import RedirectView
from ppadmin.views import user_disclaimer, DisclaimerUpdateView, \
    DisclaimerDeleteView, ActivityLogListView, toggle_subscribed, \
    MailingListView, unsubscribe, UserListView


urlpatterns = [
    url(r'^users/$', UserListView.as_view(), name="users"),
    url(r'^users/(?P<encoded_user_id>[\w-]+)/disclaimer/$',
        user_disclaimer,
        name='user_disclaimer'),
    url(r'^users/(?P<encoded_user_id>[\w-]+)/disclaimer/update/$',
        DisclaimerUpdateView.as_view(),
        name='update_user_disclaimer'),
    url(r'^users/(?P<encoded_user_id>[\w-]+)/disclaimer/delete/$',
        DisclaimerDeleteView.as_view(),
        name='delete_user_disclaimer'),
    url(
        r'activitylog/$', ActivityLogListView.as_view(), name='activitylog'
    ),
    url(
        r'^users/(?P<user_id>\d+)/toggle_subscribed/$',
        toggle_subscribed, name='toggle_subscribed'
    ),
    url(r'^users/mailing-list/$', MailingListView.as_view(), name='mailing_list'),
    url(
        r'^users/(?P<user_id>\d+)/mailing-list/unsubscribe$',
        unsubscribe, name='unsubscribe'
    ),
    url(r'^$',
        RedirectView.as_view(url='/ppadmin/users/', permanent=True)),
]