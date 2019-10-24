import os
import xlrd
from datetime import datetime
from model_bakery import baker

from django.contrib.auth.models import Group, User
from django.core import management
from django.core.cache import cache
from django.urls import reverse
from django.db.models import Q
from django.test import TestCase
from django.utils import timezone

from accounts.models import OnlineDisclaimer
from activitylog.models import ActivityLog
from .helpers import format_content, TestSetupStaffLoginRequiredMixin
from ..utils import int_str, chaffify
from ..views.user_views import NAME_FILTERS


class ActivityLogListViewTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(ActivityLogListViewTests, cls).setUpTestData()
        cls.url = reverse('ppadmin:activitylog')

    def setUp(self):
        super(ActivityLogListViewTests, self).setUp()
        # 8 logs
        # 2 logs when self.user, self.staff_user are created in setUp
        # 1 log when user's disclaimer created
        # 3 with log messages to test search text
        # 2 with fixed dates to test search date
        baker.make(ActivityLog, log='Test log message')
        baker.make(ActivityLog, log='Test log message1 One')
        baker.make(ActivityLog, log='Test log message2 Two')
        baker.make(
            ActivityLog,
            timestamp=datetime(2015, 1, 1, 16, 0, tzinfo=timezone.utc),
            log='Log with test date'
        )
        baker.make(
            ActivityLog,
            timestamp=datetime(2015, 1, 1, 4, 0, tzinfo=timezone.utc),
            log='Log with test date for search'
    )

    def test_search_text(self):
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search': 'message1'}
        )
        self.assertEqual(len(resp.context_data['logs']), 1)

        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search': 'message'})
        self.assertEqual(len(resp.context_data['logs']), 3)

    def test_search_is_case_insensitive(self):
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search': 'Message'})
        self.assertEqual(len(resp.context_data['logs']), 3)

    def test_search_date(self):
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search_date': '01-Jan-2015'
            }
        )
        self.assertEqual(len(resp.context_data['logs']), 2)

    def test_invalid_search_date_format(self):
        """
        invalid search date returns all results and a message
        """
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search_date': '01-34-2015'}
        )
        self.assertEqual(len(resp.context_data['logs']), 8)

    def test_search_date_and_text(self):
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search_date': '01-Jan-2015',
            'search': 'test date for search'}
        )
        self.assertEqual(len(resp.context_data['logs']), 1)

    def test_search_multiple_terms(self):
        """
        Search with multiple terms returns only logs that contain all terms
        """
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search': 'Message'})
        self.assertEqual(len(resp.context_data['logs']), 3)

        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search': 'Message One'})
        self.assertEqual(len(resp.context_data['logs']), 1)

        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search': 'test one'})
        self.assertEqual(len(resp.context_data['logs']), 1)

    def test_reset(self):
        """
        Test that reset button resets the search text and date and excludes
        empty cron job messages
        """
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {
            'search_submitted': 'Search',
            'search_date': '01-Jan-2015',
            'search': 'test date for search'
            }
        )
        self.assertEqual(len(resp.context_data['logs']), 1)

        resp = self.client.get(self.url, {
            'search_date': '01-Jan-2015',
            'search': 'test date for search',
            'reset': 'Reset'
            }
        )
        self.assertEqual(len(resp.context_data['logs']), 8)

    def test_empty_cron_job_logs_filtered_by_default(self):
        # Make an empty job log
        baker.make(
            ActivityLog,
            timestamp=datetime(2015, 1, 1, 4, 0, tzinfo=timezone.utc),
            log='CRON: Auto warn/withdraw selected unconfirmed/unpaid run: '
                'no action required',

        )
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(ActivityLog.objects.count(), 9)
        self.assertEqual(len(resp.context_data['logs']), 8)

    def test_show_empty_cron_job_logs(self):
        # Make an empty job log
        baker.make(
            ActivityLog,
            timestamp=datetime(2015, 1, 1, 4, 0, tzinfo=timezone.utc),
            log='CRON: Auto warn/withdraw selected unconfirmed/unpaid run: '
                'no action required',

        )
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url, {'search_submitted': 'Search'})
        self.assertEqual(ActivityLog.objects.count(), 9)
        self.assertEqual(len(resp.context_data['logs']), 9)


class UserListViewTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(UserListViewTests, cls).setUpTestData()
        cls.url = reverse('ppadmin:users')

    def test_all_users_are_displayed(self):
        baker.make(User, _quantity=6)
        # 8 users total, incl self.user, self.staff_user
        self.assertEqual(User.objects.count(), 8)
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertEqual(
            sorted(resp.context_data['users'].values_list('id')),
            sorted(User.objects.values_list('id'))
        )

    def test_abbreviations_for_long_username(self):
        """
        Usernames > 15 characters are split to 2 lines
        """
        baker.make(User, username='test123456789101112')
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertIn('test12345678-</br>9101112', resp.rendered_content)

    def test_abbreviations_for_long_names(self):
        """
        Names > 18 characters are split to 2 lines; names with hyphens are
        split on the first hyphen
        """
        baker.make(
            User,
            first_name='namewithmorethan18characters',
            last_name='name-with-three-hyphens'
        )
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertIn(
            'namewithmoretha-</br>n18characters', resp.rendered_content
        )
        self.assertIn('name-</br>with-three-hyphens', resp.rendered_content)

    def test_abbreviations_for_long_email(self):
        """
        Email > 25 characters is truncated
        """
        baker.make(User, email='test12345678@longemail.com')
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.get(self.url)
        self.assertIn('test12345678@longemail...', resp.rendered_content)

    def test_user_search(self):
        self.client.login(username=self.staff_user.username, password='test')

        baker.make(
            User, username='FooBar', first_name='Foo', last_name='Bar'
        )
        baker.make(
            User, username='Testing1', first_name='Foo', last_name='Bar'
        )
        baker.make(
            User, username='Testing2', first_name='Boo', last_name='Bar'
        )

        resp = self.client.get(
            self.url, {'search_submitted': 'Search', 'search': 'Foo'}
        )
        self.assertEqual(len(resp.context_data['users']), 2)

        resp = self.client.get(
            self.url, {'search_submitted': 'Search', 'search': 'FooBar'}
        )
        self.assertEqual(len(resp.context_data['users']), 1)

        resp = self.client.get(
            self.url, {'search_submitted': 'Search', 'search': 'testing'}
        )
        self.assertEqual(len(resp.context_data['users']), 2)

        self.assertEqual(User.objects.count(), 5)  # 5 total, incl setup users
        resp = self.client.get(
            self.url, {'reset': 'Reset', 'search': 'Foo'}
        )
        self.assertEqual(len(resp.context_data['users']), 5)

    def test_user_filter(self):
        self.client.login(username=self.staff_user.username, password='test')
        baker.make(
            User, username='FooBar', first_name='AUser', last_name='Bar'
        )
        baker.make(
            User, username='Testing1', first_name='aUser', last_name='Bar'
        )
        baker.make(
            User, username='Testing2', first_name='BUser', last_name='Bar'
        )

        resp = self.client.get(self.url, {'filter': 'A'})
        self.assertEqual(len(resp.context_data['users']), 2)
        for user in resp.context_data['users']:
            self.assertTrue(user.first_name.upper().startswith('A'))

         # 5 users total, incl self.user, self.staff_user
        self.assertEqual(User.objects.count(), 5)
        resp = self.client.get(self.url, {'filter': 'All'})
        self.assertEqual(len(resp.context_data['users']), 5)

    def test_user_filter_and_search(self):
        self.client.login(username=self.staff_user.username, password='test')
        baker.make(User, username='FooBar', first_name='AUser', last_name='Bar')
        baker.make(
            User, username='Testing1', first_name='aUser', last_name='Bar'
        )
        baker.make(
            User, username='Testing2', first_name='BUser', last_name='Bar'
        )

        resp = self.client.get(self.url, {'filter': 'A', 'search': 'Test'})
        self.assertEqual(len(resp.context_data['users']), 1)
        found_user = resp.context_data['users'][0]
        self.assertEqual(found_user.first_name, "aUser")

    def test_filter_options(self):
        self.client.login(username=self.staff_user.username, password='test')
        # make a user with first name starting with all options
        for option in NAME_FILTERS:
            baker.make(User, first_name='{}Usr'.format(option))
        # delete any starting with Z
        User.objects.filter(first_name__istartswith='Z').delete()
        resp = self.client.get(self.url)
        filter_options = resp.context_data['filter_options']
        for opt in filter_options:
            if opt['value'] == 'Z':
                self.assertFalse(opt['available'])
            else:
                self.assertTrue(opt['available'])

        users = User.objects.filter(
            Q(first_name__istartswith='A') |
            Q(first_name__istartswith='B') |
            Q(first_name__istartswith='C')
        )
        for user in users:
            user.username = "{}_testfoo".format(user.first_name)
            user.save()

        resp = self.client.get(
            self.url, {'search': 'testfoo', 'search_submitted': 'Search'}
        )
        filter_options = resp.context_data['filter_options']
        for opt in filter_options:
            if opt['value'] in ['All', 'A', 'B', 'C']:
                self.assertTrue(opt['available'])
            else:
                self.assertFalse(opt['available'])


