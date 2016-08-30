from mock import patch
from model_mommy import mommy

from django.core.urlresolvers import reverse
from django.core import mail
from django.test import TestCase
from django.contrib.auth.models import Group, User

from .helpers import TestSetupStaffLoginRequiredMixin
from activitylog.models import ActivityLog


class EmailUsersTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EmailUsersTests, cls).setUpTestData()
        cls.url = reverse('ppadmin:email_users')
        cls.mailing_list_url = reverse('ppadmin:send_mailing_list')

        # 12 users total; 10 created here, staff user and non-staff user
        for i in range(10):
            mommy.make(
                User, first_name='Test{}'.format(i),
                last_name='User{}'.format(i),
                email='Test{}@testuser.com'.format(i)
            )

    def user_dict(self, user):
        return {
                'id': user.id,
                'email': user.email,
                'fullname': '{} {} ({})'.format(
                    user.first_name, user.last_name, user.username
                )
            }

    def test_users_in_context_on_post_from_entries_list(self):
        """
        Button on entries list posts to email users view with 'email_selected'
        and a list of user ids.  Returns the form page with a list of users'
        info in a dict in the context_data; NO emails sent for this
        request
        """
        self.client.login(
            username=self.staff_user.username, password='test'
        )
        resp = self.client.post(
            self.url,
            {
                'emailusers': [
                    str(user.id) for user in
                    User.objects.all()
                ],
                'email_selected': ['Email Selected']
            }
        )
        self.assertEqual(len(resp.context_data['users_to_email']), 12)
        self.assertIsInstance(resp.context_data['users_to_email'][0], dict)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_emails_sent(self):
        self.client.login(
            username=self.staff_user.username, password='test'
        )
        resp = self.client.post(
            self.url, {
                'subject': 'Test email',
                'message': 'Test message',
                'from_address': 'test@test.com',
                'users_to_email': str([
                    self.user_dict(user) for user in User.objects.all()
                ])
            }
        )

        # 1 email, 12 bccs
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('Test message', email.body)
        self.assertEqual(email.to, [])
        self.assertEqual(email.reply_to, ['test@test.com'])
        self.assertEqual(len(email.bcc), 12)
        self.assertEqual(
            sorted(email.bcc),
            sorted([user.email for user in User.objects.all()])
        )
        self.assertEqual(
            email.subject, 'Test email'
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('ppadmin:entries'), resp.url)

    @patch('entries.email_helpers.EmailMultiAlternatives.send')
    def test_email_errors(self, mock_send):
        mock_send.side_effect = Exception('Error sending email')
        self.client.login(
            username=self.staff_user.username, password='test'
        )
        self.client.post(
            self.url, {
                'subject': 'Test email2',
                'message': 'Test message',
                'from_address': 'test@test.com',
                'users_to_email': str([
                    self.user_dict(user) for user in
                    User.objects.all()
                ])
            }
        )
        self.assertEqual(len(mail.outbox), 0)
        log = ActivityLog.objects.latest('id')
        self.assertEqual(
            log.log,
            'There was a problem with at least one email in the Bulk email with'
            ' subject "Test email2"'.format(
                self.staff_user.username
            )
        )

    def test_cc_email_sent(self):
        self.client.login(
            username=self.staff_user.username, password='test'
        )
        self.client.post(
            self.url, {
                'subject': 'Test email',
                'message': 'Test message',
                'from_address': 'test@test.com',
                'cc': True,
                'users_to_email': str([self.user_dict(self.user)])
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.cc[0], 'test@test.com')

    def test_reply_to_set_to_from_address(self):
        self.client.login(
            username=self.staff_user.username, password='test'
        )
        self.client.post(
            self.url, {
                'subject': 'Test email',
                'message': 'Test message',
                'from_address': 'test@test.com',
                'users_to_email': str([self.user_dict(self.user)])
            }
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].reply_to[0], 'test@test.com')

    def test_with_form_errors(self):
        self.client.login(
            username=self.staff_user.username, password='test'
        )
        resp = self.client.post(
            self.url, {
                'subject': 'Test email',
                'message': 'Test message',
                'users_to_email': str([self.user_dict(self.user)])
            }
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn('Please correct errors in form', resp.rendered_content)

    def test_get_email_for_mailing_list(self):
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.mailing_list_url)

        # group is created in view if it doesn't already exist
        group = Group.objects.get(name='subscribed')
        self.assertTrue(group.user_set.exists())

        # users are automatically subscribed on creation
        self.assertTrue(group.user_set.count(), 12)
        self.assertEqual(
            len(resp.context_data['users_to_email']), 12
        )

        for user in User.objects.exclude(id=self.user.id):
            group.user_set.remove(user)
        self.assertTrue(group.user_set.count(), 12)
        resp = self.client.get(self.mailing_list_url)
        self.assertTrue(group.user_set.count(), 1)
        self.assertEqual(
            len(resp.context_data['users_to_email']), 1
        )

    def test_send_email_for_mailing_list(self):
        self.client.login(username=self.staff_user.username,
                          password='test')
        # group is created in view if it doesn't already exist
        group = Group.objects.get(name='subscribed')
        self.assertTrue(group.user_set.exists())

        # users are automatically subscribed on creation
        self.assertTrue(group.user_set.count(), 12)

        resp = self.client.post(
            self.mailing_list_url,
            {
                'subject': 'Test email',
                'message': 'Test message',
                'from_address': 'test@test.com',
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 12)

        for user in User.objects.exclude(id=self.user.id):
            group.user_set.remove(user)
        self.assertTrue(group.user_set.count(), 12)
        resp = self.client.post(
            self.mailing_list_url,
            {
                'subject': 'Test email',
                'message': 'Test message',
                'from_address': 'test@test.com',
            }
        )
        self.assertTrue(group.user_set.count(), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 12)

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('ppadmin:mailing_list'), resp.url)

    def test_email_mailing_list_for_more_than_100_users(self):
        self.client.login(username=self.staff_user.username, password='test')

        group = Group.objects.get(name='subscribed')
        for i in range(150):
            mommy.make(User, email='subscribed{}@test.com'.format(i))

        subscribed_users = User.objects.filter(email__icontains='subscribed')
        for user in User.objects.exclude(
                id__in=subscribed_users.values_list('id', flat=True)
        ):
            group.user_set.remove(user)

        self.assertEqual(group.user_set.count(), 150)

        form_data = {
            'subject': 'Test email',
            'message': 'Test message',
            'from_address': 'test@test.com',
            'cc': True
        }

        self.client.post(self.mailing_list_url, form_data)
        self.assertEqual(len(mail.outbox), 2)  # emails split to 2 emails

        # from address cc'd on first email only
        self.assertEqual(mail.outbox[0].cc, ['test@test.com'])
        self.assertEqual(mail.outbox[1].cc, [])
        self.assertEqual(len(mail.outbox[0].bcc), 99)
        self.assertEqual(len(mail.outbox[1].bcc), 51)

    def test_unsubscribe_link_in_mailing_list_emails_only(self):
        form_data = {
            'subject': 'Test email',
            'message': 'Test message',
            'from_address': 'test@test.com',
            'cc': True
        }

        # mailing list
        self.client.login(username=self.staff_user.username, password='test')
        self.client.post(self.mailing_list_url, form_data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 12)
        self.assertIn(
            'Unsubscribe from this mailing list', mail.outbox[0].body
        )
        self.assertIn(
            reverse('accounts:subscribe'), mail.outbox[0].body
        )

        # bulk email
        form_data.update({'users_to_email': str([self.user_dict(self.user)])})
        self.client.post(self.url, form_data)

        self.assertEqual(len(mail.outbox), 2)  # mailing list email is first
        self.assertEqual(mail.outbox[-1].bcc, [self.user.email])
        self.assertNotIn(
            'Unsubscribe from this mailing list', mail.outbox[-1].body
        )

    def test_sending_test_email_only_goes_to_from_address(self):
        form_data = {
            'subject': 'Test email',
            'message': 'Test message',
            'from_address': 'test@test.com',
            'cc': True,
            'send_test': True
        }

        # mailing list
        self.client.login(username=self.staff_user.username, password='test')
        self.client.post(self.mailing_list_url, form_data)

        self.assertEqual(len(mail.outbox), 1)
        # email is sent to the 'from' address only
        self.assertEqual(mail.outbox[0].bcc, ['test@test.com'])
        # cc ignored for test email
        self.assertEqual(mail.outbox[0].cc, [])
        self.assertEqual(
            mail.outbox[0].subject,
            'Test email [TEST EMAIL]'.format(
            )
        )

        del form_data['send_test']
        self.client.post(self.mailing_list_url, form_data)
        self.assertEqual(len(mail.outbox), 2)
        # email is sent to the mailing list users
        self.assertEqual(len(mail.outbox[1].bcc), 12)
        self.assertEqual(mail.outbox[1].cc, ['test@test.com'])
        self.assertEqual(mail.outbox[1].reply_to, ['test@test.com'])
        self.assertEqual(mail.outbox[1].subject, 'Test email')
