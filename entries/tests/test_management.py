import sys

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

        # All emails in progress; one email sent per entry
        self.assertEqual(len(mail.outbox), 5)

    def test_email_warnings_sent_for_correct_entries(self):

        in_progress = mommy.make(
            Entry, status='in_progress', user__email='test_in_progress@test.com'
        )
        submitted_unpaid = mommy.make(
            Entry, status='in_progress', video_entry_paid=False,
            user__email='test_unpaid@test.com'
        )
        submitted_paid = mommy.make(
            Entry, status='in_progress', video_entry_paid=True,
            user__email='test_paid@test.com'
        )
        management.call_command('email_warnings')

        # Emails sent one per in progress and submitted/unpaid
        self.assertEqual(len(mail.outbox), 2)

        to_emails = [email.to[0] for email in mail.outbox]
        self.assertIn(in_progress.user.email, to_emails)
        self.assertIn(submitted_unpaid.user.email, to_emails)
        self.assertNotIn(submitted_paid.user.email, to_emails)

        self.assertEqual(
            self.output.getvalue(),
            'Warning emails sent for in progress/unpaid submitted entries '
            'pre-closing date: {}\n'.format(
                ', '.join([str(in_progress.id), str(submitted_unpaid.id)])
                )
        )
