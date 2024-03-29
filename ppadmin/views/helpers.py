import urllib

from functools import wraps

from django.core.cache import cache
from django.urls import reverse
from django.shortcuts import HttpResponseRedirect


def staff_required(func):
    def decorator(request, *args, **kwargs):
        cached_is_staff = cache.get('user_%s_is_staff' % str(request.user.id))
        if cached_is_staff is not None:
            user_is_staff = bool(cached_is_staff)
        else:
            user_is_staff = request.user.is_staff
            # cache for 30 mins
            cache.set(
                'user_%s_is_staff' % str(request.user.id), user_is_staff, 1800
            )

        if user_is_staff:
            return func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('permission_denied'))
    return wraps(func)(decorator)


class StaffUserMixin(object):

    def dispatch(self, request, *args, **kwargs):
        cached_is_staff = cache.get('user_%s_is_staff' % str(request.user.id))
        if cached_is_staff is not None:
            user_is_staff = bool(cached_is_staff)
        else:
            user_is_staff = self.request.user.is_staff
            cache.set(
                'user_%s_is_staff' % str(request.user.id), user_is_staff, 1800
            )
        if not user_is_staff:
            return HttpResponseRedirect(reverse('permission_denied'))
        return super(StaffUserMixin, self).dispatch(request, *args, **kwargs)
