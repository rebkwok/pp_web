import logging

from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, \
    HttpResponseRedirect, render_to_response
from django.template.response import TemplateResponse
from django.views.generic import DetailView, ListView

from braces.views import LoginRequiredMixin

from ppadmin.forms import EntryFilterForm, EntrySelectionFilterForm

from ppadmin.views.helpers import staff_required, StaffUserMixin

from activitylog.models import ActivityLog
from entries.models import Entry, CATEGORY_CHOICES_DICT
from entries.email_helpers import send_pp_email


logger = logging.getLogger(__name__)


class EntryListView(LoginRequiredMixin,  StaffUserMixin,  ListView):

    model = Entry
    template_name = 'ppadmin/entries_list.html'
    context_object_name = 'entries'
    paginate_by = 30

    def get_queryset(self):
        user_filter = self.request.GET.get('user')
        cat_filter = self.request.GET.get('cat_filter', 'all')
        status_filter = self.request.GET.get('status_filter', 'all_excl')
        reset = self.request.GET.get('reset')
        queryset = Entry.objects.select_related('user')\
            .filter(entry_year=settings.CURRENT_ENTRY_YEAR)\
            .order_by('category', 'user__first_name')

        if user_filter:
            queryset = queryset.filter(user__id=user_filter)
        elif (status_filter == 'all_excl' and cat_filter == 'all') or \
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


class SelectionMixin(object):

    def dispatch(self, request, *args, **kwargs):
        self.cat_filter = self.request.GET.get('cat_filter', 'all')
        self.hide_rejected = self.request.GET.get('hide_rejected', False)
        return super(SelectionMixin, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Entry.objects.select_related('user')\
            .filter(
                entry_year=settings.CURRENT_ENTRY_YEAR,
                status__in=[
                    'submitted', 'selected', 'selected_confirmed', 'rejected'
                ],
                withdrawn=False
            )\
            .order_by('category', 'user__first_name')

        if self.cat_filter != 'all':
            queryset = queryset.filter(category=self.cat_filter)

        if self.hide_rejected:
            queryset = queryset.exclude(status='rejected')

        return queryset

    def get_context_data(self, **kwargs):
        ctx = super(SelectionMixin, self).get_context_data(**kwargs)
        ctx.update({
            'filter_form': EntrySelectionFilterForm(
                initial={
                    'cat_filter': self.cat_filter,
                    'hide_rejected': self.hide_rejected
                }
            ),
            'doubles': self.cat_filter == 'DOU',
            'category': self.cat_filter
        })
        return ctx


class EntrySelectionListView(
    LoginRequiredMixin,  StaffUserMixin,  SelectionMixin, ListView
):
    model = Entry
    template_name = 'ppadmin/entries_selection_list.html'
    context_object_name = 'entries'
    paginate_by = 30


@login_required
@staff_required
def toggle_selection(request, entry_id, decision=None):
    template = "ppadmin/includes/selection_status.txt"
    entry = Entry.objects.select_related('user').get(id=entry_id)

    if request.method == "POST":
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
def notify_users(request, selection_type):
    if selection_type == "selected":
        unnotified_entries = Entry.objects.select_related('user').filter(
            status='selected', withdrawn=False, notified=False
        ).order_by('category')
    elif selection_type == "rejected":
        unnotified_entries = Entry.objects.select_related('user').filter(
            status='rejected', withdrawn=False, notified=False
        ).order_by('category')
    else:
        unnotified_entries = Entry.objects.select_related('user').filter(
            status__in=['selected', 'rejected'], withdrawn=False,
            notified=False
        ).order_by('category')

    if request.method == 'GET':
        context = {'entries': unnotified_entries}
        return TemplateResponse(
            request, 'ppadmin/notify_users_list.html', context
        )
        # GET: show list of users to be notified - categpry and status

    elif request.method == 'POST':
        ok_sending = []
        problem_sending = []
        for entry in unnotified_entries:
            user = entry.user
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category]
            }
            sent = send_pp_email(
                request,
                'Semi-final results', ctx,
                'ppadmin/email/selection_results.txt',
                'ppadmin/email/selection_results.html',
                [user.email]
            )
            if sent == 'OK':
                entry.notified = True
                entry.save()
                ok_sending.append(
                    '{} {}'.format(user.first_name, user.last_name)
                )
            else:
                problem_sending.append(
                    '{} {} ({})'.format(
                        user.first_name, user.last_name,
                        CATEGORY_CHOICES_DICT[entry.category]
                    )
                )

        ActivityLog.objects.create(
            log="Semi-final results notifications sent to {} by admin user "
                "{}".format(
                    ', '.join(ok_sending), request.user.username
                )
        )
        if ok_sending:
            messages.success(
                request, 'Semi-final results notifications sent to {}'.format(
                    ', '.join(ok_sending)
                )
            )
        if problem_sending:
            messages.error(
                request, 'There was some problem sending semi-final results '
                         'notification emails to the following '
                         'users: {}'.format(
                            ', '.join(problem_sending)
                         )
            )

        return HttpResponseRedirect(reverse('ppadmin:entries_selection'))


class EntryNotifiedListView(
    LoginRequiredMixin,  StaffUserMixin,  SelectionMixin, ListView
):
    model = Entry
    template_name = 'ppadmin/entries_notified_list.html'
    context_object_name = 'entries'
    paginate_by = 30

    def get_queryset(self):
        queryset = super(EntryNotifiedListView, self).get_queryset()
        return queryset.filter(notified=True)


@login_required
@staff_required
def notified_selection_reset(request, entry_id, decision=None):
    template = "ppadmin/includes/notified_status.txt"
    entry = Entry.objects.select_related('user').get(id=entry_id)
    if request.method == "POST":
        old_notification_date = entry.notified_date
        entry.notified = False
        entry.notified_date = None
        entry.save()

        ActivityLog.objects.create(
            log="Notified selected entry {entry_id} ({category}) - "
                "user {username} reset by admin user {adminuser} and marked as "
                "not notified (old notification date {date})".format(
                    entry_id=entry_id,
                    category=CATEGORY_CHOICES_DICT[entry.category],
                    username=entry.user.username,
                    adminuser=request.user.username,
                    date=old_notification_date.strftime('%d-%m-%y')
                )
        )

    return render_to_response(template, {'entry': entry})
