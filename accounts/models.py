# -*- coding: utf-8 -*-

import logging
import pytz

from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


def disclaimer_cache_key(user):
    return 'user_{}_has_disclaimer'.format(user.id)


def has_disclaimer(user):
    cache_key = disclaimer_cache_key(user)
    # get disclaimer from cache
    cached_disclaimer = cache.get(cache_key)
    if cached_disclaimer is not None:
        cached_disclaimer = bool(cached_disclaimer)
    else:
        cached_disclaimer = bool(
            OnlineDisclaimer.objects.select_related('user').filter(user=user)
        )
        # set cache; never expires (will only be invalidated if disclaimer is
        # deleted - see post_delete signal)
        cache.set(cache_key, cached_disclaimer, None)
    return cached_disclaimer


# Decorator for django models that contain readonly fields.
def has_readonly_fields(original_class):
    def store_read_only_fields(sender, instance, **kwargs):
        if not instance.id:
            return
        for field_name in sender.read_only_fields:
            val = getattr(instance, field_name)
            setattr(instance, field_name + "_oldval", val)

    def check_read_only_fields(sender, instance, **kwargs):
        if not instance.id:
            return
        for field_name in sender.read_only_fields:
            old_value = getattr(instance, field_name + "_oldval")
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                raise ValueError("Field %s is read only." % field_name)

    models.signals.post_init.connect(store_read_only_fields, original_class, weak=False) # for load
    models.signals.post_save.connect(store_read_only_fields, original_class, weak=False) # for save
    models.signals.pre_save.connect(check_read_only_fields, original_class, weak=False)
    return original_class


WAIVER_TERMS = """
I hereby declare that I have read and understood all the rules of the Pole Performance categories and agree to represent the competition in a professional manner during and prior to the event.

I agree that I am available all day on March 11th 2018.

I understand that my entry will not be accepted until I have paid the appropriate entry fee and that all judges’ decisions are final.

I am taking part in Pole Performance entirely at my own risk. Pole Performance is not responsible for any injury/death caused by my participation in this event.

I assume full responsibility for my participation, knowing the risks involved, and I hold Pole Performance and Carnegie Hall staff/volunteers free from any liability.

I am not pregnant and have not been pregnant in the past three months.

I am deemed physically fit to participate in exercise and have no health or heart conditions that may affect my ability to participate safely in a pole competition.

I give permission for my photo to be taken and used for advertisement and promotional purposes for Pole Performance.

I agree to the above T & C’s and release of liability. I have fully read and understood all information given to me by Pole Performance and free and  voluntarily sign without any inducement.
"""


@has_readonly_fields
class OnlineDisclaimer(models.Model):
    read_only_fields = ('waiver_terms', )

    user = models.OneToOneField(
        User, related_name='online_disclaimer', on_delete=models.CASCADE
    )
    date = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=255, verbose_name='name')
    emergency_contact_relationship = models.CharField(max_length=255, verbose_name='relationship')
    emergency_contact_phone = models.CharField(max_length=255, verbose_name='contact number')
    waiver_terms = models.CharField(
        max_length=2048, default=WAIVER_TERMS
    )
    terms_accepted = models.BooleanField()

    def __str__(self):
        return '{} - {}'.format(self.user.username, self.date.astimezone(
                pytz.timezone('Europe/London')
            ).strftime('%d %b %Y, %H:%M'))

    def save(self, **kwargs):
        if not self.id:
            self.waiver_terms = WAIVER_TERMS

            ActivityLog.objects.create(
                log="Waiver created: {}".format(self.__str__())
            )

            # set cache; never expires (will only be invalidated if disclaimer
            # is deleted - see post_delete signal)
            cache.set(disclaimer_cache_key(self.user), True, 0)

        super(OnlineDisclaimer, self).save()


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    pole_school = models.CharField(max_length=255, null=True, blank=True)
    dob = models.DateField(verbose_name='date of birth')
    address = models.CharField(max_length=512)
    postcode = models.CharField(max_length=10)
    phone = models.CharField(max_length=255)

    def __str__(self):
        return self.user.username
