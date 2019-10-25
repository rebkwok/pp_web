"""
Email reminders for selected/confirmed entries without completed bio and song
info
RUNS ONCE ONLY ON A SPECIFIED DATE - SET AS AT IN CRON OR JUST RUN MANUALLY
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils.safestring import mark_safe

from activitylog.models import ActivityLog

from ...models import Entry, CATEGORY_CHOICES_DICT
from ...email_helpers import send_pp_email


class Command(BaseCommand):
    help = 'email reminders for selected/confirmed entries without completed ' \
           'bio and song info'

    def handle(self, *args, **options):
        entries = [
            entry for entry in Entry.objects.select_related('user').filter(
                entry_year=settings.CURRENT_ENTRY_YEAR,
                withdrawn=False, status='selected_confirmed',
            ) if not (entry.biography and entry.song)
        ]

        for entry in entries:
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category],
            }
            send_pp_email(
                None, 'Your Pole Performance entry is incomplete',
                ctx, 'entries/email/incomplete_entry_reminder.txt',
                'entries/email/incomplete_entry_reminder.html',
                to_list=[entry.user.email]
            )

        if entries:
            msg = 'Reminder emails sent for incomplete selected-confirmed ' \
                  'entries: {}'.format(
                    ', '.join([str(entry.id) for entry in entries])
                    )
            self.stdout.write(msg)
            ActivityLog.objects.create(log='CRON: {}'.format(msg))

            # sent support notification
            send_mail('{} Incomplete entry reminders sent'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            ),
                mark_safe('Incomplete entry reminders sent for {}'.format(
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
            self.stdout.write(
                'No incomplete entries.'
            )

