from django import forms
from django.conf import settings

from allauth.account.models import EmailAddress

from .models import Entry, CATEGORY_CHOICES_DICT, CATEGORY_CHOICES_ORDER, LATE_ENTRY_CATEGORY_CHOICES, VALID_CATEGORIES
from .utils import (
    check_partner_email, all_entries_open, late_categories_entries_open
)


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

        all_open, _, _ = all_entries_open()
        late_open, _, _ = late_categories_entries_open()

        # only list the current category (for editing saved entries) and
        # categories not yet entered
        entered_categories = Entry.objects.filter(
            user=self.user, entry_year=settings.CURRENT_ENTRY_YEAR
        ).values_list('category', flat=True)
        entered_categories = {(category, CATEGORY_CHOICES_DICT[category]) for category in entered_categories}
        current_category = {(self.instance.category, CATEGORY_CHOICES_DICT[self.instance.category])} if self.instance.id else set()
        category_choices = tuple((VALID_CATEGORIES - entered_categories) | current_category)

        # remove all categories except late entry categories after first close date
        if late_open and not all_open:
            category_choices = tuple(set(category_choices) - set(LATE_ENTRY_CATEGORY_CHOICES))

        self.fields['category'].widget.choices = tuple(sorted(category_choices, key=lambda x: CATEGORY_CHOICES_ORDER[x[0]]))

        if not current_category:
            self.fields['category'].help_text = "Only one entry per category (you have already entered {}); " \
                                                "go to My Entries to edit an existing entry,".format(', '.join([cat[1] for cat in entered_categories]))

        if self.instance.id and self.instance.status != 'in_progress':
            # disallow editing of category after entry submitted
            self.already_submitted = True
            self.fields['category'].widget.attrs.update({'class': 'hide'})
        else:
            self.already_submitted = False

        late_categories = [cat[0] for cat in LATE_ENTRY_CATEGORY_CHOICES]
        if self.instance.id and (self.instance.category not in late_categories):
            is_open = all_open
        else:
            is_open = late_open

        if not is_open and not self.user.is_superuser:
            # disallow editing of video url after entries closed
            self.fields['video_url'].widget.attrs.update({'class': 'hide'})
        self.show_doubles = False
        if self.instance.id and self.instance.category == 'DOU':
            self.show_doubles = True
        elif self.data.get('category') == 'DOU':
            self.show_doubles = True
        elif not self.instance.id and (
                        category_choices[0][0] == 'DOU' or
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
