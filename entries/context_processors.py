from django.conf import settings

from entries.models import CATEGORY_CHOICES_DICT, LATE_ENTRY_CATEGORY_CHOICES
from entries.utils import all_entries_open, late_categories_entries_open



def pp_email(request):
    return {'pp_email': settings.DEFAULT_STUDIO_EMAIL}


def entries(request):
    entries_open, open_date, late_close_date = late_categories_entries_open()
    _, _, close_date = all_entries_open()

    late_category_names = set(dict(LATE_ENTRY_CATEGORY_CHOICES).values())
    all_category_names = set(dict(CATEGORY_CHOICES_DICT).values())
    early_category_names = all_category_names - late_category_names
    late_categories = ', '.join(late_category_names)
    early_categories = ', '.join(early_category_names)

    return {
        'entries_open': entries_open,
        'entries_open_date': open_date,
        'entries_close_date': close_date,
        'late_entries_close_date': late_close_date,
        'early_categories': early_categories,
        'late_categories': late_categories
    }

