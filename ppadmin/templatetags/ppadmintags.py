import pytz

from django import template
from django.utils.safestring import mark_safe

from ..utils import int_str, chaffify

from entries.models import STATUS_CHOICES_DICT
from entries.utils import check_partner_email


register = template.Library()

@register.filter
def formatted_uk_date(date):
    """
    return UTC date in uk time
    """
    uk=pytz.timezone('Europe/London')
    return date.astimezone(uk).strftime("%d %b %Y %H:%M")


@register.filter
def encode(val):
    return int_str(chaffify(val))


@register.filter
def abbr_username(user):
    if len(user) > 15:
        return mark_safe("{}-</br>{}".format(user[:12], user[12:]))
    return user


@register.filter
def abbr_name(name):
    if len(name) > 8 and '-' in name:
        split_name = name.split('-')
        return mark_safe(
            "{}-</br>{}".format(split_name[0], '-'.join(split_name[1:]))
        )
    if len(name) > 18:
        return mark_safe("{}-</br>{}".format(name[:15], name[15:]))
    return name


@register.filter
def abbr_email(email):
    if len(email) > 25:
        return "{}...".format(email[:22])
    return email


@register.filter
def abbr_url(url):
    url = url.strip("http://")
    if len(url) > 20:
        return "{}...".format(url[:17])
    return url


@register.filter
def format_status_admin(entry):
    add_text = ''
    if entry.withdrawn:
        if entry.status == "selected_confirmed":
            if entry.withdrawal_fee_paid:
                add_text = " (withdrawn-paid)"
            else:
                add_text = " (withdrawn-unpaid)"
        else:
            add_text = " (withdrawn)"
    elif entry.status == "selected":
        add_text = " - NOT CONFIRMED"
    elif entry.status == "submitted" and not entry.video_entry_paid:
        add_text = " (pending payment)"
    elif entry.status == "selected_confirmed":
        add_text1 = ''
        add_text2 = ''
        if not entry.selected_entry_paid:
            add_text1 = 'payment'
        if not (entry.biography and entry.song):
            add_text2 = 'info'

        if add_text1 and add_text2:
            add_text = ' (pending {} & {})'.format(add_text1, add_text2)
        elif add_text1 or add_text2:
            add_text = ' (pending {}{})'.format(add_text1, add_text2)

    return STATUS_CHOICES_DICT[entry.status] + add_text


@register.filter
def format_selected_status(status):
    return STATUS_CHOICES_DICT[status]
