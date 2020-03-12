import csv
import os
import pytz

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from model_bakery import baker

from django.conf import settings
from django.core import management, mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from django.utils import timezone

from allauth.account.models import EmailAddress

from accounts.admin import CookiePolicyAdminForm, DataPrivacyPolicyAdminForm
from accounts.forms import DataPrivacyAgreementForm, DisclaimerForm
from accounts.management.commands.import_disclaimer_data import logger as \
    import_disclaimer_data_logger
from accounts.management.commands.export_encrypted_disclaimers import EmailMessage
from accounts.models import CookiePolicy, OnlineDisclaimer, \
    WAIVER_TERMS, DataPrivacyPolicy, SignedDataPrivacy
from ..utils import active_data_privacy_cache_key
from accounts.views import ProfileUpdateView, DisclaimerCreateView

from .helpers import _create_session, has_active_data_privacy_agreement, \
    TestSetupMixin, make_data_privacy_agreement


class DisclaimerFormTests(TestSetupMixin, TestCase):

    def setUp(self):
        self.form_data = {
            'emergency_contact_relationship': 'mother',
            'emergency_contact_phone': '4547',
            'emergency_contact_name': 'test2',
            'terms_accepted': True,
            'password': 'password'
        }

    def test_disclaimer_form(self):
        form = DisclaimerForm(data=self.form_data)
        self.assertTrue(form.is_valid())

    def test_custom_validators(self):
        self.form_data['terms_accepted'] = False
        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'terms_accepted': [
                'You must confirm that you accept the waiver terms'
            ]}
        )

        self.form_data['terms_accepted'] = True


class ProfileUpdateViewTests(TestSetupMixin, TestCase):

    def test_updating_user_data(self):
        """
        Test custom view to allow users to update their details
        """
        url = reverse('accounts:update_profile')
        data = {
            'username': self.user.username,
            'first_name': 'Fred',
            'last_name': self.user.last_name,
            'dob': '01 Jan 1990'
        }
        self.client.login(username=self.user.username, password="test")
        self.client.post(url, data)
        self.user.refresh_from_db()
        self.assertEquals(self.user.first_name, "Fred")

    def test_cannot_change_to_an_existing_username(self):
        user1 = baker.make(User, username="test_user1",
                          first_name="Test",
                          last_name="User",
                          )
        url = reverse('accounts:update_profile')

        # Try to change self.user's username to user1's
        data = {
            'username': user1.username,
            'first_name':  self.user.first_name,
            'last_name': self.user.last_name,
            'dob': '01 Jan 1990'
        }
        self.client.login(username=self.user.username, password="test")
        response = self.client.post(url, data)
        form = response.context_data["form"]
        self.assertEqual(
            form.errors,
            {'username': ['A user already exists with this username']}
        )


class UserProfileTests(TestCase):

    def test_userprofile_str(self):
        management.call_command('setup_test_data')
        user = User.objects.get(first_name='Sally')
        self.assertEqual(str(user.profile), user.username)


class ProfileTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(ProfileTests, cls).setUpTestData()
        Group.objects.get_or_create(name='instructors')
        cls.user_with_online_disclaimer = User.objects.create_user(
            username='test_disc', password='test'
        )
        make_data_privacy_agreement(cls.user_with_online_disclaimer)
        baker.make(OnlineDisclaimer, user=cls.user_with_online_disclaimer)
        cls.user_no_disclaimer = User.objects.create_user(
            username='test_no_disc', password='test'
        )
        make_data_privacy_agreement(cls.user_no_disclaimer)
        cls.url = reverse('accounts:profile')

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_profile_view(self):
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEquals(resp.status_code, 200)

    def test_cache(self):
        self.assertIsNone(
            cache.get('user_{}_has_disclaimer'.format(
                self.user_with_online_disclaimer.id)
            )
        )
        self.client.login(
            username=self.user_with_online_disclaimer.username, password='test'
        )
        resp = self.client.get(self.url)
        self.assertEquals(resp.status_code, 200)
        self.assertTrue(
            cache.get('user_{}_has_disclaimer'.format(
                self.user_with_online_disclaimer.id)
            )
        )

        # deleting disclaimer updates cache
        OnlineDisclaimer.objects.get(
            user=self.user_with_online_disclaimer
        ).delete()
        self.assertFalse(
            cache.get('user_{}_has_disclaimer'.format(
                self.user_with_online_disclaimer.id)
            )
        )

    def test_profile_view_shows_disclaimer_info(self):
        self.client.login(username=self.user, password='test')
        resp = self.client.get(self.url)
        self.assertIn("Completed", str(resp.content))
        self.assertNotIn("Not completed", str(resp.content))
        self.assertNotIn("/accounts/waiver", str(resp.content))

        self.client.login(
            username=self.user_with_online_disclaimer.username, password='test'
        )
        resp = self.client.get(self.url)
        self.assertIn("Completed", str(resp.content))
        self.assertNotIn("Not completed", str(resp.content))
        self.assertNotIn("/accounts/waiver", str(resp.content))

        self.client.login(
            username=self.user_no_disclaimer.username, password='test'
        )
        resp = self.client.get(self.url)
        self.assertIn("Not completed", str(resp.content))
        self.assertIn("/accounts/waiver", str(resp.content))

    def test_profile_requires_signed_data_privacy(self):
        self.client.login(username=self.user, password='test')
        baker.make(DataPrivacyPolicy)
        resp = self.client.get(self.url)

        # request = self.factory.get(self.url)
        # request.user = self.user
        # resp = profile(request)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:data_privacy_review'), resp.url)


class CustomLoginViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(CustomLoginViewTests, cls).setUpTestData()
        cls.user1 = User.objects.create(username='test_user', is_active=True)
        cls.user1.set_password('password')
        cls.user1.save()
        EmailAddress.objects.create(user=cls.user1,
                                    email='test@gmail.com',
                                    primary=True,
                                    verified=True)

    def test_get_login_view(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_post_login(self):
        resp = self.client.post(
            reverse('login'),
            {'login': self.user1.username, 'password': 'password'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)

    def test_login_from_password_change(self):
        # post with login username and password overrides next in request
        # params to return to profile
        resp = self.client.post(
            reverse('login') + '?next=/accounts/password/change/',
            {'login': self.user1.username, 'password': 'password'}
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)

        resp = self.client.post(
            reverse('login') + '?next=/accounts/password/set/',
            {'login': self.user1.username, 'password': 'password'}
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)


class CustomSignUpViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('account_signup')
        super(CustomSignUpViewTests, cls).setUpTestData()

        cls.form_data = {
            'first_name': 'Test',
             'last_name': 'User',
             'dob': '01 Jan 1990',
             'username': 'testuser', 'email': 'testuser@test.com',
             'password1': 'dj34nmadkl24', 'password2': 'dj34nmadkl24',
            'data_privacy_confirmation': True
         }

    def test_get_signup_view(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context_data['form'].fields['username'].initial)

    def test_get_signup_view_with_username(self):
        resp = self.client.get(self.url + "?username=test")
        self.assertEqual(
            resp.context_data['form'].fields['username'].initial, 'test'
        )

    def test_post_signup_form_creates_user_profile(self):
        self.assertFalse(User.objects.filter(username='testuser').exists())
        self.client.post(self.url, self.form_data)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        user = User.objects.get(username='testuser')
        self.assertIsNotNone(user.profile.dob)

    def test_signup_form_with_invalid_name(self):
        # first_name must have 30 characters or fewer
        form_data = self.form_data.copy()
        form_data.update({
            'first_name': 'abcdefghijklmnopqrstuvwxyz12345',
        })
        resp = self.client.post(self.url, form_data)
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'first_name': [
                    'Ensure this value has at most 30 characters (it has 31).'
                ]
            }
        )

    def test_signup_form_with_invalid_date_format(self):
        form_data = self.form_data.copy()
        form_data.update({
            'dob': '19Jan1990',
        })
        resp = self.client.post(self.url, form_data)
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'dob': [
                    'Invalid date format.  Select from the date picker or '
                    'enter date in the format e.g. 08 Jun 1990'
                ]
            }
        )

    def test_signup_form_under_18(self):
        # user must be over 18 to register
        year = timezone.now().year - 17
        form_data = self.form_data.copy()
        form_data.update({
            'dob': '19 Jan {}'.format(year),
        })
        resp = self.client.post(self.url, form_data)
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'dob': [
                    'You must be 18 or over to register'
                ]
            }
        )

    def test_signup_dataprotection_confirmation_required(self):
        baker.make(DataPrivacyPolicy)
        form_data = self.form_data.copy()
        form_data.update({'data_privacy_confirmation': False})

        resp = self.client.post(self.url, form_data)
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'data_privacy_confirmation': [
                    'You must check this box to continue'
                ]
            }
        )

    def test_sign_up_with_data_protection(self):
        dp = baker.make(DataPrivacyPolicy)
        SignedDataPrivacy.objects.all().delete()
        form_data = self.form_data.copy()
        form_data.update({'data_privacy_confirmation': True})
        url = reverse('account_signup')
        self.client.post(url, form_data)
        user = User.objects.latest('id')
        self.assertEquals('Test', user.first_name)
        self.assertEquals('User', user.last_name)
        self.assertTrue(SignedDataPrivacy.objects.exists())
        self.assertEqual(user.data_privacy_agreement.first().version, dp.version)


