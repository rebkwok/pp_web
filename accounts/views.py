from django.contrib import messages
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.views.generic import UpdateView, CreateView, FormView
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.safestring import mark_safe

from braces.views import LoginRequiredMixin

from allauth.account.views import LoginView, SignupView

from .forms import DataPrivacyAgreementForm, DisclaimerForm, ProfileForm
from .models import DataPrivacyPolicy, has_disclaimer, SignedDataPrivacy, \
    UserProfile
from .utils import has_active_data_privacy_agreement



def profile(request):
    if DataPrivacyPolicy.current_version() > 0 and request.user.is_authenticated \
            and not has_active_data_privacy_agreement(request.user):
        return HttpResponseRedirect(
            reverse('accounts:data_privacy_review') + '?next=' + request.path
        )
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


class SignedDataPrivacyCreateView(LoginRequiredMixin, FormView):
    template_name = 'account/data_privacy_review.html'
    form_class = DataPrivacyAgreementForm

    def dispatch(self, *args, **kwargs):
        if has_active_data_privacy_agreement(self.request.user):
            return HttpResponseRedirect(
                self.request.GET.get('next', reverse('booking:events'))
            )
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['next_url'] = self.request.GET.get('next')
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        update_needed = (
            SignedDataPrivacy.objects.filter(
                user=self.request.user,
                version__lt=DataPrivacyPolicy.current_version()
            ).exists() and not has_active_data_privacy_agreement(
                self.request.user)
        )

        context.update({
            'data_protection_policy': DataPrivacyPolicy.current(),
            'update_needed': update_needed
        })
        return context

    def form_valid(self, form):
        user = self.request.user
        SignedDataPrivacy.objects.create(
            user=user, version=form.data_privacy_policy.version
        )
        return self.get_success_url()

    def get_success_url(self):
        return HttpResponseRedirect(reverse('accounts:profile'))


def data_privacy_policy(request):
    return render(
        request, 'account/data_privacy_policy.html',
        {'data_privacy_policy': DataPrivacyPolicy.current()}
    )


def cookie_policy(request):
    return render(
        request, 'account/cookie_policy.html',
        {'data_privacy_policy': DataPrivacyPolicy.current()}
    )