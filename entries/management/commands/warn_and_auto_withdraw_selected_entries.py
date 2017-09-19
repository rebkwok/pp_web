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

from ...models import Entry, CATEGORY_CHOICES_DICT, STATUS_CHOICES_DICT
from ...email_helpers import send_pp_email


class Command(BaseCommand):
    help = 'Email warnings for selected unconfirmed and selected_confirmed ' \
           'unpaid 5 days after notification date. Cancel selected unconfirmed ' \
           'and selected_confirmed 7 days after notification date'

    def handle(self, *args, **options):
        # delete old nothing-to-do logs
        ActivityLog.objects.filter(
            log='CRON: Auto warn/withdraw selected unconfirmed/unpaid '
                'run: no action required'
        ).delete()

        selected_unpaid_entries = Entry.objects.select_related('user').filter(
            withdrawn=False,
            status__in=['selected', 'selected_confirmed'],
            selected_entry_paid=False,
            entry_year=settings.CURRENT_ENTRY_YEAR,
        ).order_by('category')

        to_warn = []
        to_withdraw = []
        for entry in selected_unpaid_entries:
            warn_datetime = entry.notified_date + timedelta(days=5)
            withdrawal_datetime = entry.notified_date + timedelta(days=7)
            if timezone.now() > warn_datetime and not entry.reminder_sent:
                # only email once; ignore if reminder_sent flag on entry
                entry.reminder_sent = True
                entry.save()
                to_warn.append(entry)
            elif timezone.now() > withdrawal_datetime:
                entry.withdrawn = True
                entry.save()
                to_withdraw.append(entry)

        # email warnings to users
        for entry in to_warn:
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category],
                'withdrawal_datetime': withdrawal_datetime.strftime('%d %b %Y')
            }

            send_pp_email(
                None, 'Action needed to keep place in Pole Performance Finals',
                ctx, 'entries/email/selected_auto_warn.txt',
                'entries/email/selected_auto_warn.html',
                to_list=[entry.user.email]
            )

        # withdraw email to users
        for entry in to_withdraw:
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category]
            }
            send_pp_email(
                None, 'Your unconfirmed/unpaid entry was automatically withdrawn',
                ctx, 'entries/email/selected_auto_withdraw.txt',
                'entries/email/selected_auto_withdraw.html',
                to_list=[entry.user.email]
            )

        # withdraw email to PP
        if to_withdraw:
            entries_to_withdraw = [
                {
                    'user': '{} {}'.format(
                        entry.user.first_name, entry.user.last_name
                    ),
                    'category': CATEGORY_CHOICES_DICT[entry.category].upper(),
                    'confirmed': 'No' if
                    STATUS_CHOICES_DICT[entry.status] == 'selected' else 'Yes',
                    'paid': 'Yes' if entry.selected_entry_paid else 'No',
                    'notified_date': entry.notified_date.strftime('%d %b %Y')
                } for entry in to_withdraw
                ]
            ctx = {'entries_to_withdraw': entries_to_withdraw}
            send_pp_email(
                None, 'Unconfirmed/unpaid selected entries automatically '
                      'withdrawn',
                ctx, 'entries/email/selected_auto_withdraw_to_studio.txt',
                'entries/email/selected_auto_withdraw_to_studio.html',
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


