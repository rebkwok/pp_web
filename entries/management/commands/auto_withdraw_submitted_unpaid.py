"""
Withdraw submitted/video enry unpaid entries on closing date
Email user
RUNS ONCE ONLY ON A SPECIFIED DATE - SET AS AT IN CRON
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils.safestring import mark_safe

from activitylog.models import ActivityLog

from ...models import Entry, CATEGORY_CHOICES_DICT
from ...email_helpers import send_pp_email


class Command(BaseCommand):
    help = 'Withdraw unpaid submitted entries on closing date and email user'

    def handle(self, *args, **options):
        entries = Entry.objects.filter(
            entry_year=settings.CURRENT_ENTRY_YEAR,
            withdrawn=False, status='submitted', video_entry_paid=False
        )

        for entry in entries:
            entry.withdrawn = True
            entry.save()
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category],
            }
            send_pp_email(
                None, 'Your unpaid entry was automatically withdrawn',
                ctx, 'entries/email/entry_closed_auto_withdraw.txt',
                'entries/email/entry_closed_auto_withdraw.html',
                to_list=[entry.user.email]
            )

        if entries:
            msg = 'Unpaid submitted entries on closing date were withdrawn ' \
                  'and users notified: {}'.format(
                    [entry.id for entry in entries]
                  )
            self.stdout.write(msg)
            ActivityLog.objects.create(log='CRON: {}'.format(msg))

            # sent support notification
            send_mail('{} Unpaid submitted entries withdrawn on closing date'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            ),
                mark_safe('Unpaid submitted entries withdrawn: {}'.format(
                    ', '.join([
                                  '{username} - {category} - id {id} - {status}'.format(
                                      username=entry.user.username,
                                      category=entry.category,
                                      id=entry.id, status=entry.status)
                                  for entry in entries]))
                ),
                settings.DEFAULT_FROM_EMAIL,
                [settings.SUPPORT_EMAIL],
                fail_silently=True)
        else:
            self.stdout.write('No unpaid submitted entries to withdraw')