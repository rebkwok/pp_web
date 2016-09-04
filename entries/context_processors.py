from datetime import datetime
from entries.utils import entries_open as check_entries_open

from django.conf import settings
from django.utils import timezone

def pp_email(request):
    return {'pp_email': settings.DEFAULT_STUDIO_EMAIL}


def entries_open(request):
    entries_open, open_date, close_date = check_entries_open()
    return {
        'entries_open': entries_open,
        'entries_open_date': open_date,
        'entries_close_date': close_date
    }
