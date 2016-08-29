from django import template
from django.contrib.auth.models import Group

from ..models import OnlineDisclaimer

register = template.Library()


@register.filter
def has_disclaimer(user):
    disclaimer = OnlineDisclaimer.objects.filter(user=user)
    return bool(disclaimer)


@register.filter
def subscribed(user):
    group, _ = Group.objects.get_or_create(name='subscribed')
    return group in user.groups.all()
