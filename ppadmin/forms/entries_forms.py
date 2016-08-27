from django import forms

from entries.models import CATEGORY_CHOICES, STATUS_CHOICES


class EntrySelectionFilterForm(forms.Form):

    category_choices = list(CATEGORY_CHOICES)
    category_choices.insert(0, ('all', 'All'))

    cat_filter = forms.CharField(
        widget=forms.Select(
            choices=tuple(category_choices),
            attrs={'onchange': 'form.submit()'}
        ),
        label="Category"
    )


class EntryFilterForm(EntrySelectionFilterForm):

    status_choices = list(STATUS_CHOICES)
    status_choices.insert(0, ('all_excl', 'All (excluding in progress/withdrawn'))
    status_choices.insert(1, ('all', 'All'))
    status_choices.insert(-1, ('withdrawn', 'Withdrawn'))

    status_filter = forms.CharField(
        widget=forms.Select(
            choices=tuple(status_choices),
            attrs={'onchange': 'form.submit()'}
        ),
        label="Status"
    )

