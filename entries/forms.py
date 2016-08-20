from django import forms

from .models import Entry, CATEGORY_CHOICES


class EntryCreateUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(EntryCreateUpdateForm, self).__init__(*args, **kwargs)

        self.fields['video_url'] = forms.URLField(
            max_length=255,  help_text="URL for your video entry",
            initial="http://",
            widget=forms.TextInput(attrs={'class': "form-control"})
        )

        user_cats = Entry.objects.filter(user=user)\
            .values_list('category', flat=True)
        cat_choices = [
            choice for choice in CATEGORY_CHOICES if choice[0] not in user_cats
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

    def clean(self):
        pass
        # TODO
        # if submit, make sure all fields are complete
        # if category is doubles, check partner name and email entered
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
