import logging
import xlwt

from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from django.urls import reverse
from django.shortcuts import get_object_or_404, HttpResponse, \
    HttpResponseRedirect, render
from django.template.response import TemplateResponse
from django.views.generic import DetailView, FormView, ListView

from braces.views import LoginRequiredMixin

from ppadmin.forms import EntryFilterForm, EntrySelectionFilterForm, \
    ExportEntriesForm

from ppadmin.views.helpers import staff_required, StaffUserMixin

from activitylog.models import ActivityLog
from entries.models import Entry, CATEGORY_CHOICES_DICT, STATUS_CHOICES_DICT
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

    return render(request, template, context={'entry': entry})


@login_required
@staff_required
def notify_users(request, selection_type):
    if selection_type == "selected":
        unnotified_entries = Entry.objects.select_related('user').filter(
            status='selected', withdrawn=False, notified=False,
            entry_year=settings.CURRENT_ENTRY_YEAR
        ).order_by('category')
    elif selection_type == "rejected":
        unnotified_entries = Entry.objects.select_related('user').filter(
            status='rejected', withdrawn=False, notified=False,
            entry_year=settings.CURRENT_ENTRY_YEAR
        ).order_by('category')
    else:
        unnotified_entries = Entry.objects.select_related('user').filter(
            status__in=['selected', 'rejected'], withdrawn=False,
            entry_year=settings.CURRENT_ENTRY_YEAR,
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
                to_list=[user.email]
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
                "user {username} reset by admin user {adminuser} and marked "
                "as not notified (old notification date {date})".format(
                    entry_id=entry_id,
                    category=CATEGORY_CHOICES_DICT[entry.category],
                    username=entry.user.username,
                    adminuser=request.user.username,
                    date=old_notification_date.strftime('%d-%m-%y')
                )
        )

    return render(request, template, context={'entry': entry})


class ExportFormView(LoginRequiredMixin,  StaffUserMixin, FormView):

    form_class = ExportEntriesForm
    template_name = "ppadmin/export_entries.html"

    def form_valid(self, form):
        if 'export' in self.request.POST:
            category = form.cleaned_data['category']
            status = form.cleaned_data['status']
            column_names = form.cleaned_data['include']
            entries = Entry.objects.select_related('user').filter(
                withdrawn=False, entry_year=settings.CURRENT_ENTRY_YEAR
            ).order_by('category')

            if category != 'all':
                entries = entries.filter(category=category)
            if status != 'all':
                entries = entries.filter(status=status)
            return export_data(category, entries, column_names)
        else:
            return TemplateResponse(
                self.request,
                self.template_name,
                {'form': ExportEntriesForm(data=self.request.POST)}
            )


def get_columns_dict(entry=None, name=None, school=None):
    return {
        'name': (u"Name", 3000, name),
        'stage_name': (
            u"Stage Name", 3000, entry.stage_name if entry else None
        ),
        'pole_school': (u"Pole School", 4000, school),
        'category': (
            u"Category", 3000,
            CATEGORY_CHOICES_DICT[entry.category] if entry else None
        ),
        'song': (u"Song", 4000, entry.song if entry else None),
        'biography': (u"Biography", 10000, entry.biography if entry else None),
        'video_url': (
            u"Video Entry URL", 6000, entry.video_url if entry else None
        ),
        'status': (
            u"Status", 4500,
            STATUS_CHOICES_DICT[entry.status] if entry else None
        ),
        'video_entry_paid': (
            u"Video Fee Paid", 2000,
            'Yes' if entry and entry.video_entry_paid else 'No'
        ),
        'selected_entry_paid': (
            u"Entry Fee Paid", 2000,
            'Yes' if entry and entry.selected_entry_paid else 'No'
        ),
    }


def export_data(category, entries, column_names):
    filename = 'competitors_all.xls'
    if category != 'all':
        filename = 'competitors_{}.xls'.format(
            CATEGORY_CHOICES_DICT[category].lower()
        )

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename={}'.format(
        filename
    )
    wb = xlwt.Workbook(encoding='utf-8')

    columns_dict = get_columns_dict()
    columns = [
        (columns_dict[col_name][0], columns_dict[col_name][1])
        for col_name in column_names
    ]

    if category == 'all':
        worksheet_names = CATEGORY_CHOICES_DICT
    else:
        worksheet_names = {category: CATEGORY_CHOICES_DICT[category]}

    for worksheet_category, worksheet_name in worksheet_names.items():
        row_num = 0

        if category == 'all':
            cat_entries = entries.filter(category=worksheet_category)
        else:
            cat_entries = entries

        if cat_entries:
            ws = wb.add_sheet(worksheet_name)

            font_style = xlwt.XFStyle()
            font_style.alignment.wrap = 1
            font_style.font.bold = True

            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], font_style)
                # set column width
                ws.col(col_num).width = columns[col_num][1]

            font_style = xlwt.XFStyle()
            font_style.alignment.wrap = 1

            for entry in cat_entries:
                if entry.category == 'DOU':
                    partner = User.objects.get(email=entry.partner_email)

                school = None
                name = None
                if 'pole_school' in column_names:
                    school = entry.user.profile.pole_school
                    if entry.category == 'DOU':
                        partner_school = partner.profile.pole_school
                        school = '{} ({}{}) / {} ({}{})'.format(
                            school, entry.user.first_name[0],
                            entry.user.last_name[0], partner_school,
                            partner.first_name[0],
                            partner.last_name[0]
                        )

                if 'name' in column_names:
                    name = '{} {}'.format(
                        entry.user.first_name, entry.user.last_name
                    )
                    if entry.category == 'DOU':
                        name += ' & {} {}'.format(
                            partner.first_name, partner.last_name
                        )

                row_num += 1

                columns_dict = get_columns_dict(entry, name, school)
                row = [columns_dict[col_name][2] for col_name in column_names]

                for col_num in range(len(row)):
                    ws.write(row_num, col_num, row[col_num], font_style)

    wb.save(response)
    return response
