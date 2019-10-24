from unittest.mock import patch
from model_bakery import baker

from django.urls import reverse
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

        # 12 users total; 10 created here, staff user and non-staff user
        for i in range(10):
            baker.make(
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
            'There was a problem with at least one email in the bulk email with'
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
