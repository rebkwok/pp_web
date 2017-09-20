import logging
import operator

from datetime import datetime
from functools import reduce

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import HttpResponseRedirect
from django.views.generic import ListView

from braces.views import LoginRequiredMixin

from ppadmin.forms import ActivityLogSearchForm
from ppadmin.views.helpers import StaffUserMixin
from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


EMPTY_JOB_TEXT = [
    'CRON: Auto warn/withdraw selected unconfirmed/unpaid run: no action required',

]


class ActivityLogListView(LoginRequiredMixin, StaffUserMixin, ListView):

    model = ActivityLog
    template_name = 'ppadmin/activitylog.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self):
        queryset = ActivityLog.objects.exclude(
            log__in=EMPTY_JOB_TEXT
        ).order_by('-timestamp')
        reset = self.request.GET.get('reset')
        search_submitted = self.request.GET.get('search_submitted')
        search_text = self.request.GET.get('search')
        search_date = self.request.GET.get('search_date')
        hide_empty_cronjobs = self.request.GET.get('hide_empty_cronjobs')

        if reset or (not (search_text or search_date) and hide_empty_cronjobs) or (not reset and not search_submitted):
            return queryset

        if not hide_empty_cronjobs:
            queryset = ActivityLog.objects.all().order_by('-timestamp')

        if search_date:
            try:
                search_date = datetime.strptime(search_date, '%d-%b-%Y')
                start_datetime = search_date
                end_datetime = search_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                queryset = queryset.filter(
                    Q(timestamp__gte=start_datetime) & Q(timestamp__lte=end_datetime)
                ).order_by('-timestamp')
            except ValueError:
                messages.error(
                    self.request, 'Invalid search date format.  Please select '
                    'from datepicker or enter using the format dd-Mmm-YYYY'
                )
                return queryset

        if search_text:
            search_words = search_text.split()
            search_qs = reduce(
                operator.and_, (Q(log__icontains=x) for x in search_words)
            )
            queryset = queryset.filter(search_qs)

        return queryset

    def get_context_data(self):
        context = super(ActivityLogListView, self).get_context_data()
        context['sidenav_selection'] = 'activitylog'

        search_submitted =  self.request.GET.get('search_submitted')
        hide_empty_cronjobs = self.request.GET.get('hide_empty_cronjobs') \
            if search_submitted else 'on'
        search_text = self.request.GET.get('search', '')
        search_date = self.request.GET.get('search_date', None)
        reset = self.request.GET.get('reset')
        if reset:
            hide_empty_cronjobs = 'on'
            search_text = ''
            search_date = None
        form = ActivityLogSearchForm(
            initial={
                'search': search_text, 'search_date': search_date,
                'hide_empty_cronjobs': hide_empty_cronjobs
            })
        context['form'] = form

        return context
