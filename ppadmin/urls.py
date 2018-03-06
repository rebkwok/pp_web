from django.urls import path
from django.views.generic import RedirectView
from ppadmin.views import user_disclaimer, DisclaimerUpdateView, \
    DisclaimerDeleteView, ActivityLogListView, toggle_subscribed, \
    MailingListView, unsubscribe, UserListView, EntryListView, \
    EntryDetailView, EntryNotifiedListView, email_users_view, \
    EntrySelectionListView, toggle_selection, notified_selection_reset, \
    notify_users, export_data, ExportFormView


app_name = 'ppadmin'


urlpatterns = [
    path('users/', UserListView.as_view(), name="users"),
    path('users/<str:encoded_user_id>/disclaimer/',
        user_disclaimer,
        name='user_disclaimer'),
    path('users/<str:encoded_user_id>/disclaimer/update/',
        DisclaimerUpdateView.as_view(),
        name='update_user_disclaimer'),
    path('users/<str:encoded_user_id>/disclaimer/delete/',
        DisclaimerDeleteView.as_view(),
        name='delete_user_disclaimer'),
    path('entries/', EntryListView.as_view(), name="entries"),
    path(
        'entries/selection/', EntrySelectionListView.as_view(),
        name="entries_selection"
    ),
    path(
        'entries/selection/notify-selected/', notify_users,
        {'selection_type': 'selected'}, name="notify_selected_users"),
    path(
        'entries/selection/notify-rejected/', notify_users,
        {'selection_type': 'rejected'}, name="notify_rejected_users"),
    path(
        'entries/selection/notify/', notify_users,
        {'selection_type': 'all'}, name="notify_users"),
    path(
        'entries/<int:entry_id>/toggle_selection/selected/',
        toggle_selection, {'decision': 'selected'}, name='toggle_selected'
    ),
    path(
        'entries/<int:entry_id>)/toggle_selection/rejected/',
        toggle_selection, {'decision': 'rejected'}, name='toggle_rejected'
    ),
    path(
        'entries/<int:entry_id>/toggle_selection/undecided/',
        toggle_selection, {'decision': 'undecided'}, name='toggle_undecided'
    ),
    path(
        'entries/notified/', EntryNotifiedListView.as_view(),
        name="entries_notified"
    ),
    path(
        'entries/<int:entry_id>/notified_selection_reset/',
        notified_selection_reset, name='notified_selection_reset'
    ),
    path(
        'entries/export/', ExportFormView.as_view(), name="export_entries"
    ),
    path(
        'entries/export/excel/', export_data, name="entries_xls"
    ),
    path(
        'entries/<str:ref>/', EntryDetailView.as_view(), name="entry"
    ),
    path(
        'activitylog/', ActivityLogListView.as_view(), name='activitylog'
    ),
    path(
        'users/(<int:user_id>/toggle_subscribed/',
        toggle_subscribed, name='toggle_subscribed'
    ),
    path('users/mailing-list/', MailingListView.as_view(), name='mailing_list'),
    path(
        'users/mailing-list/send/', email_users_view, {'mailing_list': True},
        name='send_mailing_list'
    ),
    path(
        'users/email-users/', email_users_view, name='email_users'
    ),
    path(
        'users/<int:user_id>/mailing-list/unsubscribe/',
        unsubscribe, name='unsubscribe'
    ),
    path('',
        RedirectView.as_view(url='/ppadmin/entries/', permanent=True)),
]