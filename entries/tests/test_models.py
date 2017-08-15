from datetime import datetime
from mock import patch
from model_mommy import mommy

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from .helpers import TestSetupMixin
from ..models import Entry


class EntryModelTests(TestSetupMixin, TestCase):

    def test_str(self):
        entry = mommy.make(Entry, user=self.user, category='INT')
        entry.entry_ref = 'ref'
        self.assertEqual(
            str(entry),
            'Test User - ref - Intermediate - {} - In Progress'.format(
                settings.CURRENT_ENTRY_YEAR
            )
        )

    def test_entry_ref_set_on_save(self):
        entry = mommy.make(Entry, user=self.user, category='INT')
        entry.save()
        self.assertIsNotNone(entry.entry_ref)
        self.assertEqual(len(entry.entry_ref), 22)

    @patch('entries.models.timezone')
    def test_submitted_date(self, mock_tz):
        mock_now = datetime(2016, 1, 3, tzinfo=timezone.utc)
        mock_tz.now.return_value = mock_now
        entry = mommy.make(Entry, user=self.user, category='INT')
        self.assertEqual(entry.status, 'in_progress')
        self.assertIsNone(entry.date_submitted)

        entry.status = 'submitted'
        entry.save()
        self.assertEqual(entry.date_submitted, mock_now)

