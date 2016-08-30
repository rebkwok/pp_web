"""
Email warnings for unsubmitted and submitted/video enry unpaid entries 3 days
before closing date
RUNS ONCE ONLY ON A SPECIFIED DATE (THE CLOSING DATE) - SET AS AT IN CRON
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from activitylog.models import ActivityLog

from ...models import Entry
from ...email_helpers import send_pp_email


class Command(BaseCommand):
    help = 'email warnings for unpaid submitted and unsubmitted entries 3 ' \
           'days before closing date'

    def handle(self, *args, **options):
        entries = Entry.objects.select_related('user').filter(
            entry_year=settings.CURRENT_ENTRY_YEAR,
            withdrawn=False, status__in=['in_progress', 'submitted'],
            video_entry_paid=False
        )

        for entry in entries:
            ctx = {
                'entry': entry,
                'entry_close_date': settings.ENTRIES_CLOSE_DATE,
            }
            send_pp_email(
                None, 'Pole Performance entries are closing soon!',
                ctx, 'entries/email/entry_closing_auto_warn.txt',
                'entries/email/entry_closing_auto_warn.html',
                to_list=[entry.user.email]
            )

        if entries:
            msg = 'Warning emails sent for in progress/unpaid submitted ' \
                  'entries pre-closing date: {}'.format(
                    ', '.join([str(entry.id) for entry in entries])
                    )
            self.stdout.write(msg)
            ActivityLog.objects.create(log='CRON: {}'.format(msg))
        else:
            self.stdout.write(
                'No warning emails to send for in progress/unpaid submitted ' \
                'entries pre-closing date'
            )

