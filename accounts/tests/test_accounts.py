import csv
import os

from datetime import date, datetime, timedelta
from mock import Mock, patch
from model_mommy import mommy

from django.conf import settings
from django.core import management, mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.urlresolvers import reverse
from django.utils import timezone

from allauth.account.models import EmailAddress

from accounts.forms import SignupForm, DisclaimerForm
from accounts.management.commands.import_disclaimer_data import logger as \
    import_disclaimer_data_logger
from accounts.management.commands.export_encrypted_disclaimers import EmailMessage
from accounts.models import OnlineDisclaimer, \
    DISCLAIMER_TERMS, MEDICAL_TREATMENT_TERMS, OVER_18_TERMS
from accounts.views import ProfileUpdateView, profile, DisclaimerCreateView

from .helpers import _create_session, TestSetupMixin


class SignUpFormTests(TestSetupMixin, TestCase):

    def test_signup_form(self):
        form_data = {'first_name': 'Test',
                     'last_name': 'User'}
        form = SignupForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_signup_form_with_invalid_data(self):
        # first_name must have 30 characters or fewer
        form_data = {'first_name': 'abcdefghijklmnopqrstuvwxyz12345',
                     'last_name': 'User'}
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_user_assigned_from_request(self):
        user = mommy.make(User)
        url = reverse('account_signup')
        request = self.factory.get(url)
        request.user = user
        form_data = {'first_name': 'New',
                     'last_name': 'Name'}
        form = SignupForm(data=form_data)
        self.assertTrue(form.is_valid())
        form.signup(request, user)
        self.assertEquals('New', user.first_name)
        self.assertEquals('Name', user.last_name)


class DisclaimerFormTests(TestSetupMixin, TestCase):

    def setUp(self):
        self.form_data = {
            'name': 'test', 'gender': 'female',
            'dob': '01 Jan 1990', 'address': '1 test st',
            'postcode': 'TEST1', 'home_phone': '123445', 'mobile_phone': '124566',
            'emergency_contact1_name': 'test1',
            'emergency_contact1_relationship': 'mother',
            'emergency_contact1_phone': '4547',
            'emergency_contact2_name': 'test2',
            'emergency_contact2_relationship': 'father',
            'emergency_contact2_phone': '34657',
            'medical_conditions': False, 'medical_conditions_details': '',
            'joint_problems': False, 'joint_problems_details': '',
            'allergies': False, 'allergies_details': '',
            'medical_treatment_permission': True,
            'terms_accepted': True,
            'age_over_18_confirmed': True,
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
                'You must confirm that you accept the disclaimer terms'
            ]}
        )

        self.form_data['terms_accepted'] = True
        self.form_data['age_over_18_confirmed'] = False

        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'age_over_18_confirmed': [
                'You must confirm that you are 18 or over'
            ]}
        )

        self.form_data['age_over_18_confirmed'] = True
        self.form_data['medical_treatment_permission'] = False
        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'medical_treatment_permission': [
                'You must confirm that you give permission for medical '
                'treatment in the event of an accident'
            ]}
        )

    def test_under_18(self):
        self.form_data['dob'] = '01 Jan 2015'
        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'dob': [
                'You must be over 18 years in order to register'
            ]}
        )

    def test_invalid_date_format(self):
        self.form_data['dob'] = '32 Jan 2015'
        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'dob': [
                'Invalid date format.  Select from the date picker or enter '
                'date in the format e.g. 08 Jun 1990'
            ]}
        )

    def test_medical_conditions_without_details(self):
        self.form_data['medical_conditions'] = True
        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'medical_conditions_details': [
                'Please provide details of medical conditions'
            ]}
        )

    def test_joint_problems_without_details(self):
        self.form_data['joint_problems'] = True
        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'joint_problems_details': [
                'Please provide details of knee/back/shoulder/ankle/hip/neck '
                'problems'
            ]}
        )

    def test_allergies_without_details(self):
        self.form_data['allergies'] = True
        form = DisclaimerForm(data=self.form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'allergies_details': [
                'Please provide details of allergies'
            ]}
        )


