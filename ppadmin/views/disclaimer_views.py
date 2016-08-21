import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.views.generic import UpdateView, DeleteView
from django.utils import timezone

from braces.views import LoginRequiredMixin

from accounts.models import OnlineDisclaimer

from ppadmin.forms import AdminDisclaimerForm
from ppadmin.utils import str_int, dechaffify
from ppadmin.views.helpers import staff_required, StaffUserMixin

from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


@login_required
@staff_required
def user_disclaimer(request, encoded_user_id):
    user_id = dechaffify(str_int(encoded_user_id))
    disclaimer = OnlineDisclaimer.objects.get(user__id=user_id)
    ctx = {'disclaimer': disclaimer, 'encoded_user_id': encoded_user_id}

    return TemplateResponse(
        request, "ppadmin/user_disclaimer.html", ctx
    )


class DisclaimerUpdateView(LoginRequiredMixin, StaffUserMixin, UpdateView):

    model = OnlineDisclaimer
    form_class = AdminDisclaimerForm
    template_name = 'ppadmin/update_user_disclaimer.html'

    def get_object(self):
        encoded_user_id = self.kwargs.get('encoded_user_id')
        user_id = dechaffify(str_int(encoded_user_id))
        return get_object_or_404(OnlineDisclaimer, user__id=user_id)

    def get_context_data(self, **kwargs):
        context = super(DisclaimerUpdateView, self).get_context_data(**kwargs)
        user = self.get_object().user
        context['user'] = user
        return context

    def form_valid(self, form):
        changed = form.changed_data
        if 'dob' in form.changed_data:
            old = OnlineDisclaimer.objects.get(id=self.object.id)
            if old.dob == form.instance.dob:
                changed.remove('dob')
        if 'password' in form.changed_data:
             changed.remove('password')

        if changed:
            disclaimer = form.save(commit=False)
            password = form.cleaned_data['password']
            if disclaimer.user.check_password(password):
                disclaimer.date_updated = timezone.now()
                disclaimer.save()
                messages.success(
                    self.request,
                    "Disclaimer for {} has been updated".format(
                        disclaimer.user.username
                    )
                )
                ActivityLog.objects.create(
                    log="Online disclaimer for {} updated by admin "
                        "user {} (user password supplied)".format(
                        disclaimer.user.username, self.request.user.username
                    )
                )
            else:
                messages.error(self.request, "Password is incorrect")
                form = AdminDisclaimerForm(form.data)
                return TemplateResponse(
                    self.request, self.template_name, {'form': form}
                )
        else:
            messages.info(self.request, "No changes made")

        return super(DisclaimerUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('ppadmin:users')


class DisclaimerDeleteView(LoginRequiredMixin, StaffUserMixin, DeleteView):

    model = OnlineDisclaimer
    fields = '__all__'
    template_name = 'ppadmin/delete_user_disclaimer.html'

    def dispatch(self, *args, **kwargs):
        encoded_user_id = self.kwargs.get('encoded_user_id')
        user_id = dechaffify(str_int(encoded_user_id))
        self.user = User.objects.get(id=user_id)
        return super(DisclaimerDeleteView, self).dispatch(*args, **kwargs)

    def get_object(self):
        return get_object_or_404(OnlineDisclaimer, user=self.user)

    def get_context_data(self, **kwargs):
        context = super(DisclaimerDeleteView, self).get_context_data(**kwargs)
        context['user'] = self.user
        return context

    def get_success_url(self):
        messages.success(
            self.request, "Disclaimer deleted for {} {} ({})".format(
                self.user.first_name, self.user.last_name, self.user.username
            )
        )
        ActivityLog.objects.create(
            log="Disclaimer deleted for {} {} ({}) by admin user {}".format(
                self.user.first_name, self.user.last_name, self.user.username,
                self.request.user.username
            )
        )
        return reverse('ppadmin:users')
