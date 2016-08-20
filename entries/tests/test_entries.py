from model_mommy import mommy

from django.test import TestCase
from django.core.urlresolvers import reverse

from .helpers import TestSetupLoginRequiredMixin
from ..models import Entry


class EntryListViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryListViewTests, cls).setUpTestData()
        cls.url = reverse('entries:user_entries')


class EntryCreateViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryCreateViewTests, cls).setUpTestData()
        cls.url = reverse('entries:create_entry')


class EntryUpdateViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryUpdateViewTests, cls).setUpTestData()
        entry = mommy.make(Entry, user=cls.user)
        cls.url = reverse('entries:edit_entry', args=(entry.id,))


class EntryDeleteViewTests(TestSetupLoginRequiredMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(EntryDeleteViewTests, cls).setUpTestData()
        entry = mommy.make(Entry, user=cls.user)
        cls.url = reverse('entries:edit_entry', args=(entry.id,))