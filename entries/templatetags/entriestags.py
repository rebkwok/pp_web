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
def format_status(status):
    return STATUS_CHOICES_DICT[status]