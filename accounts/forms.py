from datetime import datetime

from dateutil.relativedelta import relativedelta

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone


from accounts import validators as account_validators
from .models import DataPrivacyPolicy, SignedDataPrivacy, \
    OnlineDisclaimer, WAIVER_TERMS, UserProfile


class AccountFormMixin:

    def clean(self):
        dob = self.data.get('dob', None)
        if dob and self.errors.get('dob'):
            del self.errors['dob']
        if dob:
            try:
                dob = datetime.strptime(dob, '%d %b %Y').date()
                self.cleaned_data['dob'] = dob
            except ValueError:
                self.add_error(
                    'dob', 'Invalid date format.  Select from the date picker '
                           'or enter date in the format e.g. 08 Jun 1990')

            if not self.errors.get('dob'):
                yearsago = datetime.today().date() - relativedelta(years=18)
                if dob > yearsago:
                    self.add_error('dob', 'You must be 18 or over to register')


class SignupForm(AccountFormMixin, forms.Form):
    first_name = forms.CharField(
        max_length=30, label='First name',
        widget=forms.TextInput(
            attrs={
                'class': "form-control", 'placeholder': 'First name',
                'autofocus': 'autofocus'
            }
        )
    )
    last_name = forms.CharField(
        max_length=30, label='Last name',
        widget=forms.TextInput(
            attrs={'class': "form-control", 'placeholder': 'Last name'}
        )
    )
    dob = forms.DateField(
        widget=forms.DateInput(
                attrs={'class': "form-control", 'id': 'dobdatepicker', "autocomplete": "off"},
                format='%d %b %Y'
            )
    )
    pole_school = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # get the current version here to make sure we always display and save
        # with the same version, even if it changed while the form was being
        # completed
        self.fields['email'].widget.attrs.update({'autofocus': 'autofocus'})
        if DataPrivacyPolicy.current():
            self.data_privacy_policy = DataPrivacyPolicy.current()
            self.fields['content'] = forms.CharField(
                initial=self.data_privacy_policy.content,
                required=False
            )
            self.fields['data_privacy_confirmation'] = forms.BooleanField(
                widget=forms.CheckboxInput(attrs={'class': "regular-checkbox"}),
                required=False,
                label='I confirm I have read and agree to the terms of the data ' \
                      'privacy policy'
            )

    def clean_data_privacy_confirmation(self):
        dp = self.cleaned_data.get('data_privacy_confirmation')
        if not dp:
            self.add_error(
               'data_privacy_confirmation',
               'You must check this box to continue'
            )
        else:
            return dp

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

        profile_data = self.cleaned_data.copy()
        non_profile_fields = [
            'first_name', 'last_name', 'password1', 'password2', 'username',
            'email', 'content',
            'data_privacy_confirmation'
        ]
        for field in non_profile_fields:
            if field in profile_data:
                del profile_data[field]

        UserProfile.objects.create(user=user, **profile_data)

        if hasattr(self, 'data_privacy_policy'):
           SignedDataPrivacy.objects.create(
               user=user, version=self.data_privacy_policy.version,
               date_signed=timezone.now()
           )


class ProfileForm(AccountFormMixin, forms.ModelForm):

    pole_school = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': "form-control"})
    )
    dob = forms.DateField(
        widget=forms.DateInput(
                attrs={'class': "form-control", 'id': 'dobdatepicker'},
                format='%d %b %Y'
            )
    )

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        if self.instance.id and hasattr(self.instance, "profile"):
            self.fields['dob'].initial = self.instance.profile.dob.strftime('%d %b %Y')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        existing_users = User.objects.filter(username=username).exclude(id=self.instance.id)
        if existing_users.exists():
            self.add_error(
               'username',
               'A user already exists with this username'
            )
        else:
            return username

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',)
        widgets = {
            'username': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'first_name': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'last_name': forms.TextInput(
                attrs={'class': "form-control"}
            )
        }


class DisclaimerForm(forms.ModelForm):

    terms_accepted = forms.BooleanField(
        validators=[account_validators.validate_confirm],
        required=False,
        widget=forms.CheckboxInput(
            attrs={'class': 'regular-checkbox'}
        ),
        label='Please tick to accept terms'
    )

    password = forms.CharField(
        widget=forms.PasswordInput(),
        label="Please enter your password to submit your data.<br/>"
              "By submitting this form, you confirm that "
              "the information you have provided is complete and accurate.",
        required=True
    )

    def __init__(self, *args, **kwargs):
        super(DisclaimerForm, self).__init__(*args, **kwargs)
        # the agreed-to terms are read-only fields.  For a new disclaimer, we
        # show the default terms from the model.  If we're updating an existing
        # disclaimer, we show the terms that are already on the instance (i.e.
        # the terms the user agreed to before.  THESE WILL NEVER CHANGE!  If the
        # default terms are updated, existing disclaimers will continue to show
        # the old terms that the user agreed to when they first completed the
        # disclaimer

        if self.instance.id:
            # in the DisclaimerForm, these fields are autopoulated based
            self.waiver_terms = self.instance.waiver_terms
        else:
            self.waiver_terms = WAIVER_TERMS

    class Meta:
        model = OnlineDisclaimer
        fields = (
            'emergency_contact_name', 'emergency_contact_relationship',
            'emergency_contact_phone',
            'terms_accepted')

        widgets = {
            'emergency_contact_name': forms.TextInput(
                attrs={
                    'class': 'form-control', 'autofocus': 'autofocus'
                }
            ),
            'emergency_contact_relationship': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'emergency_contact_phone': forms.TextInput(
                attrs={'class': 'form-control'},
            ),
        }


class DataPrivacyAgreementForm(forms.Form):

    confirm = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': "regular-checkbox"}),
        required=False,
        label='I confirm I have read and agree to the terms of the data ' \
              'privacy policy'
    )

    def __init__(self, *args, **kwargs):
        self.next_url = kwargs.pop('next_url')
        super(DataPrivacyAgreementForm, self).__init__(*args, **kwargs)
        self.data_privacy_policy = DataPrivacyPolicy.current()

    def clean_confirm(self):
        confirm = self.cleaned_data.get('confirm')
        if not confirm:
            self.add_error('confirm', 'You must check this box to continue')
        return
