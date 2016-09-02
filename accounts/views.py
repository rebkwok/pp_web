from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.views.generic import UpdateView, CreateView
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe

from braces.views import LoginRequiredMixin

from allauth.account.views import LoginView, SignupView

from accounts.forms import DisclaimerForm, ProfileForm
from accounts.models import has_disclaimer, UserProfile
from activitylog.models import ActivityLog

from ppadmin.models import subscribed_cache_key


def profile(request):
    disclaimer = has_disclaimer(request.user)
    return render(request, 'account/profile.html', {'disclaimer': disclaimer})


class ProfileUpdateView(LoginRequiredMixin, UpdateView):

    model = User
    template_name = 'account/update_profile.html'
    form_class = ProfileForm

    def get_object(self):
        return get_object_or_404(
            User, username=self.request.user.username,
            email=self.request.user.email
        )

    def form_valid(self, form):
        user = form.save()
        profile_data = form.cleaned_data.copy()
        # delete the fields that are on the User model
        del profile_data['first_name']
        del profile_data['last_name']
        del profile_data['username']
        UserProfile.objects.update_or_create(
            user=user, **profile_data
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('accounts:profile')


class CustomLoginView(LoginView):

    def get_success_url(self):
        super(CustomLoginView, self).get_success_url()
        ret = self.request.POST.get('next') or self.request.GET.get('next')
        if not ret or ret in [
            '/accounts/password/change/', '/accounts/password/set/',
            '/accounts/password/reset/key/done/'
        ]:
            ret = reverse('accounts:profile')

        return ret


class CustomSignUpView(SignupView):

    def get_context_data(self, **kwargs):
        # add the username to the form if passed in queryparams from login form
        context = super(CustomSignUpView, self).get_context_data(**kwargs)
        username = self.request.GET.get('username', None)
        if username is not None:
            form = context['form']
            form.fields['username'].initial = username
            context['form'] = form
        return context


class DisclaimerCreateView(LoginRequiredMixin, CreateView):

    form_class = DisclaimerForm
    template_name = 'account/disclaimer_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            if has_disclaimer(request.user):
                return HttpResponseRedirect(reverse('accounts:disclaimer_form'))
        return super(DisclaimerCreateView, self)\
            .dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DisclaimerCreateView, self).get_context_data(**kwargs)
        context['disclaimer'] = has_disclaimer(self.request.user)
        return context

    def form_valid(self, form):
        disclaimer = form.save(commit=False)

        password = form.cleaned_data['password']
        if not self.request.user.has_usable_password():
            messages.error(
                self.request,
                mark_safe(
                    "No password set on account.  "
                    "Please <a href='{}'>set a password</a> before "
                    "completing the disclaimer form.".format(
                        reverse('account_set_password')
                    )
                )
            )
            form = DisclaimerForm(form.data)
            return render(self.request, self.template_name, {'form': form})

        if self.request.user.check_password(password):
            disclaimer.user = self.request.user
            disclaimer.save()
        else:
            messages.error(self.request, "Password is incorrect")
            form = DisclaimerForm(form.data)
            return render(self.request, self.template_name, {'form': form})

        return super(DisclaimerCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('accounts:profile')


def data_protection(request):
    return render(request, 'account/data_protection_statement.html')


@login_required
def subscribe_view(request):

    if request.method == 'POST':
        group = Group.objects.get(name='subscribed')
        if 'subscribe' in request.POST:
            cache.set(subscribed_cache_key(request.user), True, None)
            group.user_set.add(request.user)
            messages.success(
                request, 'You have been subscribed to the mailing list'
            )
            ActivityLog.objects.create(
                log='User {} {} ({}) has subscribed to the mailing '
                    'list'.format(
                        request.user.first_name, request.user.last_name,
                        request.user.username
                    )
            )
        elif 'unsubscribe' in request.POST:
            cache.set(subscribed_cache_key(request.user), False, None)
            group.user_set.remove(request.user)
            messages.success(
                request, 'You have been unsubscribed from the mailing list'
            )
            ActivityLog.objects.create(
                log='User {} {} ({}) has unsubscribed from the mailing '
                    'list'.format(
                        request.user.first_name, request.user.last_name,
                        request.user.username
                    )
            )
    return TemplateResponse(
        request, 'account/mailing_list_subscribe.html'
    )
