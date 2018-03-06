from django.urls import path

from . import views


app_name = 'entries'


urlpatterns = [
    path('', views.entries_home, name='entries_home'),
    path(
        'judging-criteria/', views.judging_criteria,
        name='judging_criteria'
    ),
    path(
        'myentries/new/', views.EntryCreateView.as_view(),
        name='create_entry'
    ),
    path(
        'myentries/<str:ref>/edit/', views.EntryUpdateView.as_view(),
        name='edit_entry'
    ),
    path(
        'myentries/<str:ref>/selected/edit/',
        views.SelectedEntryUpdateView.as_view(), name='edit_selected_entry'
    ),
    path(
        'myentries/<str:ref>/video-submission-payment/',
        views.entry_video_payment,
        name='video_payment'
    ),
    path(
        'myentries/<str:ref>/selected-entry-payment/',
        views.entry_selected_payment,
        name='selected_payment'
    ),
    path(
        'myentries/<str:ref>/withdraw-entry-payment/',
        views.entry_withdrawal_payment,
        name='withdrawal_payment'
    ),
    path(
        'myentries/<str:ref>/delete/',
        views.EntryDeleteView.as_view(),
        name='delete_entry'
    ),
    path(
        'myentries/<str:ref>/withdraw/',
        views.EntryWithdrawView.as_view(),
        name='withdraw_entry'
    ),
    path(
        'myentries/<str:ref>/confirm/',
        views.EntryConfirmView.as_view(),
        name='confirm_entry'
    ),
    path(
        'myentries/check_partner/', views.check_partner,
        name='check_partner'
    ),
    path(
        'myentries/', views.EntryListView.as_view(), name='user_entries'
    ),
]