class ProfileUpdateViewTests(TestSetupMixin, TestCase):

    def test_updating_user_data(self):
        """
        Test custom view to allow users to update their details
        """
        user = mommy.make(User, username="test_user",
                          first_name="Test",
                          last_name="User",
                          )
        url = reverse('accounts:update_profile')
        request = self.factory.post(
            url, {'username': user.username,
                  'first_name': 'Fred', 'last_name': user.last_name}
        )
        request.user = user
        view = ProfileUpdateView.as_view()
        resp = view(request)
        updated_user = User.objects.get(username="test_user")
        self.assertEquals(updated_user.first_name, "Fred")


class ProfileTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(ProfileTests, cls).setUpTestData()
        Group.objects.get_or_create(name='instructors')
        cls.user_with_online_disclaimer = User.objects.create_user(
            username='test_disc', password='test'
        )
        mommy.make(OnlineDisclaimer, user=cls.user_with_online_disclaimer)
        cls.user_no_disclaimer = User.objects.create_user(
            username='test_no_disc', password='test'
        )
        cls.url = reverse('accounts:profile')

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

    def test_profile_view_shows_disclaimer_info(self):
        self.client.login(username=self.user, password='test')
        resp = self.client.get(self.url)
        self.assertIn("Completed", str(resp.content))
        self.assertNotIn("Not completed", str(resp.content))
        self.assertNotIn("/accounts/disclaimer", str(resp.content))

        self.client.login(
            username=self.user_with_online_disclaimer.username, password='test'
        )
        resp = self.client.get(self.url)
        self.assertIn("Completed", str(resp.content))
        self.assertNotIn("Not completed", str(resp.content))
        self.assertNotIn("/accounts/disclaimer", str(resp.content))

        self.client.login(
            username=self.user_no_disclaimer.username, password='test'
        )
        resp = self.client.get(self.url)
        self.assertIn("Not completed", str(resp.content))
        self.assertIn("/accounts/disclaimer", str(resp.content))


class CustomLoginViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(CustomLoginViewTests, cls).setUpTestData()
        cls.user = User.objects.create(username='test_user', is_active=True)
        cls.user.set_password('password')
        cls.user.save()
        EmailAddress.objects.create(user=cls.user,
                                    email='test@gmail.com',
                                    primary=True,
                                    verified=True)

    def test_get_login_view(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_post_login(self):
        resp = self.client.post(
            reverse('login'),
            {'login': self.user.username, 'password': 'password'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)

    def test_login_from_password_change(self):
        # facebook url is modified to return to the profile page
        resp = self.client.get(
            reverse('login') + '?next=/accounts/password/change/'
        )
        # url is weirdly formatted one way if we run only this test and the
        # other if we run all. Not sure why yet, but it would behave correctly
        # either way
        self.assertTrue(
            'href="/accounts/facebook/login/?process=login'
            '&next=%2Faccounts%2Fprofile"' in resp.rendered_content or
            'href="/accounts/facebook/login/?next=%2Faccounts%2Fprofile'
            '&process=login"' in resp.rendered_content
        )

        resp = self.client.get(
            reverse('login') + '?next=/accounts/password/set/'
        )
        self.assertTrue(
            'href="/accounts/facebook/login/?process=login'
            '&next=%2Faccounts%2Fprofile"' in resp.rendered_content or
            'href="/accounts/facebook/login/?next=%2Faccounts%2Fprofile'
            '&process=login"' in resp.rendered_content
        )

        # post with login username and password overrides next in request
        # params to return to profile
        resp = self.client.post(
            reverse('login') + '?next=/accounts/password/change/',
            {'login': self.user.username, 'password': 'password'}
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)

        resp = self.client.post(
            reverse('login') + '?next=/accounts/password/set/',
            {'login': self.user.username, 'password': 'password'}
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:profile'), resp.url)


class CustomSignUpViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('account_signup')
        super(CustomSignUpViewTests, cls).setUpTestData()

    def test_get_signup_view(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context_data['form'].fields['username'].initial)

    def test_get_signup_view_with_username(self):
        resp = self.client.get(self.url + "?username=test")
        self.assertEqual(
            resp.context_data['form'].fields['username'].initial, 'test'
        )


class DisclaimerModelTests(TestCase):

    def test_online_disclaimer_str(self,):
        user = mommy.make(User, username='testuser')
        field = OnlineDisclaimer._meta.get_field('date')
        mock_now = lambda: datetime(2015, 2, 10, 19, 0, tzinfo=timezone.utc)
        with patch.object(field, 'default', new=mock_now):
            disclaimer = mommy.make(OnlineDisclaimer, user=user)
            self.assertEqual(str(disclaimer), 'testuser - 10 Feb 2015, 19:00')

    def test_default_terms_set_on_new_online_disclaimer(self):
        disclaimer = mommy.make(
            OnlineDisclaimer, disclaimer_terms="foo", over_18_statement="bar",
            medical_treatment_terms="foobar"
        )
        self.assertEqual(disclaimer.disclaimer_terms, DISCLAIMER_TERMS)
        self.assertEqual(disclaimer.medical_treatment_terms, MEDICAL_TREATMENT_TERMS)
        self.assertEqual(disclaimer.over_18_statement, OVER_18_TERMS)

    def test_cannot_update_terms_after_first_save(self):
        disclaimer = mommy.make(OnlineDisclaimer)
        self.assertEqual(disclaimer.disclaimer_terms, DISCLAIMER_TERMS)
        self.assertEqual(disclaimer.medical_treatment_terms, MEDICAL_TREATMENT_TERMS)
        self.assertEqual(disclaimer.over_18_statement, OVER_18_TERMS)

        with self.assertRaises(ValueError):
            disclaimer.disclaimer_terms = 'foo'
            disclaimer.save()

        with self.assertRaises(ValueError):
            disclaimer.medical_treatment_terms = 'foo'
            disclaimer.save()

        with self.assertRaises(ValueError):
            disclaimer.over_18_statement = 'foo'
            disclaimer.save()


class DisclaimerCreateViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(DisclaimerCreateViewTests, cls).setUpTestData()
        cls.url = reverse('accounts:disclaimer_form')

    def setUp(self):
        self.user_no_disclaimer = User.objects.create_user(
            username='user_no_disc', password='password'
        )

        self.form_data = {
            'name': 'test', 'gender': 'female',
            'dob': '01 Jan 1990', 'address': '1 test st',
            'postcode': 'TEST1', 'home_phone': '123445', 'mobile_phone': '124566',
            'emergency_contact1_name': 'test1',
            'emergency_contact1_relationship': 'mother',
            'emergency_contact1_phone': '4547',
            'emergency_contact2_name': 'test2',
            'emergency_contact2_relationship': 'father',
            'emergency_contact2_phone': '34657',
            'medical_conditions': False, 'medical_conditions_details': '',
            'joint_problems': False, 'joint_problems_details': '',
            'allergies': False, 'allergies_details': '',
            'medical_treatment_permission': True,
            'terms_accepted': True,
            'age_over_18_confirmed': True,
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
            "You have already completed a disclaimer.",
            str(resp.rendered_content)
        )
        self.assertNotIn("Submit", str(resp.rendered_content))

        resp = self._get_response(self.user_no_disclaimer)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(
            "You have already completed a disclaimer.",
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
            "You have already completed a disclaimer.",
            str(resp.rendered_content)
        )
        self.assertNotIn("Submit", str(resp.rendered_content))

        # posting same data again redirects to form
        resp = self.client.post(self.url, self.form_data)
        self.assertEqual(resp.status_code, 302)
        # no new disclaimer created
        self.assertEqual(OnlineDisclaimer.objects.count(), 2)

    def test_message_shown_if_no_usable_password(self):
        user = mommy.make(User)
        user.set_unusable_password()
        user.save()

        resp = self._get_response(user)
        self.assertIn(
            "You need to set a password on your account in order to complete "
            "the disclaimer.",
            resp.rendered_content
        )

    def test_cannot_complete_disclaimer_without_usable_password(self):
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)
        user = mommy.make(User)
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
        resp = self.client.get(reverse('accounts:data_protection'))
        self.assertEqual(resp.status_code, 200)


@override_settings(LOG_FOLDER=os.path.dirname(__file__))
class ExportDisclaimersTests(TestCase):

    def setUp(self):
        mommy.make(OnlineDisclaimer, _quantity=10)

    def test_export_disclaimers_creates_default_bu_file(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'disclaimers_bu.csv')
        self.assertFalse(os.path.exists(bu_file))
        management.call_command('export_disclaimers')
        self.assertTrue(os.path.exists(bu_file))
        os.unlink(bu_file)

    def test_export_disclaimers_writes_correct_number_of_rows(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'disclaimers_bu.csv')
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
        mommy.make(OnlineDisclaimer, _quantity=10)

    def test_export_disclaimers_creates_default_bu_file(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'disclaimers.bu')
        self.assertFalse(os.path.exists(bu_file))
        management.call_command('export_encrypted_disclaimers')
        self.assertTrue(os.path.exists(bu_file))
        os.unlink(bu_file)

    def test_export_disclaimers_sends_email(self):
        bu_file = os.path.join(settings.LOG_FOLDER, 'disclaimers.bu')
        management.call_command('export_encrypted_disclaimers')

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [settings.SUPPORT_EMAIL])

        os.unlink(bu_file)

    @patch.object(EmailMessage, 'send')
    def test_email_errors(self, mock_send):
        mock_send.side_effect = Exception('Error sending mail')
        bu_file = os.path.join(settings.LOG_FOLDER, 'disclaimers.bu')

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
            os.path.dirname(__file__), 'test_data/test_disclaimers_backup.csv'
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
            mommy.make(User, username=username)
        self.assertFalse(OnlineDisclaimer.objects.exists())
        management.call_command('import_disclaimer_data', file=self.bu_file)
        self.assertEqual(OnlineDisclaimer.objects.count(), 3)

    def test_import_disclaimers_existing_data(self):
        import_disclaimer_data_logger.warning = Mock()
        import_disclaimer_data_logger.info = Mock()

        # if disclaimer already exists for a user, it isn't imported
        for username in ['test_1', 'test_2']:
            mommy.make(User, username=username)
        test_3 = mommy.make(User, username='test_3')
        mommy.make(
            OnlineDisclaimer, user=test_3, name='Donald Duck')

        self.assertEqual(OnlineDisclaimer.objects.count(), 1)
        management.call_command('import_disclaimer_data', file=self.bu_file)
        self.assertEqual(OnlineDisclaimer.objects.count(), 3)

        # data has not been overwritten
        disclaimer = OnlineDisclaimer.objects.get(user=test_3)
        self.assertEqual(disclaimer.name, 'Donald Duck')

        self.assertEqual(import_disclaimer_data_logger.warning.call_count, 1)
        self.assertEqual(import_disclaimer_data_logger.info.call_count, 2)

        self.assertIn(
            "Disclaimer for test_1 imported from backup.",
            str(import_disclaimer_data_logger.info.call_args_list[0])
        )
        self.assertIn(
            "Disclaimer for test_2 imported from backup.",
            str(import_disclaimer_data_logger.info.call_args_list[1])
        )
        self.assertIn(
            "Disclaimer for test_3 already exists and has not been "
            "overwritten with backup data. Dates in db and back up DO NOT "
            "match",
            str(import_disclaimer_data_logger.warning.call_args_list[0])
        )

    def test_import_disclaimers_existing_data_matching_dates(self):
        import_disclaimer_data_logger.warning = Mock()
        import_disclaimer_data_logger.info = Mock()

        test_1 = mommy.make(User, username='test_1')
        test_2 = mommy.make(User, username='test_2')
        test_3 = mommy.make(User, username='test_3')
        mommy.make(
            OnlineDisclaimer, user=test_2,
            date=datetime(2015, 1, 15, 15, 43, 19, 747445, tzinfo=timezone.utc),
            date_updated=datetime(
                2016, 1, 6, 15, 9, 16, 920219, tzinfo=timezone.utc
            )
        ),
        mommy.make(
            OnlineDisclaimer, user=test_3,
            date=datetime(2016, 2, 18, 16, 9, 16, 920219, tzinfo=timezone.utc),
        )

        self.assertEqual(OnlineDisclaimer.objects.count(), 2)
        management.call_command('import_disclaimer_data', file=self.bu_file)
        self.assertEqual(OnlineDisclaimer.objects.count(), 3)

        self.assertEqual(import_disclaimer_data_logger.warning.call_count, 2)
        self.assertEqual(import_disclaimer_data_logger.info.call_count, 1)

        self.assertIn(
            "Disclaimer for test_1 imported from backup.",
            str(import_disclaimer_data_logger.info.call_args_list[0])
        )
        self.assertIn(
            "Disclaimer for test_2 already exists and has not been "
            "overwritten with backup data. Dates in db and back up "
            "match",
            str(import_disclaimer_data_logger.warning.call_args_list[0])
        )
        self.assertIn(
            "Disclaimer for test_3 already exists and has not been "
            "overwritten with backup data. Dates in db and back up "
            "match",
            str(import_disclaimer_data_logger.warning.call_args_list[1])
        )

    def test_imported_data_is_correct(self):
        test_1 = mommy.make(User, username='test_1')
        management.call_command('import_disclaimer_data', file=self.bu_file)
        test_1_disclaimer = OnlineDisclaimer.objects.get(user=test_1)

        self.assertEqual(test_1_disclaimer.name, 'Test User1')
        self.assertEqual(
            test_1_disclaimer.date,
            datetime(2015, 12, 18, 15, 32, 7, 191781, tzinfo=timezone.utc)
        )
        self.assertEqual(test_1_disclaimer.dob, date(1991, 11, 21))
        self.assertEqual(test_1_disclaimer.address, '11 Test Road')
        self.assertEqual(test_1_disclaimer.postcode, 'TS6 8JT')
        self.assertEqual(test_1_disclaimer.home_phone, '12345667')
        self.assertEqual(test_1_disclaimer.mobile_phone, '2423223423')
        self.assertEqual(test_1_disclaimer.emergency_contact1_name, 'Test1 Contact1')
        self.assertEqual(
            test_1_disclaimer.emergency_contact1_relationship, 'Partner'
        )
        self.assertEqual(
            test_1_disclaimer.emergency_contact1_phone, '8782347239'
        )
        self.assertEqual(test_1_disclaimer.emergency_contact2_name, 'Test2 Contact1')
        self.assertEqual(
            test_1_disclaimer.emergency_contact2_relationship, 'Father'
        )
        self.assertEqual(
            test_1_disclaimer.emergency_contact2_phone, '71684362378'
        )
        self.assertFalse(test_1_disclaimer.medical_conditions)
        self.assertEqual(test_1_disclaimer.medical_conditions_details, '')
        self.assertTrue(test_1_disclaimer.joint_problems)
        self.assertEqual(test_1_disclaimer.joint_problems_details, 'knee problems')
        self.assertFalse(test_1_disclaimer.allergies)
        self.assertEqual(test_1_disclaimer.allergies_details, '')
        self.assertIsNotNone(test_1_disclaimer.medical_treatment_terms)
        self.assertTrue(test_1_disclaimer.medical_treatment_permission)
        self.assertIsNotNone(test_1_disclaimer.disclaimer_terms)
        self.assertTrue(test_1_disclaimer.terms_accepted)
        self.assertIsNotNone(test_1_disclaimer.over_18_statement)
        self.assertTrue(test_1_disclaimer.age_over_18_confirmed)


class MailingListSubscribeViewTests(TestSetupMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(MailingListSubscribeViewTests, cls).setUpTestData()
        cls.subscribed = mommy.make(Group, name='subscribed')
        cls.url = reverse('accounts:subscribe')

    def test_login_required(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            resp.url, reverse('login') + '?next=/accounts/mailing-list/'
        )

        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_get_shows_correct_subscription_status(self):
        self.client.login(username=self.user.username, password='test')
        resp = self.client.get(self.url)
        self.assertIn(
            "You are not currently subscribed to the mailing list.",
            resp.rendered_content
        )

        self.subscribed.user_set.add(self.user)
        resp = self.client.get(self.url)
        self.assertIn(
            "You are currently subscribed to the mailing list.  "
            "Please click below if you would like to unsubscribe.",
            resp.rendered_content
        )

    def test_can_change_subscription(self):
        self.subscribed = Group.objects.get(name='subscribed')
        self.client.login(username=self.user.username, password='test')
        self.assertNotIn(self.subscribed, self.user.groups.all())

        self.client.post(self.url, {'subscribe': 'Subscribe'})
        self.assertIn(self.subscribed, self.user.groups.all())

        self.client.post(self.url, {'unsubscribe': 'Unsubscribe'})
        self.assertNotIn(self.subscribed, self.user.groups.all())
