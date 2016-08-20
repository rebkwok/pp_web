from model_mommy import mommy

from django.test import TestCase, override_settings
from django.core.urlresolvers import reverse

from .helpers import TestSetupMixin, TestSetupLoginRequiredMixin
from ..models import Entry


class EntryHomeTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryHomeTests, cls).setUpTestData()
        cls.url = reverse('entries:entries_home')

    def test_can_get_without_login(self):
        resp = self.client.get(self.url)
        self. assertEqual(resp.status_code, 200)

    @override_settings(ENTRIES_OPEN=True)
    def test_entries_open(self):
        resp = self.client.get(self.url)
        self.assertIn('ENTER NOW', str(resp.content))

    @override_settings(ENTRIES_OPEN=False)
    def test_entries_open(self):
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
        self.assertIn('>Edit</a>', resp.rendered_content)
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
        self.assertIn('>Edit</a>', resp.rendered_content)
        self.assertIn('>Withdraw</a>', resp.rendered_content)

        # No paypal form if video entry paid
        entry.video_entry_paid = True
        entry.save()
        resp = self.client.get(self.url)
        entry_ctx = resp.context_data['entries'][0]
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])

    def test_entry_selected(self):
        # shows correct status, paypal button for entry, edit and withdraw btns
        entry = mommy.make(Entry, user=self.user, status='selected')
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        entries = resp.context_data['entries']
        self.assertEqual(len(resp.context_data['entries']), 1)
        entry_ctx = entries[0]
        self.assertEqual(entry_ctx['instance'], entry)
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNotNone(entry_ctx['paypal_selected_form'])
        self.assertFalse(entry_ctx['can_delete'])
        self.assertIn('>Edit</a>', resp.rendered_content)
        self.assertIn('>Withdraw</a>', resp.rendered_content)

        # No paypal form if selected entry paid
        entry.selected_entry_paid = True
        entry.save()
        resp = self.client.get(self.url)
        entry_ctx = resp.context_data['entries'][0]
        self.assertIsNone(entry_ctx['paypal_video_form'])
        self.assertIsNone(entry_ctx['paypal_selected_form'])

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
        self.assertIn('>Edit</a>', resp.rendered_content)
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
        self.assertNotIn('>Edit</a>', resp.rendered_content)
        self.assertNotIn('>Withdraw</a>', resp.rendered_content)
        self.assertIn(
            'Contact organizers if you wish to reopen this entry',
            resp.rendered_content
        )


class EntryCreateViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryCreateViewTests, cls).setUpTestData()
        cls.url = reverse('entries:create_entry')

    def setUp(self):
        self.post_data = {
            'category': 'BEG',
            'save': 'Save'
        }

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
        del data['save']
        data.update({'submit': 'Submit'})
        resp = self.client.post(self.url, data)

        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'video_url': ['This field is required'],
                'biography': ['This field is required']
            }
        )
        self.assertEqual(Entry.objects.count(), 0)

        data.update({
            'video_url': 'http://foo.com',
            'biography': 'About me'
        })
        self.client.post(self.url, data)
        self.assertEqual(Entry.objects.count(), 1)

        # status has been changed from in_progress to submitted
        self.assertEqual(Entry.objects.first().status, 'submitted')


class EntryUpdateViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryUpdateViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user)
        cls.url = reverse('entries:edit_entry', args=(cls.entry.entry_ref,))

    def setUp(self):
        self.post_data = {
            'category': 'BEG',
            'save': 'Save'
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
        del data['save']
        data.update({'submit': 'Submit'})
        resp = self.client.post(self.url, data)

        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'video_url': ['This field is required'],
                'biography': ['This field is required']
            }
        )

        data.update({
            'video_url': 'http://foo.com',
            'biography': 'About me'
        })
        self.client.post(self.url, data)
        self.entry.refresh_from_db()
        # status has been changed from in_progress to submitted
        self.assertEqual(self.entry.status, 'submitted')


class EntryDeleteViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryDeleteViewTests, cls).setUpTestData()
        cls.entry = mommy.make(Entry, user=cls.user)
        cls.url = reverse('entries:delete_entry', args=(cls.entry.entry_ref,))

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

    def test_get_context(self):
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.context_data['action'], 'withdraw')

    def test_withdraw(self):
        self.client.login(username=self.user.username, password='test')
        self.assertEqual(self.entry.status, 'submitted')
        self.assertFalse(self.entry.withdrawn)
        self.client.post(self.url, {'id': self.entry.id})

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, 'submitted')
        self.assertTrue(self.entry.withdrawn)
