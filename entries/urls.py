from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.entries_home, name='entries_home'),
    url(
        r'^myentries/new/$', views.EntryCreateView.as_view(),
        name='create_entry'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/edit/$', views.EntryUpdateView.as_view(),
        name='edit_entry'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/selected/edit/$',
        views.SelectedEntryUpdateView.as_view(), name='edit_selected_entry'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/video-submission-payment/$',
        views.entry_video_payment,
        name='video_payment'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/selected-entry-payment/$',
        views.entry_selected_payment,
        name='selected_payment'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/withdraw-entry-payment/$',
        views.entry_withdrawal_payment,
        name='withdrawal_payment'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/delete/$',
        views.EntryDeleteView.as_view(),
        name='delete_entry'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/withdraw/$',
        views.EntryWithdrawView.as_view(),
        name='withdraw_entry'
    ),
    url(
        r'^myentries/(?P<ref>[\w-]+)/confirm/$',
        views.EntryConfirmView.as_view(),
        name='confirm_entry'
    ),
    url(
        r'^myentries/check_partner/$', views.check_partner,
        name='check_partner'
    ),
    url(
        r'^myentries/$', views.EntryListView.as_view(), name='user_entries'
    ),
]