class DisclaimerModelTests(TestCase):
    def test_online_disclaimer_str(self):
        user = baker.make(User, username='testuser')
        disclaimer = baker.make(OnlineDisclaimer, user=user)
        self.assertEqual(str(disclaimer), 'testuser - {}'.format(
            disclaimer.date.astimezone(
                pytz.timezone('Europe/London')
            ).strftime('%d %b %Y, %H:%M')
        ))

    def test_default_terms_set_on_new_online_disclaimer(self):
        disclaimer = baker.make(
            OnlineDisclaimer, waiver_terms="foo"
        )
        self.assertEqual(disclaimer.waiver_terms, WAIVER_TERMS)

    def test_cannot_update_terms_after_first_save(self):
        disclaimer = baker.make(OnlineDisclaimer)
        self.assertEqual(disclaimer.waiver_terms, WAIVER_TERMS)

        with self.assertRaises(ValueError):
            disclaimer.waiver_terms = 'foo'
            disclaimer.save()


class DisclaimerCreateViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(DisclaimerCreateViewTests, cls).setUpTestData()
        cls.url = reverse('accounts:disclaimer_form')

    def setUp(self):
        super().setUp()
        self.user_no_disclaimer = User.objects.create_user(
            username='user_no_disc', password='password'
        )

        self.form_data = {
            'emergency_contact_name': 'test1',
            'emergency_contact_relationship': 'mother',
            'emergency_contact_phone': '4547',
            'terms_accepted': True,
            'password': 'password'
        }

    def _get_response(self, user):
        url = reverse('accounts:disclaimer_form')
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        view = DisclaimerCreateView.as_view()
        return view(request)

    def _post_response(self, user, form_data):
        url = reverse('accounts:disclaimer_form')
        session = _create_session()
        request = self.factory.post(url, form_data)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        view = DisclaimerCreateView.as_view()
        return view(request)

    def test_login_required(self):
        resp = self.client.get(self.url)
        redirected_url = reverse('account_login') + "?next={}".format(self.url)

        self.assertEqual(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_shows_msg_if_already_has_disclaimer(self):
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        self.assertIn(
            "You have already completed a waiver.",
            str(resp.rendered_content)
        )
        self.assertNotIn("Submit", str(resp.rendered_content))

        resp = self._get_response(self.user_no_disclaimer)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(
            "You have already completed a waiver.",
            str(resp.rendered_content)
        )
        self.assertIn("Submit", str(resp.rendered_content))


    def test_submitting_form_without_valid_password(self):
        # setup creates 1 user with online disclaimer
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)
        self.user_no_disclaimer.set_password('test_password')
        self.user_no_disclaimer.save()

        self.assertTrue(self.user_no_disclaimer.has_usable_password())

        self.client.login(
            username=self.user_no_disclaimer.username, password='test_password'
        )
        self.client.post(self.url, self.form_data)
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)

    def test_submitting_form_creates_disclaimer(self):
        # setup creates 1 user with online disclaimer
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)
        self.client.login(
            username=self.user_no_disclaimer.username, password='password'
        )
        self.client.post(self.url, self.form_data)
        self.assertEqual(OnlineDisclaimer.objects.count(), 2)

        # user now has disclaimer and can't re-access
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        self.assertIn(
            "You have already completed a waiver.",
            str(resp.rendered_content)
        )
        self.assertNotIn("Submit", str(resp.rendered_content))

        # posting same data again redirects to form
        resp = self.client.post(self.url, self.form_data)
        self.assertEqual(resp.status_code, 302)
        # no new disclaimer created
        self.assertEqual(OnlineDisclaimer.objects.count(), 2)

    def test_message_shown_if_no_usable_password(self):
        user = baker.make(User)
        user.set_unusable_password()
        user.save()

        resp = self._get_response(user)
        self.assertIn(
            "You need to set a password on your account in order to complete "
            "the waiver.",
            resp.rendered_content
        )

    def test_cannot_complete_disclaimer_without_usable_password(self):
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)
        user = baker.make(User)
        user.set_unusable_password()
        user.save()

        resp = self._post_response(user, self.form_data)
        self.assertIn(
            "No password set on account.",
            str(resp.content)
        )
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)

        user.set_password('password')
        user.save()
        self._post_response(user, self.form_data)
        self.assertEqual(OnlineDisclaimer.objects.count(), 2)


