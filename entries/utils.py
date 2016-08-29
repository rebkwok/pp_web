from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import has_disclaimer

from .models import Entry


def check_partner_email(email):
    ok = False
    try:
        partner = User.objects.get(email=email)
    except User.DoesNotExist:
        partner = None

    result = {'partner': bool(partner)}

    if partner:
        has_disc = has_disclaimer(partner)
        if has_disc:
            result['partner_waiver'] = has_disc

        # check if partner has already created an Entry for doubles
        already_entered = Entry.objects.filter(
            entry_year=settings.CURRENT_ENTRY_YEAR,
            user=partner, category='DOU'
        ).exists()
        result['partner_already_entered'] = already_entered
        ok = has_disc and not already_entered

    return result, ok


def entries_open():
    open_date = datetime.strptime(settings.ENTRIES_OPEN_DATE, "%d/%m/%Y")
    open_date = open_date.replace(tzinfo=timezone.utc)
    close_date = datetime.strptime(settings.ENTRIES_CLOSE_DATE, "%d/%m/%Y")
    close_date = close_date.replace(tzinfo=timezone.utc)
    return open_date < timezone.now() < close_date