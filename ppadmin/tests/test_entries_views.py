from mock import patch
from model_mommy import mommy

from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from entries.models import Entry
from .helpers import TestSetupStaffLoginRequiredMixin


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

    def test_status_display(self):
        entry = mommy.make(
            Entry, status='submitted', category='BEG', withdrawn=True
        )
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'status_filter': 'withdrawn'})
        self.assertIn('Submitted (withdrawn)', resp.rendered_content)

        entry.status = 'submitted'
        entry.withdrawn = False
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn('Submitted (pending payment)', resp.rendered_content)

        entry.video_entry_paid = True
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn('Submitted', resp.rendered_content)
        self.assertNotIn('Submitted (pending payment)', resp.rendered_content)

        entry.status = 'selected'
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn('Selected - NOT CONFIRMED', resp.rendered_content)

        entry.status = 'selected_confirmed'
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn(
            'Selected - confirmed (pending payment &amp; info)', resp.rendered_content
        )

        entry.selected_entry_paid = True
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn(
            'Selected - confirmed (pending info)', resp.rendered_content
        )

        entry.selected_entry_paid = False
        entry.biography = "About"
        entry.song = 'song'
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn(
            'Selected - confirmed (pending payment)', resp.rendered_content
        )

        entry.selected_entry_paid = True
        entry.save()
        resp = self.client.get(self.url)
        self.assertIn('Selected - confirmed', resp.rendered_content)
        self.assertNotIn(
            'Selected - confirmed (pending info)', resp.rendered_content
        )
        self.assertNotIn(
            'Selected - confirmed (pending payment &amp; info)', resp.rendered_content
        )
        self.assertNotIn(
            'Selected - confirmed (pending payment)', resp.rendered_content
        )

        entry.status = "selected_confirmed"
        entry.withdrawn = True
        entry.withdrawal_fee_paid = False
        entry.save()
        resp = self.client.get(self.url, {'status_filter': 'withdrawn'})
        self.assertIn(
            'Selected - confirmed (withdrawn-unpaid)', resp.rendered_content
        )

        entry.withdrawal_fee_paid = True
        entry.save()
        resp = self.client.get(self.url, {'status_filter': 'withdrawn'})
        self.assertIn(
            'Selected - confirmed (withdrawn-paid)', resp.rendered_content
        )


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


class ToggleSelectionTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(ToggleSelectionTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, status='submitted')
        cls.url = reverse('ppadmin:toggle_selected', args=[cls.entry.id])

    def setUp(self):
        self.submitted_entry = mommy.make(Entry, status='submitted')
        self.selected_entry = mommy.make(Entry, status='selected')
        self.rejected_entry = mommy.make(Entry, status='rejected')
        self.selected_confirmed = mommy.make(Entry, status='selected_confirmed')

    def select_url(self, entry):
        return reverse('ppadmin:toggle_selected', args=[entry.id])

    def reject_url(self, entry):
        return reverse('ppadmin:toggle_rejected', args=[entry.id])

    def undecided_url(self, entry):
        return reverse('ppadmin:toggle_undecided', args=[entry.id])

    def test_toggle_selected(self):
        self.assertEqual(self.submitted_entry.status, 'submitted')
        self.assertEqual(self.rejected_entry.status, 'rejected')

        self.client.login(username=self.staff_user.username, password='test')

        self.client.post(self.select_url(self.submitted_entry))
        self.submitted_entry.refresh_from_db()
        self.assertEqual(self.submitted_entry.status, 'selected')

        self.client.post(self.select_url(self.rejected_entry))
        self.rejected_entry.refresh_from_db()
        self.assertEqual(self.rejected_entry.status, 'selected')

    def test_toggle_rejected(self):
        self.assertEqual(self.submitted_entry.status, 'submitted')
        self.assertEqual(self.selected_entry.status, 'selected')

        self.client.login(username=self.staff_user.username, password='test')

        self.client.post(self.reject_url(self.submitted_entry))
        self.submitted_entry.refresh_from_db()
        self.assertEqual(self.submitted_entry.status, 'rejected')

        self.client.post(self.reject_url(self.selected_entry))
        self.selected_entry.refresh_from_db()
        self.assertEqual(self.selected_entry.status, 'rejected')

    def test_toggle_undecided(self):
        self.assertEqual(self.selected_entry.status, 'selected')
        self.assertEqual(self.rejected_entry.status, 'rejected')

        self.client.login(username=self.staff_user.username, password='test')

        self.client.post(self.undecided_url(self.selected_entry))
        self.selected_entry.refresh_from_db()
        self.assertEqual(self.selected_entry.status, 'submitted')

        self.client.post(self.undecided_url(self.rejected_entry))
        self.rejected_entry.refresh_from_db()
        self.assertEqual(self.rejected_entry.status, 'submitted')

    def test_cannot_change_selected_confirmed(self):
        self.assertEqual(self.selected_confirmed.status, 'selected_confirmed')

        self.client.login(username=self.staff_user.username, password='test')

        self.client.post(self.undecided_url(self.selected_confirmed))
        self.selected_confirmed.refresh_from_db()
        self.assertEqual(self.selected_confirmed.status, 'selected_confirmed')

        self.client.post(self.select_url(self.selected_confirmed))
        self.selected_confirmed.refresh_from_db()
        self.assertEqual(self.selected_confirmed.status, 'selected_confirmed')

        self.client.post(self.reject_url(self.selected_confirmed))
        self.selected_confirmed.refresh_from_db()
        self.assertEqual(self.selected_confirmed.status, 'selected_confirmed')


class NotifiedSelectionResetTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(NotifiedSelectionResetTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, status='selected', notified=True)
        cls.url = reverse('ppadmin:notified_selection_reset', args=[cls.entry.id])

    def test_reset_notified_selection(self):
        self.assertEqual(self.entry.status, 'selected')
        self.assertTrue(self.entry.notified)
        self.assertIsNotNone(self.entry.notified_date)

        self.client.login(username=self.staff_user.username, password='test')
        self.client.post(self.url)

        self.entry.refresh_from_db()
        # status stays the same, notified and notified date are rest
        self.assertEqual(self.entry.status, 'selected')
        self.assertFalse(self.entry.notified)
        self.assertIsNone(self.entry.notified_date)


class NotifyUsersTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(NotifyUsersTests, cls).setUpTestData()
        cls.url = reverse('ppadmin:notify_users')

    def setUp(self):
        mommy.make(
            Entry, status='selected', user__email='selected@test.com')
        mommy.make(Entry, status='selected', notified=True)
        mommy.make(Entry, status='submitted')
        mommy.make(Entry, status='rejected', user__email='rejected@test.com')
        mommy.make(Entry, status='rejected', notified=True)

    def test_notify_selected_entries(self):
        self.client.login(username=self.staff_user.username, password='test')

        self.assertEqual(Entry.objects.filter(notified=True).count(), 2)
        self.client.post(reverse('ppadmin:notify_selected_users'))

        self.assertEqual(Entry.objects.filter(notified=True).count(), 3)
        # 1 email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['selected@test.com'])
        self.assertIn('Congratulations!', mail.outbox[0].body)
        self.assertNotIn('you have not been successful', mail.outbox[0].body)

    def test_notify_rejected_entries(self):
        self.client.login(username=self.staff_user.username, password='test')

        self.assertEqual(Entry.objects.filter(notified=True).count(), 2)
        self.client.post(reverse('ppadmin:notify_rejected_users'))

        self.assertEqual(Entry.objects.filter(notified=True).count(), 3)
        # 1 email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['rejected@test.com'])
        self.assertNotIn('Congratulations!', mail.outbox[0].body)
        self.assertIn('you have not been successful', mail.outbox[0].body)

    def test_notify_all_entries(self):
        self.client.login(username=self.staff_user.username, password='test')

        self.assertEqual(Entry.objects.filter(notified=True).count(), 2)
        self.client.post(self.url)

        self.assertEqual(Entry.objects.filter(notified=True).count(), 4)
        # 2 email sent - 1 selected, 1 rejected
        self.assertEqual(len(mail.outbox), 2)
        rejected_mail = [
            email for email in mail.outbox if email.to == ['rejected@test.com']
            ]
        selected_mail = [
            email for email in mail.outbox if email.to == ['selected@test.com']
            ]
        self.assertEqual(len(rejected_mail), 1)
        self.assertEqual(len(selected_mail), 1)
        self.assertNotIn('Congratulations!', rejected_mail[0].body)
        self.assertIn('Congratulations!', selected_mail[0].body)
        self.assertIn('you have not been successful', rejected_mail[0].body)
        self.assertNotIn('you have not been successful', selected_mail[0].body)

    @patch('entries.email_helpers.EmailMultiAlternatives.send')
    def test_problem_sending_emails(self, mock_send):
        mock_send.side_effect = Exception('Error sending email')

        self.client.login(username=self.staff_user.username, password='test')

        self.assertEqual(Entry.objects.filter(notified=True).count(), 2)
        resp = self.client.post(self.url, follow=True)

        # notified has not changed
        self.assertEqual(Entry.objects.filter(notified=True).count(), 2)
        # No emails sent
        self.assertEqual(len(mail.outbox), 0)

        self.assertIn(
            'There was some problem sending semi-final results notification '
            'emails to the following users:',
            resp.rendered_content
        )

