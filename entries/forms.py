from django import forms

from .models import Entry, CATEGORY_CHOICES


class EntryCreateUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
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
        user_cats = Entry.objects.filter(user=user)\
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
            # disallow editing of category and video url after entry submitted
            self.already_submitted = True
            self.fields['category'].widget.attrs.update({'class': 'hide'})
            self.fields['video_url'].widget.attrs.update({'class': 'hide'})

        if not self.instance.id and cat_choices[0][0] != 'DOU' \
                and self.fields['category'].initial != 'DOU':
                self.hide_doubles = True

    def clean_video_url(self):
        video_url = self.cleaned_data['video_url']
        if video_url == 'http://' and 'submitted' not in self.data:
            return ''
        return video_url

    def clean(self):
        super(EntryCreateUpdateForm, self).clean()
        # make sure all fields except stage name and song choice are completed
        # for submitted entries
        if 'submitted' in self.data:
            required_fields = ['category', 'video_url', 'biography']
            for field in required_fields:
                field_data = self.cleaned_data.get(field)
                if not field_data:
                    self.add_error(field, 'This field is required')

            if self.cleaned_data['category'] == 'DOU':
                doubles_required_fields = ['partner_name', 'partner_email']
                for field in doubles_required_fields:
                    field_data = self.cleaned_data.get(field)
                    if not field_data:
                        self.add_error(field, 'This field is required')

        # Add button on form to check partner registered and disclaimer complete (ajax)
        # Ajax partner fields with category selection

    class Meta:
        model = Entry
        fields = (
            'stage_name', 'category', 'song', 'video_url', 'biography',
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