class DataProtectionViewTests(TestSetupMixin, TestCase):

    def test_get_data_protection_view(self):
        # no need to be a logged in user to access
        resp = self.client.get(reverse('data_privacy_policy'))
        self.assertEqual(resp.status_code, 200)


@override_settings(LOG_FOLDER=os.path.dirname(__file__))
class ExportDisclaimersTests(TestCase):

    def setUp(self):
        baker.make(OnlineDisclaimer, _quantity=10)

    def test_export_disclaimers_creates_default_bu_file(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'waivers_bu.csv')
        self.assertFalse(os.path.exists(bu_file))
        management.call_command('export_disclaimers')
        self.assertTrue(os.path.exists(bu_file))
        os.unlink(bu_file)

    def test_export_disclaimers_writes_correct_number_of_rows(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'waivers_bu.csv')
        management.call_command('export_disclaimers')

        with open(bu_file, 'r') as exported:
            reader = csv.reader(exported)
            rows = list(reader)
        self.assertEqual(len(rows), 11)  # 10 records plus header row
        os.unlink(bu_file)

    def test_export_disclaimers_with_filename_argument(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'test_file.csv')
        self.assertFalse(os.path.exists(bu_file))
        management.call_command('export_disclaimers', file=bu_file)
        self.assertTrue(os.path.exists(bu_file))
        os.unlink(bu_file)


@override_settings(LOG_FOLDER=os.path.dirname(__file__))
class ExportEncryptedDisclaimersTests(TestCase):

    def setUp(self):
        baker.make(OnlineDisclaimer, _quantity=10)

    def test_export_disclaimers_creates_default_bu_file(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'waivers.bu')
        self.assertFalse(os.path.exists(bu_file))
        management.call_command('export_encrypted_disclaimers')
        self.assertTrue(os.path.exists(bu_file))
        os.unlink(bu_file)

    def test_export_disclaimers_sends_email(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'waivers.bu')
        management.call_command('export_encrypted_disclaimers')

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [settings.SUPPORT_EMAIL])

        os.unlink(bu_file)

    @patch.object(EmailMessage, 'send')
    def test_email_errors(self, mock_send):
        mock_send.side_effect = Exception('Error sending mail')
        bu_file = os.path.join(settings.LOG_FOLDER, 'waivers.bu')

        self.assertFalse(os.path.exists(bu_file))
        management.call_command('export_encrypted_disclaimers')
        # mail not sent, but back up still created
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(os.path.exists(bu_file))
        os.unlink(bu_file)

    def test_export_disclaimers_with_filename_argument(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'test_file.txt')
        self.assertFalse(os.path.exists(bu_file))
        management.call_command('export_encrypted_disclaimers', file=bu_file)
        self.assertTrue(os.path.exists(bu_file))
        os.unlink(bu_file)


class ImportDisclaimersTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.bu_file = os.path.join(
            os.path.dirname(__file__), 'test_data/test_waivers_backup.csv'
        )

    def test_import_disclaimers_no_matching_users(self):
        import_disclaimer_data_logger.warning = Mock()
        self.assertFalse(OnlineDisclaimer.objects.exists())
        management.call_command('import_disclaimer_data', file=self.bu_file)
        self.assertEqual(OnlineDisclaimer.objects.count(), 0)

        self.assertEqual(import_disclaimer_data_logger.warning.call_count, 3)
        self.assertIn(
            "Unknown user test_1 in backup data; data on row 1 not imported",
            str(import_disclaimer_data_logger.warning.call_args_list[0])
        )
        self.assertIn(
            "Unknown user test_2 in backup data; data on row 2 not imported",
            str(import_disclaimer_data_logger.warning.call_args_list[1])
        )
        self.assertIn(
            "Unknown user test_3 in backup data; data on row 3 not imported",
            str(import_disclaimer_data_logger.warning.call_args_list[2])
        )

    def test_import_disclaimers(self):
        for username in ['test_1', 'test_2', 'test_3']:
            baker.make(User, username=username)
        self.assertFalse(OnlineDisclaimer.objects.exists())
        management.call_command('import_disclaimer_data', file=self.bu_file)
        self.assertEqual(OnlineDisclaimer.objects.count(), 3)

    def test_import_disclaimers_existing_data(self):
        import_disclaimer_data_logger.warning = Mock()
        import_disclaimer_data_logger.info = Mock()

        # if disclaimer already exists for a user, it isn't imported
        for username in ['test_1', 'test_2']:
            baker.make(User, username=username)
        test_3 = baker.make(User, username='test_3')
        baker.make(OnlineDisclaimer, user=test_3, emergency_contact_name="Don")

        self.assertEqual(OnlineDisclaimer.objects.count(), 1)
        management.call_command('import_disclaimer_data', file=self.bu_file)
        self.assertEqual(OnlineDisclaimer.objects.count(), 3)

        # data has not been overwritten
        disclaimer = OnlineDisclaimer.objects.get(user=test_3)
        self.assertEqual(disclaimer.emergency_contact_name, 'Don')

        self.assertEqual(import_disclaimer_data_logger.warning.call_count, 1)
        self.assertEqual(import_disclaimer_data_logger.info.call_count, 2)

        self.assertIn(
            "Waiver for test_1 imported from backup.",
            str(import_disclaimer_data_logger.info.call_args_list[0])
        )
        self.assertIn(
            "Waiver for test_2 imported from backup.",
            str(import_disclaimer_data_logger.info.call_args_list[1])
        )
        self.assertIn(
            "Waiver for test_3 already exists and has not been "
            "overwritten with backup data. Dates in db and back up DO NOT "
            "match",
            str(import_disclaimer_data_logger.warning.call_args_list[0])
        )

    def test_import_disclaimers_existing_data_matching_dates(self):
        import_disclaimer_data_logger.warning = Mock()
        import_disclaimer_data_logger.info = Mock()

        test_1 = baker.make(User, username='test_1')
        test_2 = baker.make(User, username='test_2')
        test_3 = baker.make(User, username='test_3')
        baker.make(
            OnlineDisclaimer, user=test_2,
            date=datetime(2015, 1, 15, 15, 43, 19, 747445, tzinfo=timezone.utc),
            date_updated=datetime(
                2016, 1, 6, 15, 9, 16, 920219, tzinfo=timezone.utc
            )
        ),
        baker.make(
            OnlineDisclaimer, user=test_3,
            date=datetime(2016, 2, 18, 16, 9, 16, 920219, tzinfo=timezone.utc),
        )

        self.assertEqual(OnlineDisclaimer.objects.count(), 2)
        management.call_command('import_disclaimer_data', file=self.bu_file)
        self.assertEqual(OnlineDisclaimer.objects.count(), 3)

        self.assertEqual(import_disclaimer_data_logger.warning.call_count, 2)
        self.assertEqual(import_disclaimer_data_logger.info.call_count, 1)

        self.assertIn(
            "Waiver for test_1 imported from backup.",
            str(import_disclaimer_data_logger.info.call_args_list[0])
        )
        self.assertIn(
            "Waiver for test_2 already exists and has not been "
            "overwritten with backup data. Dates in db and back up "
            "match",
            str(import_disclaimer_data_logger.warning.call_args_list[0])
        )
        self.assertIn(
            "Waiver for test_3 already exists and has not been "
            "overwritten with backup data. Dates in db and back up "
            "match",
            str(import_disclaimer_data_logger.warning.call_args_list[1])
        )

    def test_imported_data_is_correct(self):
        test_1 = baker.make(User, username='test_1')
        management.call_command('import_disclaimer_data', file=self.bu_file)
        test_1_disclaimer = OnlineDisclaimer.objects.get(user=test_1)

        self.assertEqual(
            test_1_disclaimer.date,
            datetime(2015, 12, 18, 15, 32, 7, 191781, tzinfo=timezone.utc)
        )
        self.assertEqual(test_1_disclaimer.emergency_contact_name, 'Test1 Contact1')
        self.assertEqual(
            test_1_disclaimer.emergency_contact_relationship, 'Partner'
        )
        self.assertEqual(
            test_1_disclaimer.emergency_contact_phone, '8782347239'
        )
        self.assertIsNotNone(test_1_disclaimer.waiver_terms)
        self.assertTrue(test_1_disclaimer.terms_accepted)


