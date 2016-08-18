from django import template
from django.conf import settings

register = template.Library()


@register.assignment_tag
def entries_open():
    return settings.ENTRIES_OPEN
