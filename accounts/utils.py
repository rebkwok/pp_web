# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.cache import cache


def active_data_privacy_cache_key(user):
    from accounts.models import DataPrivacyPolicy
    current_version = DataPrivacyPolicy.current_version()
    return 'user_{}_active_data_privacy_agreement_version_{}'.format(
        user.id, current_version
    )


def has_active_data_privacy_agreement(user):
    key = active_data_privacy_cache_key(user)
    has_active_agreement = cache.get(key)
    if has_active_agreement is None:
        has_active_agreement = any([True for dp in user.data_privacy_agreement.all() if dp.is_active])
        cache.set(key, has_active_agreement, timeout=600)
    return bool(has_active_agreement)
