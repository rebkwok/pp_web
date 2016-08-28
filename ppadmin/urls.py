from django.conf.urls import url
from django.views.generic import RedirectView
from ppadmin.views import user_disclaimer, DisclaimerUpdateView, \
    DisclaimerDeleteView, ActivityLogListView, toggle_subscribed, \
    MailingListView, unsubscribe, UserListView, EntryListView, \
    EntryDetailView, EntryNotifiedListView, \
    EntrySelectionListView, toggle_selection, toggle_selection_reset, \
    notify_users


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
    url(r'^entries/$', EntryListView.as_view(), name="entries"),
    url(
        r'^entries/selection/$', EntrySelectionListView.as_view(),
        name="entries_selection"
    ),
    url(
        r'^entries/selection/notify-selected/$', notify_users,
        {'selection_type': 'selected'}, name="notify_selected_users"),
    url(
        r'^entries/selection/notify-rejected/$', notify_users,
        {'selection_type': 'rejected'}, name="notify_rejected_users"),
    url(
        r'^entries/selection/notify/$', notify_users,
        {'selection_type': 'all'}, name="notify_users"),
    url(
        r'^entries/(?P<entry_id>\d+)/toggle_selection/selected/$',
        toggle_selection, {'decision': 'selected'}
    ),
    url(
        r'^entries/(?P<entry_id>\d+)/toggle_selection/rejected/$',
        toggle_selection, {'decision': 'rejected'}
    ),
    url(
        r'^entries/(?P<entry_id>\d+)/toggle_selection/undecided/$',
        toggle_selection, {'decision': 'undecided'}
    ),
    url(
        r'^entries/notified/$', EntryNotifiedListView.as_view(),
        name="entries_notified"
    ),
    url(
        r'^entries/(?P<entry_id>\d+)/toggle_selection_reset/$',
        toggle_selection_reset
    ),
    url(
        r'^entries/(?P<ref>[\w-]+)/$', EntryDetailView.as_view(), name="entry"
    ),
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
        RedirectView.as_view(url='/ppadmin/entries/', permanent=True)),
]