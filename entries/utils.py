from django.conf import settings
from django.contrib.auth.models import User

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
