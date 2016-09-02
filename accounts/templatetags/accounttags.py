from django import template
from django.contrib.auth.models import Group

from ..models import OnlineDisclaimer
from ..models import has_disclaimer as has_waiver

register = template.Library()


@register.filter
def has_disclaimer(user):
    return has_waiver(user)


@register.filter
def subscribed(user):
    group, _ = Group.objects.get_or_create(name='subscribed')
    return group in user.groups.all()
