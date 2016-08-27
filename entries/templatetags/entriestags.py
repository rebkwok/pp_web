from django import template
from django.conf import settings

from ..models import CATEGORY_CHOICES_DICT, STATUS_CHOICES_DICT

register = template.Library()


@register.assignment_tag
def entries_open():
    return settings.ENTRIES_OPEN


@register.filter
def format_category(category):
    return CATEGORY_CHOICES_DICT[category]


@register.filter
def format_status(entry):
    add_text = ''
    if entry.withdrawn:
        return "Withdrawn"
    elif entry.status == 'rejected':
        return "Unsuccessful"
    elif entry.status == "selected":
        add_text = " - NOT CONFIRMED"
    elif (
            (entry.status == "submitted" and not entry.video_entry_paid) or
            (entry.status in ["selected", "selected_confirmed"] and not
                entry.selected_entry_paid)
    ):
        add_text = " (pending payment)"
    return STATUS_CHOICES_DICT[entry.status] + add_text

@register.filter
def status_class(entry):
    if not entry.withdrawn:
        if entry.status == "submitted":
            if entry.video_entry_paid:
                return "complete info bold"
            return "incomplete info bold"
        if entry.status in ["selected", "selected_confirmed"]:
            if entry.selected_entry_paid:
                return "complete success bold"
            return "incomplete danger bold"
        return ""
    return ""
