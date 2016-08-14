from django import template

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