class DataPrivacyPolicyModelTests(TestCase):

    def test_no_policy_version(self):
        self.assertEqual(DataPrivacyPolicy.current_version(), 0)

    def test_policy_versioning(self):
        self.assertEqual(DataPrivacyPolicy.current_version(), 0)

        DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('1.0'))

        DataPrivacyPolicy.objects.create(content='Foo1')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('2.0'))

        DataPrivacyPolicy.objects.create(content='Foo2', version=Decimal('2.6'))
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('2.6'))

        DataPrivacyPolicy.objects.create(content='Foo3')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('3.0'))

    def test_cannot_make_new_version_with_same_content(self):
        DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('1.0'))
        with self.assertRaises(ValidationError):
            DataPrivacyPolicy.objects.create(content='Foo')

    def test_policy_str(self):
        dp = DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(
            str(dp), 'Data Privacy Policy - Version {}'.format(dp.version)
        )


class CookiePolicyModelTests(TestCase):

    def test_policy_versioning(self):
        CookiePolicy.objects.create(content='Foo')
        self.assertEqual(CookiePolicy.current().version, Decimal('1.0'))

        CookiePolicy.objects.create(content='Foo1')
        self.assertEqual(CookiePolicy.current().version, Decimal('2.0'))

        CookiePolicy.objects.create(content='Foo2', version=Decimal('2.6'))
        self.assertEqual(CookiePolicy.current().version, Decimal('2.6'))

        CookiePolicy.objects.create(content='Foo3')
        self.assertEqual(CookiePolicy.current().version, Decimal('3.0'))

    def test_cannot_make_new_version_with_same_content(self):
        CookiePolicy.objects.create(content='Foo')
        self.assertEqual(CookiePolicy.current().version, Decimal('1.0'))
        with self.assertRaises(ValidationError):
            CookiePolicy.objects.create(content='Foo')

    def test_policy_str(self):
        dp = CookiePolicy.objects.create(content='Foo')
        self.assertEqual(
            str(dp), 'Cookie Policy - Version {}'.format(dp.version)
        )


class SignedDataPrivacyModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        DataPrivacyPolicy.objects.create(content='Foo')

    def setUp(self):
        super().setUp()
        self.user = baker.make(User)

    def test_cached_on_save(self):
        make_data_privacy_agreement(self.user)
        self.assertTrue(cache.get(active_data_privacy_cache_key(self.user)))

        DataPrivacyPolicy.objects.create(content='New Foo')
        self.assertFalse(has_active_data_privacy_agreement(self.user))

    def test_delete(self):
        make_data_privacy_agreement(self.user)
        self.assertTrue(cache.get(active_data_privacy_cache_key(self.user)))

        SignedDataPrivacy.objects.get(user=self.user).delete()
        self.assertIsNone(cache.get(active_data_privacy_cache_key(self.user)))


class DataPrivacyViewTests(TestCase):

    def test_get_data_privacy_view(self):
        # no need to be a logged in user to access
        resp = self.client.get(reverse('data_privacy_policy'))
        self.assertEqual(resp.status_code, 200)


class CookiePolicyViewTests(TestCase):

    def test_get_cookie_view(self):
        # no need to be a logged in user to access
        resp = self.client.get(reverse('cookie_policy'))
        self.assertEqual(resp.status_code, 200)


class SignedDataPrivacyCreateViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('accounts:data_privacy_review')

    def setUp(self):
        super().setUp()
        self.client.login(username=self.user.username, password='test')

    def test_user_already_has_active_signed_agreement(self):
        # dp agreement is created in setup
        self.assertTrue(has_active_data_privacy_agreement(self.user))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('entries:entries_home'))

        # make new policy
        baker.make(DataPrivacyPolicy)
        self.assertFalse(has_active_data_privacy_agreement(self.user))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_create_new_agreement(self):
        # make new policy
        baker.make(DataPrivacyPolicy)
        self.assertFalse(has_active_data_privacy_agreement(self.user))

        self.client.post(self.url, data={'confirm': True})
        self.assertTrue(has_active_data_privacy_agreement(self.user))


class DataPrivacyAgreementFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = baker.make(User)
        baker.make(DataPrivacyPolicy)

    def test_confirm_required(self):
        form = DataPrivacyAgreementForm(next_url='/', data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors, {'confirm': ['You must check this box to continue']}
        )
        form = DataPrivacyAgreementForm(next_url='/', data={'confirm': True})
        self.assertTrue(form.is_valid())


class CookiePolicyAdminFormTests(TestCase):

    def test_create_cookie_policy_version_help(self):
        form = CookiePolicyAdminForm()
        # version initial set to 1.0 for first policy
        self.assertEqual(form.fields['version'].help_text, '')
        self.assertEqual(form.fields['version'].initial, 1.0)

        baker.make(CookiePolicy, version=1.0)
        # help text added if updating
        form = CookiePolicyAdminForm()
        self.assertEqual(
            form.fields['version'].help_text,
            'Current version is 1.0.  Leave blank for next major version'
        )
        self.assertIsNone(form.fields['version'].initial)

    def test_validation_error_if_no_changes(self):
        policy = baker.make(CookiePolicy, version=1.0, content='Foo')
        form = CookiePolicyAdminForm(
            data={
                'content': 'Foo',
                'version': 1.5,
                'issue_date': policy.issue_date
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(),
            [
                'No changes made from previous version; new version must '
                'update policy content'
            ]
        )


class DataPrivacyPolicyAdminFormTests(TestCase):

    def test_create_data_privacy_policy_version_help(self):
        form = DataPrivacyPolicyAdminForm()
        # version initial set to 1.0 for first policy
        self.assertEqual(form.fields['version'].help_text, '')
        self.assertEqual(form.fields['version'].initial, 1.0)

        baker.make(DataPrivacyPolicy, version=1.0)
        # help text added if updating
        form = DataPrivacyPolicyAdminForm()
        self.assertEqual(
            form.fields['version'].help_text,
            'Current version is 1.0.  Leave blank for next major version'
        )
        self.assertIsNone(form.fields['version'].initial)

    def test_validation_error_if_no_changes(self):
        policy = baker.make(DataPrivacyPolicy, version=1.0, content='Foo')
        form = DataPrivacyPolicyAdminForm(
            data={
                'content': 'Foo',
                'version': 1.5,
                'issue_date': policy.issue_date
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(),
            [
                'No changes made from previous version; new version must '
                'update policy content'
            ]
        )
