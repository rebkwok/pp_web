"""
Email warnings for selected unconfirmed and selected_confirmed unpaid 5 days
after notification date.
Cancel selected unconfirmed and selected_confirmed 7 days after notification
date (email user and PP)
"""
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.management.base import BaseCommand

from activitylog.models import ActivityLog

from ..models import Entry
from ..email_helpers import send_pp_email


class Command(BaseCommand):
    help = 'Email warnings for selected unconfirmed and selected_confirmed ' \
           'unpaid 5 days after notification date. Cancel selected unconfirmed ' \
           'and selected_confirmed 7 days after notification date'

    def handle(self, *args, **options):

        selected_unpaid_entries = Entry.objects.select_related('user').filter(
            withdrawn=False,
            status__in=['selected', 'selected_confirmed'],
            selected_entry_paid=False
        )

        to_warn = []
        to_withdraw = []
        for entry in selected_unpaid_entries:
            warn_datetime = entry.notified_date + timedelta(days=5)
            cancel_datetime = entry.notified_date + timedelta(days=7)
            if warn_datetime > timezone.now() and not entry.reminder_sent:
                # only email once; ignore if reminder_sent flag on entry
                entry.reminder_sent = True
                entry.save()
                to_warn.append(entry)
            elif cancel_datetime > timezone.now():
                entry.withdrawn = True
                entry.save()
                to_withdraw.append(entry)

        # email warnings to users
        for entry in to_warn:
            ctx = {'entry': entry}
            send_pp_email(
                None, 'Action needed to keep place in Pole Performance Finals',
                ctx, 'entries/email/selected_auto_warn.txt',
                'entries/email/selected_auto_warn.html',
                to_list=[entry.user.email]
            )

        # withdraw email to users
        for entry in to_withdraw:
            ctx = {'entry': entry}
            send_pp_email(
                None, 'Your unconfirmed/unpaid entry was automatically withdrawn',
                ctx, 'entries/email/selected_auto_cancel.txt',
                'entries/email/selected_auto_cancel.html',
                to_list=[entry.user.email]
            )

        # withdraw email to PP
        if to_withdraw:
            ctx = {'entries_to_withdraw': to_withdraw}
            send_pp_email(
                None, 'Unconfirmed/unpaid selected entries automatically '
                      'withdrawn',
                ctx, 'entries/email/selected_auto_cancel_to_studio.txt',
                'entries/email/selected_auto_cancel_to_studio.html',
                to_list=[settings.DEFAULT_STUDIO_EMAIL]
            )

        if to_warn:
            msg = 'Warning emails sent for unconfirmed/unpaid selected ' \
                  'entries: {}'.format([entry.id for entry in to_warn])
            self.stdout.write(msg)
            ActivityLog.objects.create(log='CRON: {}'.format(msg))
        else:
            self.stdout.write(
                'No warning emails to send for unconfirmed/unpaid selected '
                'entries'
            )

        if to_withdraw:
            msg = 'Unconfirmed/unpaid selected entries withdrawn and users ' \
                  'notified: {}'.format([entry.id for entry in to_withdraw])
            self.stdout.write(msg)
            ActivityLog.objects.create(log='CRON: {}'.format(msg))
        else:
            self.stdout.write(
                'No unconfirmed/unpaid selected entries to withdraw'
            )

        if not (to_withdraw or to_warn):
            ActivityLog.objects.create(
                log='CRON: Auto warn/withdraw selected unconfirmed/unpaid '
                    'run: no action required'
            )