class UserDisclaimerViewTests(TestSetupStaffLoginRequiredMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super(UserDisclaimerViewTests, cls).setUpTestData()
        cls.url = reverse(
            'ppadmin:user_disclaimer',
            args=[int_str(chaffify(cls.user.id))]
        )

    def test_get_with_invalid_encoded_user_id(self):
        """
        Invalid user id raises Value error when decoding; return 404
        """
        self.client.login(username=self.staff_user.username, password='test')
        resp = self.client.post(
            reverse('ppadmin:user_disclaimer', args=['foo'])
        )
        self.assertEqual(resp.status_code, 404)


class DisclaimerUpdateViewTests(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(DisclaimerUpdateViewTests, cls).setUpTestData()
        cls.url = reverse(
            'ppadmin:update_user_disclaimer',
            args=[int_str(chaffify(cls.user.id))]
        )

    def setUp(self):
        super(DisclaimerUpdateViewTests, self).setUp()
        self.user.set_password('password')
        self.user.save()
        # remove existing disclaimer for self.user
        OnlineDisclaimer.objects.all().delete()
        self.disclaimer = baker.make(
            OnlineDisclaimer, user=self.user,
            terms_accepted=True
        )
        self.post_data = {
            'id': self.disclaimer.id,
            'emergency_contact_name': 'Foo',
            'emergency_contact_relationship': 'mother',
            'emergency_contact_phone': '4547',
            'terms_accepted': True,
            'password': 'password'
        }

    def test_user_password_required_to_update_disclaimer(self):
        self.assertNotEqual(self.disclaimer.emergency_contact_name, 'Foo')
        self.client.login(username=self.staff_user.username, password='test')
        self.client.post(self.url, self.post_data)
        self.disclaimer.refresh_from_db()
        self.assertEqual(self.disclaimer.emergency_contact_name, 'Foo')

    def test_user_password_incorrect(self):
        self.post_data['password'] = 'password1'
        self.assertTrue(
            self.client.login(username=self.staff_user.username, password='test')
        )
        resp = self.client.post(self.url, self.post_data, follow=True)
        self.assertIn(
            'Password is incorrect', format_content(resp.rendered_content)
        )

    def test_update_dislaimer_sets_date_updated(self):
        self.assertIsNone(self.disclaimer.date_updated)
        self.client.login(username=self.staff_user.username, password='test')
        self.client.post(self.url, self.post_data)

        self.disclaimer.refresh_from_db()
        self.assertIsNotNone(self.disclaimer.date_updated)

    def test_no_changes_made(self):
        post_data = {
            'id': self.disclaimer.id,
            'emergency_contact_name': self.disclaimer.emergency_contact_name,
            'emergency_contact_relationship': self.disclaimer.emergency_contact_relationship,
            'emergency_contact_phone': self.disclaimer.emergency_contact_phone,
            'terms_accepted': True,
            'password': 'password'
        }

        self.assertTrue(
            self.client.login(username=self.staff_user.username, password='test')
        )
        resp = self.client.post(self.url, post_data, follow=True)
        self.assertIn(
            'No changes made', format_content(resp.rendered_content)
        )


class DisclaimerDeleteViewTests(TestSetupStaffLoginRequiredMixin,
                                TestCase):
    @classmethod
    def setUpTestData(cls):
        super(DisclaimerDeleteViewTests, cls).setUpTestData()
        cls.url = reverse(
            'ppadmin:delete_user_disclaimer',
            args=[int_str(chaffify(cls.user.id))]
        )

    def test_delete_disclaimer(self):
        self.assertEqual(OnlineDisclaimer.objects.count(), 1)
        encoded_user_id = int_str(chaffify(self.user.id))
        delete_url = reverse(
            'ppadmin:delete_user_disclaimer', args=[encoded_user_id]
        )
        self.client.login(username=self.staff_user.username, password='test')
        self.client.delete(self.url)
        self.assertEqual(OnlineDisclaimer.objects.count(), 0)


class ExportEntriesView(TestSetupStaffLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(ExportEntriesView, cls).setUpTestData()
        cls.url = reverse('ppadmin:export_entries')

    def test_no_entries(self):
        self.client.login(username=self.staff_user.username, password='test')
        form_data = {
            'category': 'BEG', 'status': 'in_progress',
            'include': ['name']
        }
        # submitting from dropdown change
        resp = self.client.post(self.url, data=form_data)
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'__all__': ['No entries match selected category/status.']}
        )

        # submitting from export button
        form_data.update({'export': True})
        resp = self.client.post(self.url, data=form_data)
        form = resp.context_data['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'__all__': ['No entries match selected category/status.']}
        )

    def test_submit_all_categories(self):
        self.client.login(username=self.staff_user.username, password='test')
        management.call_command('setup_test_data')
        form_data = {
            'category': 'all', 'status': 'all',
            'include': ['name']
        }
        # submitting from dropdown change
        resp = self.client.post(self.url, data=form_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual( resp['Content-Type'], 'text/html; charset=utf-8')

        # submitting from export button
        form_data.update({'export': True})
        resp = self.client.post(self.url, data=form_data)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/ms-excel')
        self.assertEqual(
            resp['Content-Disposition'],
            'attachment; filename=competitors_all.xls'
        )

    def test_file_content(self):
        self.client.login(username=self.staff_user.username, password='test')
        management.call_command('setup_test_data')
        form_data = {
            'category': 'all', 'status': 'all',
            'include': ['name', 'pole_school', 'category'],
            'export': True
        }
        resp = self.client.post(self.url, data=form_data)

        # test file content
        # Test data:
        #  - BEG: 1 in progress, 2 submitted
        #  - INT: 1 in progress, 2 submitted
        #  - ADV: 1 in progress
        #  - DOU: 2 submitted
        #  - MEN, PRO: none
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        filename = os.path.join(curr_dir, "temp.xls")

        with open(filename, "wb") as f:
            f.write(resp.content)
        book = xlrd.open_workbook(filename)

        # 4 sheets, one per category
        self.assertEqual(book.nsheets, 4)
        self.assertCountEqual(
            book.sheet_names(),
            ['Advanced', 'Beginner', 'Doubles', 'Intermediate']
        )
        beg = book.sheet_by_name('Beginner')
        int = book.sheet_by_name('Intermediate')
        adv = book.sheet_by_name('Advanced')
        dou = book.sheet_by_name('Doubles')
        self.assertEqual(beg.nrows, 4)  # header row + 3 data rows
        self.assertEqual(int.nrows, 4)
        self.assertEqual(adv.nrows, 2)
        self.assertEqual(dou.nrows, 3)
        self.assertEqual(beg.ncols, 3)  # as specified in 'includes' field
        # Name field is composed of first and last names
        for i in range(0, beg.nrows):
            if i == 0:  # header row
                self.assertEqual(dou.cell_value(rowx=i, colx=0), 'Name')
            else:
                beg_names = ['Sally Test', 'Anna Test', 'Emma Test']
                self.assertIn(beg.cell_value(rowx=i, colx=0), beg_names)

        # For doubles, name field includes partner name
        for i in range(0, dou.nrows):
            if i == 0:  # header row
                self.assertEqual(dou.cell_value(rowx=i, colx=0), 'Name')
            else:
                dou_names = ['Sally Test & Bob Test', 'Ann Test & Anna Test']
                self.assertIn(
                    dou.cell_value(rowx=i, colx=0), dou_names
                )
                # school for doubles shows both partners
                sch_names = [
                    'School 0 (ST) / School 1 (BT)',
                    'School 2 (AT) / School 3 (AT)'
                ]
                self.assertIn(
                    dou.cell_value(rowx=i, colx=1), sch_names
                )

        os.unlink(filename)

    def test_submit_select_categories(self):
        self.client.login(username=self.staff_user.username, password='test')
        management.call_command('setup_test_data')
        form_data = {
            'category': 'DOU', 'status': 'submitted',
            'include': ['name', 'stage_name', 'pole_school']
        }
        # submitting from dropdown change
        resp = self.client.post(self.url, data=form_data)
        self.assertEqual(resp.status_code, 200)

        # submitting from export button
        form_data.update({'export': True})
        resp = self.client.post(self.url, data=form_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/ms-excel')
        self.assertEqual(
            resp['Content-Disposition'],
            'attachment; filename=competitors_doubles.xls'
        )
