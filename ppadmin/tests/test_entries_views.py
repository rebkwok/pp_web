from datetime import datetime
from model_mommy import mommy

from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.test import TestCase
from django.utils import timezone

from accounts.models import OnlineDisclaimer
from entries.models import Entry
from activitylog.models import ActivityLog
from .helpers import format_content, TestSetupStaffLoginRequiredMixin


class EntryListViewTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryListViewTests, cls).setUpTestData()
        cls.url = reverse('ppadmin:entries')

    def test_default_entries_displayed(self):
        """
        Default view shows current year only; excludes in progress and withdrawn
        """
        old_entry = mommy.make(Entry, entry_year=2014, status='submitted')
        in_progress = mommy.make(Entry, status='in_progress')
        withdrawn = mommy.make(Entry, status='submitted', withdrawn=True)
        mommy.make(Entry, status='submitted')
        mommy.make(Entry, status='selected')
        mommy.make(Entry, status='selected_confirmed')
        mommy.make(Entry, status='rejected')

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.context_data['entries'].count(), 4)
        for entry in [old_entry, in_progress, withdrawn]:
            self.assertNotIn(entry, resp.context_data['entries'])

    def test_abbreviations_for_long_url(self):
        """
        URLs have http:// stripped and > 20 characters are abbreviated
        """
        entry = mommy.make(
            Entry, status='submitted', video_url='http://foo.com'
        )
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertIn('>foo.com<', resp.rendered_content)
        self.assertNotIn('>http://foo.com<', resp.rendered_content)

        entry.video_url = 'http://foo1234567890123.com'
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn('>foo1234567890123.com<', resp.rendered_content)
        self.assertNotIn('>http://foo1234567890123.com<', resp.rendered_content)

        entry.video_url = 'http://foo1234567890123456789.com'
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn('>foo12345678901234...<', resp.rendered_content)

    def test_category_filter(self):
        """
        Default view shows current year only; excludes in progress and withdrawn
        With category filter, also exclude old, in_progress and withdrawn;
        return the selected category
        """
        old_entry = mommy.make(
            Entry, entry_year=2014, status='submitted', category='BEG'
        )
        in_progress = mommy.make(
            Entry, status='in_progress', category='BEG'
        )
        withdrawn = mommy.make(
            Entry, status='submitted', withdrawn=True, category='INT'
        )
        beg1 = mommy.make(Entry, status='submitted', category='BEG')
        int1 = mommy.make(Entry, status='selected', category='INT')
        beg2 = mommy.make(Entry, status='rejected', category='BEG')
        int2 = mommy.make(Entry, status='selected_confirmed', category='INT')

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'cat_filter': 'BEG'})
        self.assertEqual(resp.context_data['entries'].count(), 2)

        for entry in [old_entry, in_progress, withdrawn, int1, int2]:
            self.assertNotIn(entry, resp.context_data['entries'])

        for entry in [beg1, beg2]:
            self.assertIn(entry, resp.context_data['entries'])


    def test_status_filter(self):
        """
        Default view shows current year only; excludes in progress and withdrawn
        With category filter, also exclude old, in_progress and withdrawn;
        return the selected category
        """
        old_entry = mommy.make(
            Entry, entry_year=2014, status='submitted', category='BEG'
        )
        in_progress = mommy.make(
            Entry, status='in_progress', category='BEG'
        )
        withdrawn = mommy.make(
            Entry, status='submitted', withdrawn=True, category='INT'
        )
        submitted = mommy.make(Entry, status='submitted', category='BEG')
        selected = mommy.make(Entry, status='selected', category='INT')
        rejected = mommy.make(Entry, status='rejected', category='BEG')
        selected_confirmed = mommy.make(
            Entry, status='selected_confirmed', category='INT'
        )

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'status_filter': 'all'})

        # returns all except old
        self.assertEqual(resp.context_data['entries'].count(), 6)
        self.assertNotIn(old_entry, resp.context_data['entries'])

        resp = self.client.get(self.url, {'status_filter': 'selected'})
        self.assertEqual(resp.context_data['entries'].count(), 1)
        self.assertIn(selected, resp.context_data['entries'])

        resp = self.client.get(self.url, {'status_filter': 'withdrawn'})
        self.assertEqual(resp.context_data['entries'].count(), 1)
        self.assertIn(withdrawn, resp.context_data['entries'])

    def test_category_and_status_filters(self):
        old_entry = mommy.make(
            Entry, entry_year=2014, status='submitted', category='BEG'
        )
        in_progress = mommy.make(
            Entry, status='in_progress', category='BEG'
        )
        withdrawn = mommy.make(
            Entry, status='submitted', withdrawn=True, category='INT'
        )
        submitted = mommy.make(Entry, status='submitted', category='BEG')
        selected = mommy.make(Entry, status='selected', category='INT')
        rejected = mommy.make(Entry, status='rejected', category='BEG')
        selected_confirmed = mommy.make(
            Entry, status='selected_confirmed', category='INT'
        )

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(
            self.url, {'status_filter': 'all', 'cat_filter': 'BEG'}
        )
        self.assertEqual(resp.context_data['entries'].count(), 3)
        for entry in [in_progress, submitted, rejected]:
            self.assertIn(entry, resp.context_data['entries'])
        # old_entry still not shown, even though matches category and status
        # is all
        for entry in [old_entry, withdrawn, selected, selected_confirmed]:
            self.assertNotIn(entry, resp.context_data['entries'])

    def test_user_filter(self):
        """
        User id can be passed from the UserList as query param.  Shows all
        user's entries except old ones
        """
        user = mommy.make(User)
        old_entry = mommy.make(
            Entry, entry_year=2014, user=user, status='submitted',
            category='BEG'
        )
        in_progress = mommy.make(
            Entry, status='in_progress', user=user, category='BEG'
        )
        withdrawn = mommy.make(
            Entry, status='submitted', withdrawn=True, category='INT', user=user
        )
        submitted = mommy.make(
            Entry, status='submitted', category='PRO', user=user
        )
        # 4 entries total
        self.assertEqual(Entry.objects.count(), 4)
        self.client.login(username=self.staff_user.username, password='test')

        resp = self.client.get(self.url + "?user={}".format(user.id))
        self.assertEqual(resp.context_data['entries'].count(), 3)
        for entry in [in_progress, withdrawn, submitted]:
            self.assertIn(entry, resp.context_data['entries'])
        # old_entry still not shown, even though matches category and status
        # is all
        self.assertNotIn(old_entry, resp.context_data['entries'])

    def test_reset(self):
        """
        Reset sets filters back to default - exclude in progress, withdrawn
        and old
        """
        old_entry = mommy.make(
            Entry, entry_year=2014, status='submitted', category='BEG'
        )
        in_progress = mommy.make(
            Entry, status='in_progress', category='BEG'
        )
        withdrawn = mommy.make(
            Entry, status='submitted', withdrawn=True, category='INT'
        )
        submitted = mommy.make(Entry, status='submitted', category='BEG')
        selected = mommy.make(Entry, status='selected', category='INT')
        rejected = mommy.make(Entry, status='rejected', category='BEG')
        selected_confirmed = mommy.make(
            Entry, status='selected_confirmed', category='INT'
        )

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(
            self.url,
            {
                'status_filter': 'in_progress', 'cat_filter': 'BEG',
                'reset': 'Reset'
            }
        )
        self.assertEqual(resp.context_data['entries'].count(), 4)
        for entry in [submitted, selected, rejected, selected_confirmed]:
            self.assertIn(entry, resp.context_data['entries'])
        for entry in [old_entry, in_progress, withdrawn]:
            self.assertNotIn(entry, resp.context_data['entries'])


class EntryDetailViewTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryDetailViewTests, cls).setUpTestData()
        entry = mommy.make(Entry)
        cls.url = reverse('ppadmin:entry', args=[entry.entry_ref])


class EntrySelectionListViewTests(TestSetupStaffLoginRequiredMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super(EntrySelectionListViewTests, cls).setUpTestData()
        cls.url = reverse('ppadmin:entries_selection')


    def test_in_progress_and_withdrawn_excluded(self):
        """
        Default view shows current year only; excludes in progress and withdrawn
        """
        old_entry = mommy.make(Entry, entry_year=2014, status='submitted')
        in_progress = mommy.make(Entry, status='in_progress')
        withdrawn = mommy.make(Entry, status='submitted', withdrawn=True)
        mommy.make(Entry, status='submitted')
        mommy.make(Entry, status='selected')
        mommy.make(Entry, status='selected_confirmed')
        mommy.make(Entry, status='rejected')

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.context_data['entries'].count(), 4)
        for entry in [old_entry, in_progress, withdrawn]:
            self.assertNotIn(entry, resp.context_data['entries'])

    def test_category_filter(self):
        """
        Default view shows current year only; excludes in progress and withdrawn
        With category filter, also exclude old, in_progress and withdrawn;
        return the selected category
        """
        old_entry = mommy.make(
            Entry, entry_year=2014, status='submitted', category='BEG'
        )
        in_progress = mommy.make(
            Entry, status='in_progress', category='BEG'
        )
        withdrawn = mommy.make(
            Entry, status='submitted', withdrawn=True, category='INT'
        )
        beg1 = mommy.make(Entry, status='submitted', category='BEG')
        int1 = mommy.make(Entry, status='selected', category='INT')
        beg2 = mommy.make(Entry, status='rejected', category='BEG')
        int2 = mommy.make(Entry, status='selected_confirmed', category='INT')

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'cat_filter': 'BEG'})
        self.assertEqual(resp.context_data['entries'].count(), 2)

        for entry in [old_entry, in_progress, withdrawn, int1, int2]:
            self.assertNotIn(entry, resp.context_data['entries'])

        for entry in [beg1, beg2]:
            self.assertIn(entry, resp.context_data['entries'])

    def test_hide_rejected(self):
        old_entry = mommy.make(Entry, entry_year=2014, status='submitted')
        in_progress = mommy.make(Entry, status='in_progress')
        withdrawn = mommy.make(Entry, status='submitted', withdrawn=True)
        mommy.make(Entry, status='submitted')
        mommy.make(Entry, status='selected')
        mommy.make(Entry, status='selected_confirmed')
        rejected = mommy.make(Entry, status='rejected')

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'hide_rejected': 'Hide rejected'})
        self.assertEqual(resp.context_data['entries'].count(), 3)
        for entry in [old_entry, in_progress, withdrawn, rejected]:
            self.assertNotIn(entry, resp.context_data['entries'])

    def test_doubles_filter_shows_extra_doubles_fields(self):
        mommy.make(Entry, status='submitted', category='BEG')
        mommy.make(Entry, status='selected', category='DOU')
        mommy.make(Entry, status='selected_confirmed', category='BEG')
        mommy.make(Entry, status='rejected', category='DOU')

        self.assertEqual(Entry.objects.count(), 4)

        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'cat_filter': 'DOU'})
        self.assertEqual(resp.context_data['entries'].count(), 2)
        self.assertTrue(resp.context_data['doubles'])
        self.assertIn('Doubles</br>partner', resp.rendered_content)

        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'cat_filter': 'BEG'})
        self.assertEqual(resp.context_data['entries'].count(), 2)
        self.assertFalse(resp.context_data['doubles'])
        self.assertNotIn('Doubles</br>partner', resp.rendered_content)


class EntryNotifiedListViewTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryNotifiedListViewTests, cls).setUpTestData()
        cls.url = reverse('ppadmin:entries_notified')

    def test_in_progress_and_withdrawn_excluded_and_notified_shown(self):
        """
        Default view shows current year only; excludes in progress and withdrawn
        """
        old_entry = mommy.make(Entry, entry_year=2014, status='submitted')
        in_progress = mommy.make(Entry, status='in_progress')
        withdrawn = mommy.make(Entry, status='submitted', withdrawn=True)
        mommy.make(Entry, status='submitted')
        notified = mommy.make(Entry, status='selected', notified=True)
        mommy.make(Entry, status='selected_confirmed')
        mommy.make(Entry, status='rejected')

        # 7 entries total
        self.assertEqual(Entry.objects.count(), 7)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.context_data['entries'].count(), 1)
        self.assertIn(notified, resp.context_data['entries'])