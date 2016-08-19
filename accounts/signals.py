from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from activitylog.models import ActivityLog


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, *args, **kwargs):
    # Log when new user created and add to mailing list
    if created:
        ActivityLog.objects.create(
            log='New user registered: {} {}, username {}'.format(
                    instance.first_name, instance.last_name, instance.username
            )
        )
        group = Group.objects.get_or_create(name='subscribed')
        group.user_set.add(instance)
        ActivityLog.objects.create(
            log='New user {} added to mailing list'.format(instance.username)
        )
