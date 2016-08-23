from model_mommy import  mommy

from django.test import TestCase

from ..forms import EntryCreateUpdateForm
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
                'biography': ['This field is required'],
            }
        )

        data.update(
            {
                'video_url': 'http://foo.com',
                'biography': 'About me'
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
            'biography': 'About me',
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
            'biography': 'About me',
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
