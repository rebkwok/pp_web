import sys
import os

from datetime import datetime, timedelta
from io import StringIO
from mock import patch
from model_mommy import mommy

from django.test import TestCase, override_settings
from django.conf import settings
from django.core import management
from django.core import mail
from django.db.models import Q
from django.contrib.auth.models import Group, User
from django.utils import timezone

from activitylog.models import ActivityLog
from ..models import Entry


class ManagementCommandsTests(TestCase):

    def setUp(self):
        # redirect stdout so we can test it
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output

    def tearDown(self):
        self.output.close()
        sys.stdout = self.saved_stdout

    def test_email_warnings(self):
        mommy.make(Entry, _quantity=5)
        management.call_command('email_warnings')

        # All emails in progress; one email sent per entry and one support
        self.assertEqual(len(mail.outbox), 6)

    def test_email_warnings_sent_for_correct_entries(self):

        in_progress = mommy.make(
            Entry, status='in_progress', user__email='test_in_progress@test.com'
        )
        submitted_unpaid = mommy.make(
            Entry, status='submitted', video_entry_paid=False,
            user__email='test_unpaid@test.com'
        )
        submitted_paid = mommy.make(
            Entry, status='submitted', video_entry_paid=True,
            user__email='test_paid@test.com'
        )
        management.call_command('email_warnings')

        # Emails sent one per in progress and submitted/unpaid and one support
        self.assertEqual(len(mail.outbox), 3)

        to_emails = [email.to[0] for email in mail.outbox]
        self.assertIn(in_progress.user.email, to_emails)
        self.assertIn(submitted_unpaid.user.email, to_emails)
        self.assertNotIn(submitted_paid.user.email, to_emails)

        self.assertEqual(mail.outbox[2].to, [settings.SUPPORT_EMAIL])

        self.assertEqual(
            self.output.getvalue(),
            'Warning emails sent for in progress/unpaid submitted entries '
            'pre-closing date: {}\n'.format(
                ', '.join([str(in_progress.id), str(submitted_unpaid.id)])
                )
        )

    def test_no_warnings_to_send(self):
        mommy.make(
            Entry, status='selected', user__email='test_in_progress@test.com'
        )
        mommy.make(
            Entry, status='submitted', video_entry_paid=True,
            user__email='test_unpaid@test.com'
        )
        management.call_command('email_warnings')

        # Nothing to send
        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(
            self.output.getvalue(),
            'No warning emails to send for in progress/unpaid submitted ' \
            'entries pre-closing date\n'
        )

    def test_withdraw_submitted_unpaid(self):
        in_progress = mommy.make(
            Entry, status='in_progress', user__email='test_in_progress@test.com'
        )
        submitted_unpaid = mommy.make(
            Entry, status='submitted', video_entry_paid=False,
            user__email='test_unpaid@test.com'
        )
        submitted_unpaid1 = mommy.make(
            Entry, status='submitted', video_entry_paid=False,
            user__email='test_unpaid1@test.com'
        )
        submitted_paid = mommy.make(
            Entry, status='submitted', video_entry_paid=True,
            user__email='test_paid@test.com'
        )
        management.call_command('auto_withdraw_submitted_unpaid')

        # 1 withdrawn; 2 emails: 1 for each withdrawn entry and 1 to support
        self.assertEqual(len(mail.outbox), 3)
        to_emails = [email.to[0] for email in mail.outbox]
        self.assertIn(submitted_unpaid.user.email, to_emails)
        self.assertIn(submitted_unpaid1.user.email, to_emails)
        self.assertNotIn(in_progress.user.email, to_emails)
        self.assertNotIn(submitted_paid.user.email, to_emails)

        self.assertEqual(mail.outbox[2].to, [settings.SUPPORT_EMAIL])

        in_progress.refresh_from_db()
        submitted_unpaid.refresh_from_db()
        submitted_unpaid1.refresh_from_db()
        submitted_paid.refresh_from_db()

        for entry in [in_progress, submitted_paid]:
            self.assertFalse(entry.withdrawn)

        for entry in [submitted_unpaid, submitted_unpaid1]:
            self.assertTrue(entry.withdrawn)

    def test_no_submitted_entries_to_withdraw(self):
        mommy.make(
            Entry, status='selected', user__email='test_in_progress@test.com'
        )
        mommy.make(
            Entry, status='submitted', video_entry_paid=True,
            user__email='test_unpaid@test.com'
        )
        management.call_command('auto_withdraw_submitted_unpaid')

        # Nothing to send
        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(
            self.output.getvalue(),
            'No unpaid submitted entries to withdraw\n'
        )

    @patch('entries.management.commands.warn_and_auto_withdraw_selected_entries.'
        'timezone')
    def test_warn_selected(self, mock_tz):
        """
        Selected unconfirmed and selected_confirmed unpaid get warning emails
        5 days after notification date
        """
        mock_tz.now.return_value = datetime(
            2016, 2, 20, 19, 0, tzinfo=timezone.utc
        )

        # notified 4 days ago
        unconfirmed = mommy.make(
            Entry, status='selected', notified=True,
            notified_date=datetime(2016, 2, 16, 19, 0, tzinfo=timezone.utc),
            reminder_sent=False, user__email='unconfirmed@test.com'
        )
        confirmed_unpaid = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=False,
            notified_date=datetime(2016, 2, 16, 19, 0, tzinfo=timezone.utc),
            reminder_sent=False, user__email='confirmed_unpaid@test.com'
        )
        confirmed_paid = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=True,
            notified_date=datetime(2016, 2, 16, 19, 0, tzinfo=timezone.utc),
            reminder_sent=False, user__email='confirmed_paid@test.com'
        )

        # notified 5 days 1 hr ago
        unconfirmed1 = mommy.make(
            Entry, status='selected', notified=True,
            notified_date=datetime(2016, 2, 15, 18, 0, tzinfo=timezone.utc),
            reminder_sent=False, user__email='unconfirmed1@test.com'
        )
        confirmed_unpaid1 = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=False,
            notified_date=datetime(2016, 2, 15, 18, 0, tzinfo=timezone.utc),
            reminder_sent=False, user__email='confirmed_unpaid1@test.com'
        )
        confirmed_paid1 = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=True,
            notified_date=datetime(2016, 2, 15, 18, 0, tzinfo=timezone.utc),
            reminder_sent=False, user__email='confirmed_paid1@test.com'
        )
        reminder_already_sent = mommy.make(
            Entry, status='selected', notified=True,
            notified_date=datetime(2016, 2, 15, 18, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='already_sent@test.com'
        )

        management.call_command('warn_and_auto_withdraw_selected_entries')

        # Emails sent to the entries with notified date 5 days ago only; not
        # sent for the paid entry or the reminder already sent entry
        self.assertEqual(len(mail.outbox), 2)
        to_emails = [email.to[0] for email in mail.outbox]

        self.assertIn(unconfirmed1.user.email, to_emails)
        self.assertIn(confirmed_unpaid1.user.email, to_emails)

        for entry in [
            unconfirmed, confirmed_unpaid, confirmed_unpaid, confirmed_paid,
            confirmed_paid1, reminder_already_sent
        ]:
            self.assertNotIn(entry.user.email, to_emails)

    @patch('entries.management.commands.warn_and_auto_withdraw_selected_entries.'
        'timezone')
    def test_auto_withdraw_selected(self, mock_tz):
        """
        Selected unconfirmed and selected_confirmed unpaid get automatically
        withdrawn and users notified 7 days after notification date
        """
        mock_tz.now.return_value = datetime(
            2016, 2, 20, 19, 0, tzinfo=timezone.utc
        )

        # notified 6 days ago, reminders already sent
        unconfirmed = mommy.make(
            Entry, status='selected', notified=True,
            notified_date=datetime(2016, 2, 14, 19, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='unconfirmed@test.com'
        )
        confirmed_unpaid = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=False,
            notified_date=datetime(2016, 2, 14, 19, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='confirmed_unpaid@test.com'
        )
        confirmed_paid = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=True,
            notified_date=datetime(2016, 2, 14, 19, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='confirmed_paid@test.com'
        )

        # notified 7 days 1 hr ago, reminders already sent
        unconfirmed1 = mommy.make(
            Entry, status='selected', notified=True,
            notified_date=datetime(2016, 2, 13, 18, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='unconfirmed1@test.com'
        )
        confirmed_unpaid1 = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=False,
            notified_date=datetime(2016, 2, 13, 18, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='confirmed_unpaid1@test.com'
        )
        confirmed_paid1 = mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=True,
            notified_date=datetime(2016, 2, 13, 18, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='confirmed_paid1@test.com',
        )

        management.call_command('warn_and_auto_withdraw_selected_entries')

        # Emails sent to the entries with notified date 7 days ago only; not
        # sent for the paid entry
        # Also sends 1 email to studio
        self.assertEqual(len(mail.outbox), 3)
        to_emails = [email.to[0] for email in mail.outbox]

        unconfirmed.refresh_from_db()
        confirmed_paid.refresh_from_db()
        confirmed_unpaid.refresh_from_db()
        unconfirmed1.refresh_from_db()
        confirmed_unpaid1.refresh_from_db()
        confirmed_paid1.refresh_from_db()

        # last email is the studio one
        self.assertEqual(mail.outbox[-1].to, [settings.DEFAULT_STUDIO_EMAIL])

        for entry in [unconfirmed1, confirmed_unpaid1]:
            self.assertIn(entry.user.email, to_emails)
            self.assertTrue(entry.withdrawn)

        for entry in [
            unconfirmed, confirmed_unpaid, confirmed_unpaid, confirmed_paid,
            confirmed_paid1
        ]:
            self.assertNotIn(entry.user.email, to_emails)
            self.assertFalse(entry.withdrawn)

    @patch(
        'entries.management.commands.warn_and_auto_withdraw_selected_entries.'
        'timezone')
    def test_no_selected_entries_to_warn_or_withdraw(self, mock_tz):
        """
        Selected unconfirmed and selected_confirmed unpaid get automatically
        withdrawn and users notified 7 days after notification date
        """
        mock_tz.now.return_value = datetime(
            2016, 2, 20, 19, 0, tzinfo=timezone.utc
        )

        # notified 6 days ago, reminders already sent
        mommy.make(
            Entry, status='selected', notified=True,
            notified_date=datetime(2016, 2, 14, 19, 0, tzinfo=timezone.utc),
            reminder_sent=True, user__email='unconfirmed@test.com'
        )
        # reminded > 7 days ago, paid, never reminded
        mommy.make(
            Entry, status='selected_confirmed', notified=True,
            selected_entry_paid=True,
            notified_date=datetime(2016, 2, 10, 18, 0, tzinfo=timezone.utc),
            reminder_sent=False, user__email='confirmed_paid1@test.com',
        )
        management.call_command('warn_and_auto_withdraw_selected_entries')

        # Nothing to send
        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(
            ActivityLog.objects.latest('id').log,
            'CRON: Auto warn/withdraw selected unconfirmed/unpaid '
            'run: no action required'
        )

    def test_setup_test_data(self):
        self.assertFalse(User.objects.exists())
        self.assertFalse(Entry.objects.exists())

        management.call_command('setup_test_data')

        self.assertEqual(User.objects.count(), 5)
        self.assertEqual(Entry.objects.count(), 9)

    def test_export_entries(self):
        management.call_command('setup_test_data')
        management.call_command('export_entries', 'BEG')

        self.assertEqual(
            Entry.objects.filter(
                category='BEG', status='submitted', withdrawn=False,
                video_entry_paid=True
            ).count(),
            1
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            mail.outbox[0].body, 'Submitted entry data attached. 1 entry.')

        management.call_command('export_entries', 'INT')
        self.assertEqual(
            Entry.objects.filter(
                category='INT', status='submitted', withdrawn=False,
                video_entry_paid=True
            ).count(),
            2
        )
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            mail.outbox[1].body, 'Submitted entry data attached. 2 entries.')

        # save file
        filepath = os.path.join(os.getcwd(), 'test.csv')
        management.call_command(
            'export_entries', 'INT', file=filepath
        )
        self.assertFalse(os.path.exists(filepath))

        management.call_command(
            'export_entries', 'INT', file=filepath, save=True
        )
        self.assertTrue(os.path.exists(filepath))
        # cleanup
        os.unlink(filepath)



