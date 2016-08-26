from model_mommy import  mommy

from django.contrib.auth.models import User
from django.test import TestCase

from allauth.account.models import EmailAddress

from accounts.models import OnlineDisclaimer

from ..forms import EntryCreateUpdateForm, SelectedEntryUpdateForm
from .helpers import TestSetupMixin
from ..models import Entry, CATEGORY_CHOICES


class EntryCreateUpdateFormTests(TestSetupMixin, TestCase):

    def test_save_form_valid(self):
        data = {
            'category': 'BEG',
            'saved': 'Save'
        }

        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertTrue(form.is_valid())

    def test_save_form_valid_video_url(self):
        """
        Video url is set to empty string if not entered on a Save
        """
        data = {
            'category': 'BEG',
            'video_url': 'http://',
            'saved': 'Save'
        }

        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertTrue(form.is_valid())

    def test_submit_form_valid(self):
        data = {
            'category': 'BEG',
            'submitted': 'Submit'
        }

        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'video_url': ['This field is required'],
            }
        )

        data.update(
            {
                'video_url': 'http://foo.com',
            }
        )
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertTrue(form.is_valid())

    def test_submit_form_valid_video_url(self):
        """
        Video url is not set to empty string if not entered on a Save
        """
        data = {
            'category': 'BEG',
            'video_url': 'http://',
            'submitted': 'Submit'
        }

        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['video_url'], ['Enter a valid URL.']
        )

        data.update(video_url='http://foo.com')
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertTrue(form.is_valid())

    def test_submit_doubles_category_form_valid(self):
        """
        Doubles category also required partner fields to submit
        """
        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit'
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_name': ['This field is required'],
                'partner_email': ['This field is required'],
            }
        )

    def test_category_initial(self):
        form = EntryCreateUpdateForm(
            user=self.user, initial_data={'category': 'INT'}
        )
        self.assertEqual(form.initial, {'category': 'INT'})

    def test_category_choices_excludes_already_entered(self):
        mommy.make(Entry, user=self.user, category='BEG')
        form = EntryCreateUpdateForm(user=self.user, initial_data={})
        cat = form.fields['category']

        cat_choices = list(CATEGORY_CHOICES)
        cat_choices.remove(('BEG', 'Beginner'))
        self.assertEqual(cat.widget.choices, cat_choices)

    def test_category_choices_includes_already_entered_for_updates(self):
        entry = mommy.make(Entry, user=self.user)
        form = EntryCreateUpdateForm(
            instance=entry, user=self.user, initial_data={}
        )
        cat = form.fields['category']

        self.assertEqual(cat.widget.choices, list(CATEGORY_CHOICES))

    def test_category_and_video_url_hidden_for_submitted(self):
        entry = mommy.make(Entry, user=self.user, status='submitted')
        form = EntryCreateUpdateForm(
            instance=entry, user=self.user, initial_data={}
        )
        self.assertEqual(
            form.fields['category'].widget.attrs['class'], 'hide'
        )
        self.assertEqual(
            form.fields['video_url'].widget.attrs['class'], 'hide'
        )

    def test_doubles_partner_email_same_as_user(self):
        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': self.user.email
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'This cannot be one of your own registered email addresses'
                ]
            }
        )

    def test_doubles_partner_email_same_as_user_additional_email(self):
        mommy.make(EmailAddress, user=self.user, email='other@test.com')
        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': 'other@test.com'
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'This cannot be one of your own registered email addresses'
                ]
            }
        )

    def test_submit_doubles_partner_not_registered(self):
        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': 'nouser@unknown.com'
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'Partner is not registered'
                ]
            }
        )

    def test_submit_doubles_partner_no_waiver(self):
        partner = mommy.make(
            User, username='partner', email='partner@test.com'
        )
        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'Partner has registered but has not yet completed waiver'
                ]
            }
        )

    def test_submit_doubles_partner_already_entered(self):
        partner = mommy.make(
            User, username='partner', email='partner@test.com'
        )
        mommy.make(OnlineDisclaimer, user=partner)
        mommy.make(Entry, category='DOU', user=partner)

        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'A user with this email address has already entered '
                    'the doubles category'
                ]
            }
        )

    def test_submit_doubles(self):
        partner = mommy.make(
            User, username='partner', email='partner@test.com'
        )
        mommy.make(OnlineDisclaimer, user=partner)

        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertTrue(form.is_valid())


class SelectedEntryUpdateFormTests(TestSetupMixin, TestCase):

    def setUp(self):
        self.entry = mommy.make(Entry, user=self.user, status='selected')

    def test_submit_form_valid(self):
        data = {
            'submitted': 'Submit'
        }

        form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertTrue(form.is_valid())

    def test_submit_doubles_category_form_valid(self):
        """
        Doubles category also required partner fields to submit
        """
        self.entry.category = 'DOU'
        self.entry.save()
        data = {
            'category': 'DOU',
            'submitted': 'Submit'
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_name': ['This field is required'],
                'partner_email': ['This field is required'],
            }
        )

    def test_doubles_partner_email_same_as_user(self):
        self.entry.category = 'DOU'
        self.entry.save()
        data = {
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': self.user.email
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'This cannot be one of your own registered email addresses'
                ]
            }
        )

    def test_doubles_partner_email_same_as_user_additional_email(self):
        self.entry.category = 'DOU'
        self.entry.save()
        mommy.make(EmailAddress, user=self.user, email='other@test.com')
        data = {
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': 'other@test.com'
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'This cannot be one of your own registered email addresses'
                ]
            }
        )

    def test_submit_doubles_partner_not_registered(self):
        self.entry.category = 'DOU'
        self.entry.save()
        data = {
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': 'nouser@unknown.com'
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'Partner is not registered'
                ]
            }
        )

    def test_submit_doubles_partner_no_waiver(self):
        self.entry.category = 'DOU'
        self.entry.save()
        partner = mommy.make(
            User, username='partner', email='partner@test.com'
        )
        data = {
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'Partner has registered but has not yet completed waiver'
                ]
            }
        )

    def test_submit_doubles_partner_already_entered(self):
        self.entry.category = 'DOU'
        self.entry.save()
        partner = mommy.make(
            User, username='partner', email='partner@test.com'
        )
        mommy.make(OnlineDisclaimer, user=partner)
        mommy.make(Entry, category='DOU', user=partner)

        data = {
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_email': [
                    'A user with this email address has already entered '
                    'the doubles category'
                ]
            }
        )

    def test_submit_doubles(self):
        self.entry.category = 'DOU'
        self.entry.save()
        partner = mommy.make(
            User, username='partner', email='partner@test.com'
        )
        mommy.make(OnlineDisclaimer, user=partner)

        data = {
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertTrue(form.is_valid())
