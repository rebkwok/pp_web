import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib import messages
from django.core.cache import cache
from django.urls import reverse
from django.db.models import Q
from django.shortcuts import HttpResponseRedirect, render_to_response
from django.views.generic import ListView

from braces.views import LoginRequiredMixin

from ppadmin.forms import UserListSearchForm
from ppadmin.models import subscribed_cache_key
from ppadmin.views.helpers import staff_required, StaffUserMixin
from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


NAME_FILTERS = (
    'All', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
)


def _get_name_filter_available(queryset):

    names_list = queryset.distinct().values_list('first_name', flat=True)
    letter_set = set([name[0].lower() for name in names_list if name])

    name_filter_options = []
    for option in NAME_FILTERS:
        if option == "All":
            name_filter_options.append({'value': 'All',  'available': True})
        else:
            name_filter_options.append(
                {
                    'value': option,
                    'available': option.lower() in letter_set
                }
            )
    return name_filter_options


class UserListView(LoginRequiredMixin,  StaffUserMixin,  ListView):

    model = User
    template_name = 'ppadmin/user_list.html'
    context_object_name = 'users'
    paginate_by = 30

    def get_queryset(self):
        queryset = User.objects.all().order_by('first_name')
        reset = self.request.GET.get('reset')
        search_submitted = self.request.GET.get('search_submitted')
        search_text = self.request.GET.get('search')
        filter = self.request.GET.get('filter')

        if reset or (search_submitted and not search_text) or \
                (not reset and not search_submitted and not filter):
            queryset = queryset
        elif search_text:
            queryset = queryset.filter(
                Q(first_name__icontains=search_text) |
                Q(last_name__icontains=search_text) |
                Q(username__icontains=search_text)
            )

        if filter and filter != 'All':
            queryset = queryset.filter(first_name__istartswith=filter)

        return queryset

    def get_context_data(self):
        queryset = self.get_queryset()
        context = super(UserListView,  self).get_context_data()
        context['search_submitted'] = self.request.GET.get('search_submitted')
        context['active_filter'] = self.request.GET.get('filter',  'All')
        search_text = self.request.GET.get('search',  '')
        reset = self.request.GET.get('reset')
        context['filter_options'] = _get_name_filter_available(queryset)

        num_results = queryset.count()
        total_users = User.objects.count()

        if reset:
            search_text = ''
        form = UserListSearchForm(initial={'search': search_text})
        context['form'] = form
        context['num_results'] = num_results
        context['total_users'] = total_users
        return context


@login_required
@staff_required
def toggle_subscribed(request,  user_id):
    user_to_change = User.objects.get(id=user_id)

    if request.method == 'POST':
        group, _ = Group.objects.get_or_create(name='subscribed')
        # subscribed = group in user_to_change.groups.all()
        if user_to_change.subscribed():
            group.user_set.remove(user_to_change)
            cache.set(subscribed_cache_key(user_to_change), False, None)
            ActivityLog.objects.create(
                log="User {} {} ({}) unsubscribed from mailing list by "
                    "admin user {}".format(
                    user_to_change.first_name,
                    user_to_change.last_name,
                    user_to_change.username,
                    request.user.username
                )
            )
        else:
            group.user_set.add(user_to_change)
            cache.set(subscribed_cache_key(user_to_change), True, None)
            ActivityLog.objects.create(
                log="User {} {} ({}) subscribed to mailing list by "
                    "admin user {}".format(
                    user_to_change.first_name,
                    user_to_change.last_name,
                    user_to_change.username,
                    request.user.username
                )
            )
    return render_to_response(
        "ppadmin/includes/subscribed_button.txt",
        {"user": user_to_change}
    )


class MailingListView(LoginRequiredMixin, StaffUserMixin, ListView):
    model = User
    template_name = 'ppadmin/mailing_list.html'
    context_object_name = 'users'

    def get_queryset(self, **kwargs):
        group, _ = Group.objects.get_or_create(name='subscribed')
        return group.user_set.all().order_by('first_name', 'last_name')


def unsubscribe(request, user_id):
    user_to_change = User.objects.get(id=user_id)
    group = Group.objects.get(name='subscribed')
    group.user_set.remove(user_to_change)
    cache.set(subscribed_cache_key(user_to_change), False, None)
    messages.success(
        request,
        "User {} {} ({}) unsubscribed from mailing list.".format(
            user_to_change.first_name,
            user_to_change.last_name,
            user_to_change.username
        )
    )
    ActivityLog.objects.create(
        log="User {} {} ({}) unsubscribed from mailing list by "
            "admin user {}".format(
            user_to_change.first_name,
            user_to_change.last_name,
            user_to_change.username,
            request.user.username
            )
    )
    user_to_change.save()
    return HttpResponseRedirect(reverse('ppadmin:mailing_list'))
