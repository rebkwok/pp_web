from model_bakery import  baker

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from allauth.account.models import EmailAddress

from accounts.models import OnlineDisclaimer

from ..forms import EntryCreateUpdateForm, SelectedEntryUpdateForm
from .helpers import TestSetupMixin
from ..models import Entry, VALID_CATEGORIES, CATEGORY_CHOICES_ORDER


@override_settings(
        ENTRIES_OPEN_DATE="01/01/2016",
        ENTRIES_CLOSE_DATE="01/01/2200",
        LATE_CATEGORIES_ENTRIES_CLOSE_DATE="01/02/2200"
    )
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
        baker.make(Entry, user=self.user, category='BEG')
        form = EntryCreateUpdateForm(user=self.user, initial_data={})
        cat = form.fields['category']

        cat_choices = list(VALID_CATEGORIES)
        cat_choices.remove(('BEG', 'Beginner'))
        self.assertEqual(cat.widget.choices, tuple(sorted(cat_choices, key=lambda x: CATEGORY_CHOICES_ORDER[x[0]])))

    def test_category_choices_includes_already_entered_for_updates(self):
        entry = baker.make(Entry, user=self.user)
        form = EntryCreateUpdateForm(
            instance=entry, user=self.user, initial_data={}
        )
        cat = form.fields['category']

        self.assertEqual(cat.widget.choices, tuple(sorted(VALID_CATEGORIES, key=lambda x: CATEGORY_CHOICES_ORDER[x[0]])))

    def test_category_hidden_for_submitted(self):
        entry = baker.make(Entry, user=self.user, status='submitted')
        form = EntryCreateUpdateForm(
            instance=entry, user=self.user, initial_data={}
        )
        self.assertEqual(
            form.fields['category'].widget.attrs['class'], 'hide'
        )

    @override_settings(ENTRIES_CLOSE_DATE="01/01/2016")
    def test_video_url_hidden_if_entries_closed(self):
        entry = baker.make(Entry, user=self.user, status='submitted')
        form = EntryCreateUpdateForm(
            instance=entry, user=self.user, initial_data={}
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
        baker.make(EmailAddress, user=self.user, email='other@test.com')
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
        partner = baker.make(
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
        partner = baker.make(
            User, username='partner', email='partner@test.com'
        )
        baker.make(OnlineDisclaimer, user=partner)
        baker.make(Entry, category='DOU', user=partner)

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
        partner = baker.make(
            User, username='partner', email='partner@test.com'
        )
        baker.make(OnlineDisclaimer, user=partner)

        data = {
            'category': 'DOU',
            'video_url': 'http://foo.com',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = EntryCreateUpdateForm(data, user=self.user, initial_data={})
        self.assertTrue(form.is_valid())

    def test_show_doubles(self):
        """
        Show double if existing doubles entry, new entry with doubles in
        initial data or new entry with doubles as first in choices (b/c entries
        already created for other categories)
        """
        entry = baker.make(Entry, user=self.user, category='DOU')
        form = EntryCreateUpdateForm(
            instance=entry, user=self.user, initial_data={}
        )
        self.assertTrue(form.show_doubles)
        entry.category = 'BEG'
        entry.save()
        form = EntryCreateUpdateForm(
            instance=entry, user=self.user, initial_data={}
        )
        self.assertFalse(form.show_doubles)

        user = baker.make(User)
        form = EntryCreateUpdateForm(
            user=user, initial_data={'category': 'DOU'}
        )
        self.assertTrue(form.show_doubles)

        # make entries for all preceding categories in the choices list
        baker.make(Entry, user=user, category='BEG')
        baker.make(Entry, user=user, category='INT')
        baker.make(Entry, user=user, category='ADV')
        baker.make(Entry, user=user, category='PRO')
        baker.make(Entry, user=user, category='SMP')

        form = EntryCreateUpdateForm(user=user, initial_data={})
        self.assertTrue(form.show_doubles)


class SelectedEntryUpdateFormTests(TestSetupMixin, TestCase):

    def setUp(self):
        self.entry = baker.make(Entry, user=self.user, status='selected')

    def test_submit_form_valid(self):
        data = {
            'submitted': 'Submit',
            'song': 'Song title',
            'biography': 'About me'
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
            'song': 'Song title',
            'biography': 'About me',
            'category': 'DOU',
            'submitted': 'Submit'
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'partner_name': ['This field is required.'],
                'partner_email': ['This field is required.'],
            }
        )

    def test_doubles_partner_email_same_as_user(self):
        self.entry.category = 'DOU'
        self.entry.save()
        data = {
            'song': 'Song title',
            'biography': 'About me',
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
        baker.make(EmailAddress, user=self.user, email='other@test.com')
        data = {

            'song': 'Song title',
            'biography': 'About me',
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
            'song': 'Song title',
            'biography': 'About me',
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
        partner = baker.make(
            User, username='partner', email='partner@test.com'
        )
        data = {
            'song': 'Song title',
            'biography': 'About me',
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
        partner = baker.make(
            User, username='partner', email='partner@test.com'
        )
        baker.make(OnlineDisclaimer, user=partner)
        baker.make(Entry, category='DOU', user=partner)

        data = {
            'song': 'Song title',
            'biography': 'About me',
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
        partner = baker.make(
            User, username='partner', email='partner@test.com'
        )
        baker.make(OnlineDisclaimer, user=partner)

        data = {
            'song': 'Song title',
            'biography': 'About me',
            'submitted': 'Submit',
            'partner_name': 'Test user',
            'partner_email': partner.email
        }
        form = form = SelectedEntryUpdateForm(instance=self.entry, data=data)
        self.assertTrue(form.is_valid())
