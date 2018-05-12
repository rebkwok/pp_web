import os

from model_mommy import mommy

from django.conf import settings
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.http import Http404

from accounts.models import OnlineDisclaimer
from accounts.utils import has_active_data_privacy_agreement

from .helpers import format_content, TestSetupMixin, TestSetupLoginRequiredMixin
from ..models import Entry, STATUS_CHOICES_DICT
from ..views import pdf_view

from payments.models import PaypalEntryTransaction


class EntryHomeTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryHomeTests, cls).setUpTestData()
        cls.url = reverse('entries:entries_home')

    def test_can_get_without_login(self):
        resp = self.client.get(self.url)
        self. assertEqual(resp.status_code, 200)

    @override_settings(
        ENTRIES_OPEN_DATE="01/01/2016",
        ENTRIES_CLOSE_DATE="01/01/2200",
        LATE_CATEGORIES_ENTRIES_CLOSE_DATE="01/02/2200"
    )
    def test_entries_open(self):
        resp = self.client.get(self.url)
        self.assertIn('ENTER NOW', str(resp.content))

    @override_settings(
        ENTRIES_OPEN_DATE="01/01/2010",
        LATE_CATEGORIES_ENTRIES_CLOSE_DATE="01/01/2016"
    )
    def test_entries_closed(self):
        resp = self.client.get(self.url)
        self.assertNotIn('ENTER NOW', str(resp.content))


class EntryListViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryListViewTests, cls).setUpTestData()
        cls.url = reverse('entries:user_entries')

    def test_shows_all_users_entries(self):
        mommy.make(Entry, user=self.user, category='BEG')
        mommy.make(Entry, user=self.user, category='INT')
        mommy.make(Entry, category='BEG')
        mommy.make(Entry, category='INT')
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.context_data['entries']), 2)

    def test_entry_in_progress(self):
        # shows correct status, no paypal buttons, edit and delete button
        entry = mommy.make(Entry, user=self.user)
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        entries = resp.context_data['entries']
        self.assertEqual(len(resp.context_data['entries']), 1)
        entry_ctx = entries[0]
        self.assertEqual(entry_ctx['instance'], entry)
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])
        self.assertTrue(entry_ctx['can_delete'])
        self.assertIn('>Edit details</a>', resp.rendered_content)
        self.assertNotIn('>Withdraw</a>', resp.rendered_content)

    def test_entry_submitted(self):
        # shows correct status, paypal button for video, edit and withdraw btns
        entry = mommy.make(Entry, user=self.user, status='submitted')
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        entries = resp.context_data['entries']
        self.assertEqual(len(resp.context_data['entries']), 1)
        entry_ctx = entries[0]
        self.assertEqual(entry_ctx['instance'], entry)
        self.assertIsNotNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])
        self.assertFalse(entry_ctx['can_delete'])
        self.assertIn('>Edit details</a>', resp.rendered_content)
        self.assertIn('>Withdraw</a>', resp.rendered_content)
        # status shows payment pending
        self.assertIn('Submitted (pending payment)', resp.rendered_content)

        # No paypal form if video entry paid
        entry.video_entry_paid = True
        entry.save()
        resp = self.client.get(self.url)
        entry_ctx = resp.context_data['entries'][0]
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])
        self.assertIn('Submitted', resp.rendered_content)
        self.assertNotIn('Submitted (pending payment)', resp.rendered_content)

    def test_entry_selected(self):
        # shows correct status, no paypal button for payments,
        # edit and withdraw btns
        entry = mommy.make(Entry, user=self.user, status='selected')
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        entries = resp.context_data['entries']
        self.assertEqual(len(resp.context_data['entries']), 1)
        entry_ctx = entries[0]
        self.assertEqual(entry_ctx['instance'], entry)
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])
        self.assertFalse(entry_ctx['can_delete'])
        self.assertIn('>Edit details</a>', resp.rendered_content)
        self.assertIn('>Withdraw</a>', resp.rendered_content)

        # status shows not confirmed
        self.assertIn('Selected - NOT CONFIRMED', resp.rendered_content)

    def test_entry_selected_confirmed(self):
        # shows correct status, paypal button for selected payments,
        # edit and withdraw btns
        entry = mommy.make(Entry, user=self.user, status='selected_confirmed')
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        entries = resp.context_data['entries']
        self.assertEqual(len(resp.context_data['entries']), 1)
        entry_ctx = entries[0]
        self.assertEqual(entry_ctx['instance'], entry)
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNotNone(entry_ctx['paypal_selected_form'])
        self.assertFalse(entry_ctx['can_delete'])
        self.assertIn('>Edit details</a>', resp.rendered_content)
        self.assertIn('>Withdraw</a>', resp.rendered_content)

        # status shows payment pending
        self.assertIn(
            'Selected - confirmed (pending payment)', resp.rendered_content
        )

        # No paypal form if selected entry paid
        entry.selected_entry_paid = True
        entry.save()
        resp = self.client.get(self.url)
        entry_ctx = resp.context_data['entries'][0]
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])
        self.assertIn('Selected', resp.rendered_content)
        self.assertNotIn(
            'Selected - confirmed (pending payment)', resp.rendered_content
        )

    def test_entry_rejected(self):
        # shows correct status, paypal button for entry, edit and withdraw btns
        entry = mommy.make(Entry, user=self.user, status='rejected')
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        entries = resp.context_data['entries']
        self.assertEqual(len(resp.context_data['entries']), 1)
        entry_ctx = entries[0]
        self.assertEqual(entry_ctx['instance'], entry)
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])
        self.assertFalse(entry_ctx['can_delete'])
        self.assertIn('>Edit details</a>', resp.rendered_content)
        self.assertIn('>Withdraw</a>', resp.rendered_content)

    def test_entry_withdrawn(self):
        # shows withdrawn as status, no paypal buttons,
        # no edit/delete/withdraw btns
        entry = mommy.make(
            Entry, user=self.user, status='submitted', withdrawn=True
        )
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        entry_ctx = resp.context_data['entries'][0]
        self.assertEqual(entry_ctx['instance'], entry)
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])
        self.assertFalse(entry_ctx['can_delete'])
        self.assertNotIn('>Edit details</a>', resp.rendered_content)
        self.assertNotIn('>Withdraw</a>', resp.rendered_content)
        self.assertIn(
            'Contact organizers if you wish to reopen this entry',
            resp.rendered_content
        )


