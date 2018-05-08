# -*- coding: utf-8 -*-

import logging
import pytz

from math import floor

from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from activitylog.models import ActivityLog

from .utils import active_data_privacy_cache_key


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


@has_readonly_fields
class CookiePolicy(models.Model):
    read_only_fields = ('content', 'version', 'issue_date')

    content = models.TextField()
    version = models.DecimalField(unique=True, decimal_places=1, max_digits=100)
    issue_date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Cookie Policies"

    @classmethod
    def current_version(cls):
        current_policy = CookiePolicy.current()
        if current_policy is None:
            return 0
        return current_policy.version

    @classmethod
    def current(cls):
        return CookiePolicy.objects.order_by('version').last()

    def __str__(self):
        return 'Cookie Policy - Version {}'.format(self.version)

    def save(self, **kwargs):
        if not self.id:
            current = CookiePolicy.current()
            if current and current.content == self.content:
                raise ValidationError('No changes made to content; not saved')

        if not self.id and not self.version:
            # if no version specified, go to next major version
            self.version = floor((CookiePolicy.current_version() + 1))
        super(CookiePolicy, self).save(**kwargs)
        ActivityLog.objects.create(
            log='Cookie Policy version {} created'.format(self.version)
        )


@has_readonly_fields
class DataPrivacyPolicy(models.Model):
    read_only_fields = ('content', 'version', 'issue_date')

    content = models.TextField()
    version = models.DecimalField(unique=True, decimal_places=1, max_digits=100)
    issue_date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Data Privacy Policies"

    @classmethod
    def current_version(cls):
        current_policy = DataPrivacyPolicy.current()
        if current_policy is None:
            return 0
        return current_policy.version

    @classmethod
    def current(cls):
        return DataPrivacyPolicy.objects.order_by('version').last()

    def __str__(self):
        return 'Data Privacy Policy - Version {}'.format(self.version)

    def save(self, **kwargs):

        if not self.id:
            current = DataPrivacyPolicy.current()
            if current and current.content == self.content:
                raise ValidationError('No changes made to content; not saved')

        if not self.id and not self.version:
            # if no version specified, go to next major version
            self.version = floor((DataPrivacyPolicy.current_version() + 1))
        super().save(**kwargs)
        ActivityLog.objects.create(
            log='Data Privacy Policy version {} created'.format(self.version)
        )


class SignedDataPrivacy(models.Model):
    read_only_fields = ('date_signed', 'version')

    user = models.ForeignKey(
        User, related_name='data_privacy_agreement', on_delete=models.CASCADE
    )
    date_signed = models.DateTimeField(default=timezone.now)
    version = models.DecimalField(decimal_places=1, max_digits=100)

    class Meta:
        unique_together = ('user', 'version')
        verbose_name = "Signed Data Privacy Agreement"

    def __str__(self):
        return '{} - V{}'.format(self.user.username, self.version)

    @property
    def is_active(self):
        return self.version == DataPrivacyPolicy.current_version()

    def save(self, **kwargs):
        if not self.id:
            ActivityLog.objects.create(
                log="Signed data privacy policy agreement created: {}".format(self.__str__())
            )
        super(SignedDataPrivacy, self).save()
        # cache agreement
        if self.is_active:
            cache.set(
                active_data_privacy_cache_key(self.user), True, timeout=600
            )

    def delete(self, using=None, keep_parents=False):
        # clear cache if this is the active signed agreement
        if self.is_active:
            cache.delete(active_data_privacy_cache_key(self.user))
        super(SignedDataPrivacy, self).delete(using, keep_parents)
