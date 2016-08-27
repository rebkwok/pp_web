import logging

from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib import messages

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import get_object_or_404, \
    HttpResponseRedirect, render_to_response
from django.views.generic import DetailView, ListView

from braces.views import LoginRequiredMixin

from ppadmin.forms import EntryFilterForm, EntrySelectionFilterForm

from ppadmin.views.helpers import staff_required, StaffUserMixin

from activitylog.models import ActivityLog
from entries.models import Entry, CATEGORY_CHOICES_DICT


logger = logging.getLogger(__name__)


class EntryListView(LoginRequiredMixin,  StaffUserMixin,  ListView):

    model = Entry
    template_name = 'ppadmin/entries_list.html'
    context_object_name = 'entries'
    paginate_by = 30

    def get_queryset(self):
        user_filter = self.request.GET.get('user')
        cat_filter = self.request.GET.get('cat_filter')
        status_filter = self.request.GET.get('status_filter')
        reset = self.request.GET.get('reset')
        queryset = Entry.objects.select_related('user')\
            .filter(entry_year=settings.CURRENT_ENTRY_YEAR)\
            .order_by('category', 'user__first_name')

        if user_filter:
            queryset = queryset.filter(user__id=user_filter)
        elif not (cat_filter and status_filter) or \
                (status_filter == 'all_excl' and cat_filter == 'all') or \
                reset:
            # by default, exclude withdrawn and in progress
            queryset = queryset.filter(withdrawn=False)\
                .exclude(status='in_progress')
        else:
            if cat_filter and cat_filter != 'all':
                queryset = queryset.filter(category=cat_filter)

            if status_filter:
                if status_filter == 'all_excl':
                    queryset = queryset.filter(withdrawn=False)\
                        .exclude(status='in_progress')
                elif status_filter == 'withdrawn':
                    queryset = queryset.filter(withdrawn=True)
                elif status_filter != 'all':
                    queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super(EntryListView, self).get_context_data(**kwargs)
        cat_filter = self.request.GET.get('cat_filter')
        status_filter = self.request.GET.get('status_filter')
        reset = self.request.GET.get('reset')

        if reset:
            context['filter_form'] = EntryFilterForm(
                initial={
                    'cat_filter': 'all', 'status_filter': 'all_excl'
                }
            )
        else:
            context['filter_form'] = EntryFilterForm(
                initial={
                    'cat_filter': cat_filter, 'status_filter': status_filter
                }
            )
        return context


class EntryDetailView(LoginRequiredMixin,  StaffUserMixin,  DetailView):

    model = Entry
    template_name = 'ppadmin/entry_detail.html'
    context_object_name = 'entry'

    def get_object(self, queryset=None):
        return get_object_or_404(Entry, entry_ref=self.kwargs['ref'])


class EntrySelectionListView(LoginRequiredMixin,  StaffUserMixin,  ListView):
    model = Entry
    template_name = 'ppadmin/entries_selection_list.html'
    context_object_name = 'entries'
    paginate_by = 30

    def get_queryset(self):
        cat_filter = self.request.GET.get('cat_filter', 'all')
        hide_rejected = self.request.GET.get('hide_rejected', False)

        queryset = Entry.objects.select_related('user')\
            .filter(
                entry_year=settings.CURRENT_ENTRY_YEAR,
                status__in=[
                    'submitted', 'selected', 'selected_confirmed', 'rejected'
                ],
                withdrawn=False
            )\
            .order_by('category', 'user__first_name')

        if cat_filter != 'all':
            queryset = queryset.filter(category=cat_filter)

        if hide_rejected:
            queryset = queryset.exclude(status='rejected')

        return queryset

    def get_context_data(self, **kwargs):
        cat_filter = self.request.GET.get('cat_filter', 'all')
        hide_rejected = self.request.GET.get('hide_rejected', False)
        ctx = super(EntrySelectionListView, self).get_context_data(**kwargs)
        ctx.update({
            'filter_form': EntrySelectionFilterForm(
                initial={
                    'cat_filter': cat_filter, 'hide_rejected': hide_rejected
                }
            ),
            'doubles': cat_filter == 'DOU',
            'category': cat_filter
        })
        return ctx


@login_required
@staff_required
def toggle_selection(request, entry_id, decision=None):
    template = "ppadmin/includes/selection_status.txt"

    entry = Entry.objects.select_related('user').get(id=entry_id)

    if not entry.status == "selected_confirmed":
        if entry.status != decision:
            old_status = entry.status
            if decision == "selected":
                entry.status = 'selected'
            elif decision == "rejected":
                entry.status = 'rejected'
            elif decision == "undecided":
                entry.status = 'submitted'
            entry.save()

            ActivityLog.objects.create(
                log="Entry {entry_id} ({category}) - user {username} - "
                    "changed from {old_status} to {decision} by admin "
                    "user {adminuser}".format(
                        entry_id=entry_id,
                        category=CATEGORY_CHOICES_DICT[entry.category],
                        username=entry.user.username,
                        old_status=old_status,
                        decision=decision,
                        adminuser=request.user.username
                    )
            )

    return render_to_response(template, {'entry': entry})


@login_required
@staff_required
def notify_users(request):
    unnotified_entries = Entry.objects.select_related('user').filter(
        status__in=['selected', 'rejected'], withdrawn=False,
        notified=False
    )

    # TODO
    # GET: show list of users to be notified - categpry and status
    # POST: send emails to unnotified users, redirect to selection list
