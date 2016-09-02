from django.core.cache import cache
from django.contrib.auth.models import Group, User


def subscribed_cache_key(user):
    return 'user_{}_is_subscribed'.format(user.id)


def subscribed(self):
    cache_key = subscribed_cache_key(self)
    # get disclaimer from cache
    cached_subscribed = cache.get(cache_key)
    if cached_subscribed is not None:
        cached_subscribed = bool(cached_subscribed)
    else:
        group, _ = Group.objects.get_or_create(name='subscribed')
        cached_subscribed = group in self.groups.all()
        # set cache; never expires (will only be invalidated if unsubscribed
        # by user or admin)
        cache.set(cache_key, cached_subscribed, None)
    return cached_subscribed


User.add_to_class("subscribed", subscribed)
