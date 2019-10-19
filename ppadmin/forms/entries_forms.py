from django.conf import settings
from django import forms

from entries.models import CATEGORY_CHOICES, Entry, STATUS_CHOICES


class CategoryFilterForm(forms.Form):

    category_choices = list(CATEGORY_CHOICES)
    category_choices.insert(0, ('all', 'All'))

    cat_filter = forms.CharField(
        widget=forms.Select(
            choices=tuple(category_choices),
            attrs={'onchange': 'form.submit()', 'class': 'filter-dropdown'}
        ),
        label="Category"
    )


class EntryFilterForm(CategoryFilterForm):

    status_choices = list(STATUS_CHOICES)
    status_choices.insert(0, ('all_excl', 'All (excluding in progress/withdrawn'))
    status_choices.insert(1, ('all', 'All'))
    status_choices.insert(-1, ('withdrawn', 'Withdrawn'))

    status_filter = forms.CharField(
        widget=forms.Select(
            choices=tuple(status_choices),
            attrs={'onchange': 'form.submit()', 'class': 'filter-dropdown'}
        ),
        label="Status"
    )


class EntrySelectionFilterForm(CategoryFilterForm):

    hide_rejected = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={'onchange': 'form.submit()'}
        ),
        label="Hide rejected entries"
    )


class ExportEntriesForm(forms.Form):
    status_choices = list(STATUS_CHOICES)
    status_choices.insert(0, ('all', 'All'))
    category_choices = list(CATEGORY_CHOICES)
    category_choices.insert(0, ('all', 'All (categories on separate sheets)'))

    category = forms.CharField(
        widget=forms.Select(
            choices=tuple(category_choices),
            attrs={'onchange': 'form.submit()', 'class': 'filter-dropdown'}
        ),
        initial="all"

    )

    status = forms.CharField(
        widget=forms.Select(
            choices=tuple(status_choices),
            attrs={'onchange': 'form.submit()', 'class': 'filter-dropdown'}
        ),
        initial='selected_confirmed'
    )

    include_choices = (
        ('name', 'Name'),
        ('stage_name', 'Stage Name'),
        ('pole_school', 'Pole School'),
        ('category', 'Category'),
        ('video_url', 'Video Entry URL'),
        ('song', 'Song'),
        ('biography', 'Biography'),
        ('status', 'Status'),
        ('video_entry_paid', 'Video Fee Paid'),
        ('selected_entry_paid', 'Entry Fee Paid')
    )
    # checkboxes for fields to include
    include = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'select-checkbox'}
        ),
        label="Choose fields to include",
        choices=include_choices,
        initial=[
            'name', 'stage_name', 'pole_school', 'category', 'song',
            'biography'
        ],
        required=True
    )

    def clean(self):
        entries = Entry.objects.filter(
            withdrawn=False, entry_year=settings.CURRENT_ENTRY_YEAR
        ).order_by('category')
        category = self.cleaned_data['category']
        status = self.cleaned_data['status']

        if category != 'all':
            entries = entries.filter(category=category)
        if status != 'all':
            entries = entries.filter(status=status)

        if not entries.exists():
            self.add_error(
                '__all__', 'No entries match selected category/status.'
            )

