from django import forms
from django.conf import settings

from allauth.account.models import EmailAddress

from .models import Entry, CATEGORY_CHOICES
from .utils import check_partner_email, entries_open


class EntryFormMixin(object):

    def add_doubles_fields_errors(self, partner_email):
        doubles_required_fields = ['partner_name', 'partner_email']
        for field in doubles_required_fields:
            if field not in self.errors:
                field_data = self.cleaned_data.get(field)
                if not field_data:
                    self.add_error(field, 'This field is required')

        if partner_email:
            partner_checks, ok = check_partner_email(partner_email)
            if not ok:
                if not partner_checks.get('partner'):
                    self.add_error(
                        'partner_email', 'Partner is not registered'
                    )
                elif not partner_checks.get('partner_waiver'):
                    self.add_error(
                        'partner_email',
                        'Partner has registered but has not yet '
                        'completed waiver'
                    )
                elif partner_checks.get('partner_already_entered'):
                    self.add_error(
                        'partner_email',
                        'A user with this email address has already '
                        'entered the doubles category'
                    )

    def clean_partner_email(self):
        partner_email = self.cleaned_data.get('partner_email')
        if partner_email:
            emailaddresses = EmailAddress.objects.filter(user=self.user)\
                .values_list('email', flat=True)

            if partner_email in emailaddresses or \
                            partner_email == self.user.email:
                # make sure partner email is different from current user
                self.add_error(
                    'partner_email',
                    'This cannot be one of your own registered email addresses'
                )
            else:
                return partner_email


class EntryCreateUpdateForm(EntryFormMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        initial_data = kwargs.pop('initial_data')
        kwargs['initial'] = initial_data
        super(EntryCreateUpdateForm, self).__init__(*args, **kwargs)

        self.fields['video_url'] = forms.CharField(
            max_length=255,  help_text="URL for your video entry",
            initial="http://",
            widget=forms.TextInput(attrs={'class': "form-control"}),
            required=False,
        )

        # only list the current category (for editing saved entries) and
        # categories not yet entered
        user_cats = Entry.objects.filter(user=self.user)\
            .values_list('category', flat=True)
        cat_choices = [
            choice for choice in CATEGORY_CHOICES if choice[0] not in
            user_cats or
            (self.instance.id and choice[0] == self.instance.category)
        ]

        self.fields['category'].widget.choices = cat_choices

        if user_cats:
            self.fields['category']\
                .help_text = "Only one entry per category; if you want to " \
                             "edit an existing entry, go to My Entries to " \
                             "select it"

        if self.instance.id and self.instance.status != 'in_progress':
            # disallow editing of category after entry submitted
            self.already_submitted = True
            self.fields['category'].widget.attrs.update({'class': 'hide'})

        is_open, _, _ = entries_open()
        if not is_open:
            # disallow editing of video url after entries closed
            self.fields['video_url'].widget.attrs.update({'class': 'hide'})
        self.show_doubles = False
        if self.instance.id and self.instance.category == 'DOU':
            self.show_doubles = True
        elif self.data.get('category') == 'DOU':
            self.show_doubles = True
        elif not self.instance.id and (
                        cat_choices[0][0] == 'DOU' or
                        self.initial.get('category') == 'DOU'
        ):
            self.show_doubles = True

        email_help = self.fields['partner_email'].help_text
        new_email_help = email_help + " Use the button below to check your " \
                                      "partner's information"
        self.fields['partner_email'].help_text = new_email_help

    def clean_video_url(self):
        video_url = self.cleaned_data['video_url']
        if video_url == 'http://' and 'submitted' not in self.data:
            return ''
        return video_url

    def clean(self):
        super(EntryCreateUpdateForm, self).clean()
        partner_email = self.cleaned_data.get('partner_email')

        # make sure all fields except stage name and song choice are completed
        # for submitted entries
        if 'submitted' in self.data:
            required_fields = ['category', 'video_url']
            for field in required_fields:
                field_data = self.cleaned_data.get(field)
                if not field_data:
                    self.add_error(field, 'This field is required')

            if self.cleaned_data['category'] == 'DOU':
                self.add_doubles_fields_errors(partner_email)

    class Meta:
        model = Entry
        fields = (
            'stage_name', 'category', 'video_url',
            'partner_name', 'partner_email'
        )
        widgets = {
            'stage_name': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'category': forms.Select(
                attrs={
                    'class': "form-control", 'onchange': "entryform.submit();"
                }
            ),
            'song': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'biography': forms.Textarea(
                attrs={'class': "form-control"}
            ),
            'partner_name': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'partner_email': forms.EmailInput(
                attrs={'class': "form-control"}
            ),
        }


class SelectedEntryUpdateForm(EntryFormMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(SelectedEntryUpdateForm, self).__init__(*args, **kwargs)
        self.user = self.instance.user
        if self.instance.category == 'DOU':
            self.show_doubles = True
            email_help = self.fields['partner_email'].help_text
            new_email_help = email_help + " Use the button below to check " \
                                          "your partner's information"
            self.fields['partner_email'].help_text = new_email_help
            self.fields['partner_email'].required = True
            self.fields['partner_name'].required = True
        self.fields['biography'].required = True
        self.fields['song'].required = True
        self.fields['song']\
            .help_text = "Please email your song in .mp3 format to {} as " \
                         "soon as possible".format(
            settings.DEFAULT_STUDIO_EMAIL
        )

    def clean(self):
        super(SelectedEntryUpdateForm, self).clean()
        partner_email = self.cleaned_data.get('partner_email')

        # make sure all fields except stage name and song choice are completed
        # for submitted entries
        if self.instance.category == 'DOU':
            self.add_doubles_fields_errors(partner_email)

    class Meta:
        model = Entry
        fields = (
            'stage_name', 'song', 'biography', 'partner_name', 'partner_email'
        )
        widgets = {
            'stage_name': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'song': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'biography': forms.Textarea(
                attrs={'class': "form-control"}
            ),
            'partner_name': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'partner_email': forms.EmailInput(
                attrs={'class': "form-control"}
            ),
        }
