from django import template
from django.contrib.auth.models import Group

from ..models import OnlineDisclaimer

register = template.Library()


@register.assignment_tag
def modify_redirect_field_value(ret_url):
    if ret_url and ret_url in ['/accounts/password/change/', '/accounts/password/set/']:
        return '/accounts/profile'
    return ret_url


@register.filter
def has_disclaimer(user):
    disclaimer = OnlineDisclaimer.objects.filter(user=user)
    return bool(disclaimer)


@register.filter
def subscribed(user):
    group, _ = Group.objects.get_or_create(name='subscribed')
    return group in user.groups.all()


@register.simple_tag
def get_verbose_field_name(instance, field_name):
    return instance._meta.get_field(field_name).verbose_name.title()