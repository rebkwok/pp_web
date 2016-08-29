from datetime import datetime

from dateutil.relativedelta import relativedelta

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from accounts import validators as account_validators
from accounts.models import OnlineDisclaimer, WAIVER_TERMS, UserProfile


class AccountFormMixin(object):

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
                    'dob', 'Invalid date format.  Select from '
                                        'the date picker or enter date in the '
                                        'format e.g. 08 Jun 1990')

            if not self.errors.get('dob'):
                yearsago = datetime.today().date() - relativedelta(years=18)
                if dob > yearsago:
                    self.add_error(
                        'dob', 'You must be 18 or over to register'
                    )

        # password = self.cleaned_data.get('password1')
        # if password:
        #     validate_password(self.cleaned_data['password1'])


class SignupForm(AccountFormMixin, forms.Form):
    first_name = forms.CharField(
        max_length=30, label='First name',
        widget=forms.TextInput(
            {
                'class': "form-control", 'placeholder': 'First name',
                'autofocus': 'autofocus'
            }
        )
    )
    last_name = forms.CharField(
        max_length=30, label='Last name',
        widget=forms.TextInput(
            {'class': "form-control", 'placeholder': 'Last name'}
        )
    )
    dob = forms.DateField(
        widget=forms.DateInput(
                attrs={'class': "form-control", 'id': 'dobdatepicker'},
                format='%d %b %Y'
            )
    )
    address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': "form-control"})
    )
    postcode = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': "form-control"})
    )
    phone = forms.CharField(
        max_length=255, label='phone number',
        widget=forms.TextInput(attrs={'class': "form-control"})
    )
    pole_school = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': "form-control"})
        self.fields['username'].widget.attrs.update({'class': "form-control"})
        self.fields['password1'].widget.attrs.update({'class': "form-control"})
        self.fields['password2'].widget.attrs.update({'class': "form-control"})

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

        profile_data = self.cleaned_data.copy()
        non_profile_fields = [
            'first_name', 'last_name', 'password1', 'password2', 'username',
            'email'
        ]
        for field in non_profile_fields:
            del profile_data[field]

        UserProfile.objects.create(user=user, **profile_data)


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
    address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': "form-control"})
    )
    postcode = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': "form-control"})
    )
    phone = forms.CharField(
        max_length=255, label='phone number',
        widget=forms.TextInput(attrs={'class': "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

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
                attrs={'class': 'form-control'}
            ),
            'emergency_contact_relationship': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'emergency_contact_phone': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
        }