@override_settings(
        ENTRIES_OPEN_DATE="01/01/2016",
        ENTRIES_CLOSE_DATE="01/01/2200",
        LATE_CATEGORIES_ENTRIES_CLOSE_DATE="01/01/2200"
    )
class EntryCreateViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryCreateViewTests, cls).setUpTestData()
        cls.url = reverse('entries:create_entry')

    def setUp(self):
        self.post_data = {
            'category': 'BEG',
            'saved': 'Save'
        }

    def test_cant_access_outside_entries_open_period(self):
        self.client.login(username=self.user.username, password='test')
        with override_settings(
                LATE_CATEGORIES_ENTRIES_CLOSE_DATE="01/01/2016",
                ENTRIES_CLOSE_DATE="01/01/2016"
        ):
            resp = self.client.get(self.url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse('permission_denied'), resp.url)

    def test_cant_access_without_signed_data_privacy(self):
        user = User.objects.create_user(
            username='test1', email='test1@test.com', password='test'
        )
        self.assertFalse(has_active_data_privacy_agreement(user))
        self.client.login(username=user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:data_privacy_review'), resp.url)

    def test_create_entry_and_save(self):
        self.assertFalse(Entry.objects.exists())
        self.client.login(username=self.user.username, password='test')
        self.client.post(self.url, self.post_data)
        self.assertEqual(Entry.objects.count(), 1)
        self.assertEqual(Entry.objects.first().user, self.user)

    def test_create_entry_and_submit(self):
        """
        Submit requires all fields are entered except stage name and song
        """
        self.assertFalse(Entry.objects.exists())
        self.client.login(username=self.user.username, password='test')
        data = self.post_data.copy()
        del data['saved']
        data.update({'submitted': 'Submit'})
        resp = self.client.post(self.url, data)

        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'video_url': ['This field is required'],
            }
        )
        self.assertEqual(Entry.objects.count(), 0)

        data.update({
            'video_url': 'http://foo.com',
        })
        self.client.post(self.url, data)
        self.assertEqual(Entry.objects.count(), 1)

        # status has been changed from in_progress to submitted
        self.assertEqual(Entry.objects.first().status, 'submitted')

    def test_save_redirects_to_entries_list(self):
        self.assertFalse(Entry.objects.exists())
        self.client.login(username=self.user.username, password='test')

        resp = self.client.post(self.url, self.post_data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Entry.objects.count(), 1)
        self.assertEqual( resp.url, reverse('entries:user_entries'))
        # no emails on save
        self.assertEqual(len(mail.outbox), 0)

    def test_first_submission_redirects_to_payment_view_and_emails_user(self):
        self.assertFalse(Entry.objects.exists())
        self.client.login(username=self.user.username, password='test')
        data = self.post_data.copy()
        del data['saved']
        data.update({
            'submitted': 'Submit',
            'video_url': 'http://foo.com',
        })
        resp = self.client.post(self.url, data)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Entry.objects.count(), 1)
        entry = Entry.objects.first()
        self.assertEqual(
            resp.url, reverse('entries:video_payment', args=[entry.entry_ref])
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [entry.user.email])
        self.assertEqual(
            mail.outbox[0].subject,
            '{} Entry submitted'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX)
        )

    def test_change_category(self):
        """
        Changing the category resubmits the form without 'saved' or
        'submitted' in the POST and redirect back to the new entry form view
        with the initial data set
        """
        self.assertFalse(Entry.objects.exists())
        self.client.login(username=self.user.username, password='test')
        data = {'category': 'INT', 'video_url': 'http://foo.com'}

        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('entries:create_entry'))

        resp = self.client.post(self.url, data, follow=True)
        self.assertEqual(
            resp.context_data['form'].initial,
            {'category': 'INT', 'video_url': 'http://foo.com'}
        )
        self.assertFalse(Entry.objects.exists())

    def test_initial_set_from_session_data(self):
        """
        If category is changed on a new entry form, the form data is stored
        on the session and added to the form's initial data on the redirected
        get
        """
        self.assertFalse(Entry.objects.exists())
        self.client.login(username=self.user.username, password='test')
        session = self.client.session
        session['form_data'] = {
            'category': 'ADV', 'video_url': 'http://foo.com'
        }
        session.save()

        self.assertIsNotNone(self.client.session.get('form_data'))

        resp = self.client.get(self.url)
        self.assertEqual(
            resp.context_data['form'].initial,
            {'category': 'ADV', 'video_url': 'http://foo.com'}
        )

        # form data has been removed from session
        self.assertIsNone(self.client.session.get('form_data'))


class EntryUpdateViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryUpdateViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user)
        cls.url = reverse('entries:edit_entry', args=(cls.entry.entry_ref,))

    def setUp(self):
        self.post_data = {
            'category': 'BEG',
            'saved': 'Save'
        }

    def test_upate_entry_and_save(self):
        self.client.login(username=self.user.username, password='test')
        data = self.post_data.copy()
        data.update({'category': 'INT'})
        self.client.post(self.url, data)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.category, 'INT')

    def test_update_entry_and_submit(self):
        """
        Submit requires all fields are entered except stage name and song
        """
        self.client.login(username=self.user.username, password='test')
        data = self.post_data.copy()
        del data['saved']
        data.update({'submitted': 'Submit'})
        resp = self.client.post(self.url, data)

        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'video_url': ['This field is required'],
            }
        )

        data.update({
            'video_url': 'http://foo.com',
        })
        self.client.post(self.url, data)
        self.entry.refresh_from_db()
        # status has been changed from in_progress to submitted
        self.assertEqual(self.entry.status, 'submitted')

    def test_change_category(self):
        """
        Changing the category resubmits the form without 'saved' or
        'submitted' in the POST, saves the entry and redirects back to the
        edit entry form view
        """
        self.client.login(username=self.user.username, password='test')
        data = {'category': 'INT', 'video_url': 'http://foo.com'}

        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.url)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.category, 'INT')
        self.assertEqual(self.entry.status, 'in_progress')
        self.assertEqual(self.entry.video_url, 'http://foo.com')

    def test_first_submission_redirects_to_payment_and_emails_user(self):
        entry = mommy.make(
            Entry, user=self.user, category='ADV', status='in_progress'
        )
        url = reverse('entries:edit_entry', args=(entry.entry_ref,))
        self.client.login(username=self.user.username, password='test')

        # update and save
        data = {'stage_name': 'Me', 'category': 'ADV', 'saved': 'Save'}
        self.client.post(url, data)
        self.assertEqual(len(mail.outbox), 0)

        # submit
        del data['saved']
        data.update({'video_url': 'http://foo.com', 'submitted': 'Submit'})

        self.client.post(url, data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [entry.user.email])
        self.assertEqual(
            mail.outbox[0].subject,
            '{} Entry submitted'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX)
        )

        # update and submit again; no further email sent
        data.update({'stage_name': 'My new name'})
        self.client.post(url, data)
        self.assertEqual(len(mail.outbox), 1)


class SelectedEntryUpdateViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(SelectedEntryUpdateViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user, status='selected')
        cls.url = reverse(
            'entries:edit_selected_entry', args=(cls.entry.entry_ref,)
        )

    def setUp(self):
        self.post_data = {
            'submitted': 'Submit',
            'song': 'Song title',
            'biography': 'About me'
        }

    def test_redirect_if_not_selected(self):
        entry = mommy.make(
            Entry, user=self.user, category='INT', status='submitted'
        )
        url = reverse(
            'entries:edit_selected_entry', args=(entry.entry_ref,)
        )
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('permission_denied'), resp.url)

        entry.status = 'selected'
        entry.save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        entry.status = 'selected_confirmed'
        entry.save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        entry.withdrawn = True
        entry.save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('permission_denied'), resp.url)

        entry.withdrawn = False
        entry.status = 'rejected'
        entry.save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('permission_denied'), resp.url)

    def test_update_entry_and_save(self):
        self.client.login(username=self.user.username, password='test')
        data = self.post_data.copy()
        data.update({'biography': 'About me'})
        resp = self.client.post(self.url, data, follow=True)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.biography, 'About me')


class EntryDeleteViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryDeleteViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user)
        cls.url = reverse('entries:delete_entry', args=(cls.entry.entry_ref,))

    def test_redirect_if_not_in_progress(self):
        """
        Entry can only be deleted if status is "in_progress"
        """
        entry = mommy.make(
            Entry, user=self.user, category='INT', status='submitted'
        )
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(
            reverse('entries:delete_entry', args=(entry.entry_ref,))
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('permission_denied'), resp.url)

    def test_get_context(self):
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.context_data['action'], 'delete')

    def test_delete(self):
        self.assertEqual(Entry.objects.count(), 1)
        self.client.login(username=self.user.username, password='test')
        self.client.delete(self.url)
        self.assertEqual(Entry.objects.count(), 0)

    def test_post(self):
        """
        Also deletes
        """
        self.assertEqual(Entry.objects.count(), 1)
        self.client.login(username=self.user.username, password='test')
        self.client.delete(self.url)
        self.assertEqual(Entry.objects.count(), 0)


class EntryWithdrawViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryWithdrawViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user, status='submitted')
        cls.url = reverse(
            'entries:withdraw_entry', args=(cls.entry.entry_ref,)
        )

    def test_redirect_if_already_withdrawn(self):
        entry = mommy.make(
            Entry, user=self.user, category='INT', status='submitted',
            withdrawn=True
        )
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(
            reverse('entries:withdraw_entry', args=(entry.entry_ref,))
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('permission_denied'), resp.url)

    def test_get_context(self):
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.context_data['action'], 'withdraw')

    def test_withdraw(self):
        self.client.login(username=self.user.username, password='test')
        self.assertEqual(self.entry.status, 'submitted')
        self.assertFalse(self.entry.withdrawn)

        resp = self.client.post(self.url, {'id': self.entry.id})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("entries:user_entries"), resp.url)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, 'submitted')
        self.assertTrue(self.entry.withdrawn)

    def test_redirects_to_payment_if_selected_confirmed(self):
        self.client.login(username=self.user.username, password='test')
        entry = mommy.make(
            Entry, user=self.user, category='ADV', status='selected_confirmed',
        )
        self.assertEqual(entry.status, 'selected_confirmed')
        self.assertFalse(entry.withdrawn)
        resp = self.client.post(
            reverse('entries:withdraw_entry', args=(entry.entry_ref,)),
            {'id': entry.id}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            reverse("entries:withdrawal_payment", args=(entry.entry_ref,)),
            resp.url
        )

        entry.refresh_from_db()
        self.assertEqual(entry.status, 'selected_confirmed')
        self.assertTrue(entry.withdrawn)

    def test_emails(self):
        """
        Email sent to PP if status is selected or selected_confirmed; email to
        PP only if selected
        """
        self.client.login(username=self.user.username, password='test')
        entry = mommy.make(
            Entry, user=self.user, category='ADV', status='submitted',
        )
        self.client.post(
            reverse('entries:withdraw_entry', args=(entry.entry_ref,)),
            {'id': entry.id}
        )
        entry.refresh_from_db()
        self.assertTrue(entry.withdrawn)
        self.assertEqual(len(mail.outbox), 0)

        entry.withdrawn = False
        entry.status = 'selected'
        entry.save()

        self.client.post(
            reverse('entries:withdraw_entry', args=(entry.entry_ref,)),
            {'id': entry.id}
        )
        entry.refresh_from_db()
        self.assertTrue(entry.withdrawn)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.DEFAULT_STUDIO_EMAIL])
        self.assertEqual(
            mail.outbox[0].subject,
            '{} Entry withdrawn'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX)
        )

        entry.withdrawn = False
        entry.status = 'selected_confirmed'
        entry.save()

        self.client.post(
            reverse('entries:withdraw_entry', args=(entry.entry_ref,)),
            {'id': entry.id}
        )
        entry.refresh_from_db()
        self.assertTrue(entry.withdrawn)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[1].to, [entry.user.email])
        self.assertEqual(mail.outbox[2].to, [settings.DEFAULT_STUDIO_EMAIL])
        self.assertEqual(
            mail.outbox[1].subject,
            '{} Entry withdrawn'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX)
        )
        self.assertEqual(
            mail.outbox[2].subject,
            '{} Entry withdrawn'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX)
        )


class VideoPaymentViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(VideoPaymentViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user, status='submitted')
        cls.url = reverse(
            'entries:video_payment', args=(cls.entry.entry_ref,)
        )

    def setUp(self):
        self.entry1 =  mommy.make(
            Entry, user=self.user, category='INT', status='in_progress'
        )
        self.url1 = reverse(
            'entries:video_payment', args=(self.entry1.entry_ref,)
        )

    def login(self):
        self.client.login(username=self.user.username, password='test')

    def test_entry_not_yet_submitted(self):
        self.login()
        resp = self.client.get(self.url1)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('paypalform', resp.context_data)
        self.assertIn(
            'This entry is still in progress. Please submit it before paying '
            'the fee.',
            resp.rendered_content
        )

    def test_entry_withdrawn(self):
        self.entry.withdrawn = True
        self.entry.save()

        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('paypalform', resp.context_data)
        self.assertIn(
            'This entry has been withdrawn.',
            resp.rendered_content
        )

    def test_entry_already_paid(self):
        self.entry1.video_entry_paid = True
        self.entry1.save()

        self.login()
        resp = self.client.get(self.url1)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('paypalform', resp.context_data)
        self.assertIn(
            'The fee for this entry has already been paid.',
            resp.rendered_content
        )

    def test_renders_correct_paypal_dict_info(self):
        self.login()
        self.assertFalse(PaypalEntryTransaction.objects.exists())
        resp = self.client.get(self.url)

        # PaypalEntryTransaction is created by the view
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)
        pptrans = PaypalEntryTransaction.objects.first()
        first_invoice_id = pptrans.invoice_id

        self.assertIn('paypalform', resp.context_data)
        paypalform_data = resp.context_data['paypalform'].initial


        self.assertEqual(paypalform_data['invoice'], pptrans.invoice_id)
        self.assertEqual(
            paypalform_data['custom'], 'video {}'.format(self.entry.id)
        )
        self.assertEqual(
            paypalform_data['item_name'],
            'Video submission fee for Beginner category'
        )

        # getting the view again doesn't create a new pptrans or update inv id
        resp = self.client.get(self.url)
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)
        pptrans1 = PaypalEntryTransaction.objects.first()
        self.assertEqual(pptrans.id, pptrans1.id)
        self.assertEqual(first_invoice_id, pptrans1.invoice_id)


class DoublePartnerCheckTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(DoublePartnerCheckTests, cls).setUpTestData()
        cls.user_with_disclaimer = mommy.make(User, email='testA@test.com')
        mommy.make(OnlineDisclaimer, user=cls.user_with_disclaimer)

        cls.user_already_doubles = mommy.make(
            User, email='testB@test.com'
        )
        mommy.make(OnlineDisclaimer, user=cls.user_already_doubles)
        mommy.make(Entry, user=cls.user_already_doubles, category='DOU')

        cls.user_already_other = mommy.make(
            User, email='testC@test.com'
        )
        mommy.make(OnlineDisclaimer, user=cls.user_already_other)
        mommy.make(Entry, user=cls.user_already_other, category='BEG')

    def setUp(self):
        self.client.login(username=self.user.username, password='test')

    def get_url(self, email):
        return reverse('entries:check_partner') + '?email=' + email

    def test_partner_exists_and_has_disclaimer(self):
        resp = self.client.post(self.get_url(self.user_with_disclaimer.email))
        self.assertIn(
            'Doubles partner registered: Yes',
            format_content(str(resp.content)),
        )
        self.assertIn(
            'Waiver completed: Yes',
            format_content(str(resp.content)),
        )

    def test_partner_exists_no_disclaimer(self):
        resp = self.client.get(self.get_url(self.user_no_disclaimer.email))
        self.assertIn(
            'Doubles partner registered: Yes',
            format_content(str(resp.content)),
        )
        self.assertIn(
            'Waiver completed: No',
            format_content(str(resp.content)),
        )

    def test_partner_does_not_exist(self):
        resp = self.client.get(self.get_url('nonuser@test.com'))
        self.assertIn(
            'Doubles partner registered: No',
            format_content(str(resp.content)),
        )
        self.assertIn(
            'Waiver completed: No',
            format_content(str(resp.content)),
        )

    def test_partner_no_email_provided(self):
        resp = self.client.get(self.get_url(''))
        self.assertIn(
            'No partner email provided',
            format_content(str(resp.content)),
        )

    def test_partner_already_entered_doubles(self):
        resp = self.client.get(self.get_url(self.user_already_doubles.email))
        self.assertIn(
            '!!! A user with this email address has already entered the '
            'Doubles category. Only one entry should be submitted per doubles. '
            'You will not be able to submit this entry form. Please have your '
            'partner complete the entry form on his/her account.',
            format_content(str(resp.content)),
        )

    def test_partner_already_entered_other_category(self):
        resp = self.client.get(self.get_url(self.user_already_other.email))
        self.assertIn(
            'Doubles partner registered: Yes',
            format_content(str(resp.content)),
        )
        self.assertIn(
            'Waiver completed: Yes',
            format_content(str(resp.content)),
        )


class EntryConfirmViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryConfirmViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user, status='selected')
        cls.url = reverse('entries:confirm_entry', args=(cls.entry.entry_ref,))

    def test_redirect_if_status_not_selected_or_withdrawn(self):
        entry = mommy.make(Entry, user=self.user, category='INT')
        self.client.login(username=self.user.username, password='test')
        url = reverse('entries:confirm_entry', args=(entry.entry_ref,))

        non_selected_statuses = list(STATUS_CHOICES_DICT.keys())
        non_selected_statuses.remove('selected')

        for status in non_selected_statuses:
            entry.status = status
            entry.save()
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse('permission_denied'), resp.url)

        entry.status = 'selected'
        entry.withdrawn = True
        entry.save()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('permission_denied'), resp.url)

    def test_confirm_selected(self):
        self.client.login(username=self.user.username, password='test')
        self.assertEqual(self.entry.status, 'selected')
        resp = self.client.post(self.url, {'id': self.entry.id})

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, 'selected_confirmed')

        # redirects to payment page
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            reverse('entries:selected_payment', args=[self.entry.entry_ref]),
            resp.url
        )


class SelectedPaymentViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(SelectedPaymentViewTests, cls).setUpTestData()
        cls.entry = mommy.make(
            Entry, user=cls.user, status='selected_confirmed'
        )
        cls.url = reverse(
            'entries:selected_payment', args=(cls.entry.entry_ref,)
        )

    def setUp(self):
        self.entry1 = mommy.make(
            Entry, user=self.user, category='INT', status='submitted'
        )
        self.url1 = reverse(
            'entries:selected_payment', args=(self.entry1.entry_ref,)
        )

    def login(self):
        self.client.login(username=self.user.username, password='test')

    def test_entry_not_selected_confirmed(self):
        self.login()
        resp = self.client.get(self.url1)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('paypalform', resp.context_data)
        self.assertIn(
            'This entry has not been selected and confirmed.  '
            'Please check status on the My Entries page.',
            resp.rendered_content
        )

    def test_entry_withdrawn(self):
        entry = mommy.make(
            Entry, user=self.user, status='selected_confirmed', category='ADV',
            withdrawn=True
        )
        url = reverse('entries:selected_payment', args=(entry.entry_ref,))
        self.login()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('paypalform', resp.context_data)
        self.assertIn(
            'This entry has been withdrawn.',
            resp.rendered_content
        )

    def test_entry_already_paid(self):
        self.entry.selected_entry_paid = True
        self.entry.save()

        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('paypalform', resp.context_data)
        self.assertIn(
            'The fee for this entry has already been paid.',
            resp.rendered_content
        )

    def test_renders_correct_paypal_dict_info(self):
        self.login()
        self.assertFalse(PaypalEntryTransaction.objects.exists())
        resp = self.client.get(self.url)

        # PaypalEntryTransaction is created by the view
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)
        pptrans = PaypalEntryTransaction.objects.first()
        first_invoice_id = pptrans.invoice_id

        self.assertIn('paypalform', resp.context_data)
        paypalform_data = resp.context_data['paypalform'].initial


        self.assertEqual(paypalform_data['invoice'], pptrans.invoice_id)
        self.assertEqual(
            paypalform_data['custom'], 'selected {}'.format(self.entry.id)
        )
        self.assertEqual(
            paypalform_data['item_name'],
            'Entry fee for Beginner category'
        )

        # getting the view again doesn't create a new pptrans or update inv id
        resp = self.client.get(self.url)
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)
        pptrans1 = PaypalEntryTransaction.objects.first()
        self.assertEqual(pptrans.id, pptrans1.id)
        self.assertEqual(first_invoice_id, pptrans1.invoice_id)


class WithdrawalPaymentViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(WithdrawalPaymentViewTests, cls).setUpTestData()
        cls.entry = mommy.make(
            Entry, user=cls.user, status='selected_confirmed',
            withdrawn=True
        )
        cls.url = reverse(
            'entries:withdrawal_payment', args=(cls.entry.entry_ref,)
        )

    def login(self):
        self.client.login(username=self.user.username, password='test')

    def test_entry_not_selected_confirmed_and_withdrawn(self):
        self.login()

        entry_not_wd = mommy.make(
            Entry, user=self.user, category='INT', status='selected_confirmed'
        )
        url = reverse(
            'entries:withdrawal_payment', args=(entry_not_wd.entry_ref,)
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(resp.url, reverse('permission_denied'))

        entry_not_selected_confirmed = mommy.make(
            Entry, user=self.user, category='ADV', status='submitted',
            withdrawn=True
        )
        url = reverse(
            'entries:withdrawal_payment',
            args=(entry_not_selected_confirmed.entry_ref,)
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(resp.url, reverse('permission_denied'))

    def test_entry_already_paid(self):
        self.login()
        entry_already_paid = mommy.make(
            Entry, user=self.user, category='INT', status='selected_confirmed',
            withdrawn=True, withdrawal_fee_paid=True
        )
        url = reverse(
            'entries:withdrawal_payment', args=(entry_already_paid.entry_ref,)
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(resp.url, reverse('permission_denied'))

    def test_renders_correct_paypal_dict_info(self):
        self.login()
        self.assertFalse(PaypalEntryTransaction.objects.exists())
        resp = self.client.get(self.url)

        # PaypalEntryTransaction is created by the view
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)
        pptrans = PaypalEntryTransaction.objects.first()
        first_invoice_id = pptrans.invoice_id

        self.assertIn('paypalform', resp.context_data)
        paypalform_data = resp.context_data['paypalform'].initial


        self.assertEqual(paypalform_data['invoice'], pptrans.invoice_id)
        self.assertEqual(
            paypalform_data['custom'], 'withdrawal {}'.format(self.entry.id)
        )
        self.assertEqual(
            paypalform_data['item_name'],
            'Withdrawal fee for Beginner category'
        )

        # getting the view again doesn't create a new pptrans or update inv id
        resp = self.client.get(self.url)
        self.assertEqual(PaypalEntryTransaction.objects.count(), 1)
        pptrans1 = PaypalEntryTransaction.objects.first()
        self.assertEqual(pptrans.id, pptrans1.id)
        self.assertEqual(first_invoice_id, pptrans1.invoice_id)


class PDFViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(PDFViewTests, cls).setUpTestData()
        cls.url = reverse('entries:judging_criteria')

    def test_judging_criteria_view(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_file_not_found(self):
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(curr_dir, '..', 'files/foo.pdf')
        with self.assertRaises(Http404):
            pdf_view(file_path)

        file_path = os.path.join(curr_dir, '..', 'files/Judges2017.pdf')
        resp = pdf_view(file_path)
        self.assertEqual(resp.status_code, 200)
