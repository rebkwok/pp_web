from entries.utils import entries_open as check_entries_open

from django.conf import settings


def pp_email(request):
    return {'pp_email': settings.DEFAULT_STUDIO_EMAIL}


def entries_open(request):
    return {
        'entries_open': check_entries_open,
        'entries_open_date': settings.ENTRIES_OPEN_DATE,
        'entries_close_date': settings.ENTRIES_CLOSE_DATE
    }