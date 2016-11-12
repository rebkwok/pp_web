from datetime import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import OnlineDisclaimer, UserProfile

from ...models import Entry


class Command(BaseCommand):
    help = 'setup some test data'

    def handle(self, *args, **options):
        firstnames = ['Sally', 'Bob', 'Ann', 'Anna', 'Emma']
        for i, name in enumerate(firstnames):
            user, _ = User.objects.get_or_create(
                username='test{}{}'.format(name, i), first_name=name,
                last_name="Test", email='{}@test.com'.format(name)
            )
            UserProfile.objects.get_or_create(
                user=user, address='1 Test St', postcode='AB12 3CD',
                phone='123456', dob=datetime(1990, 1, 1)
            )
            OnlineDisclaimer.objects.get_or_create(
                user=user, emergency_contact_name='Test',
                emergency_contact_relationship='partner',
                emergency_contact_phone='123445',
                terms_accepted=True
            )

        users = User.objects.filter(first_name__in=firstnames)

        Entry.objects.get_or_create(
            category='BEG', user=users[0], status='in_progress'
        )
        Entry.objects.get_or_create(
            category='INT', user=users[1], status='in_progress'
        )
        Entry.objects.get_or_create(
            category='INT', user=users[2], status='submitted',
            video_entry_paid=True
        )
        Entry.objects.get_or_create(
            category='INT', user=users[3], status='submitted',
            video_entry_paid=True
        )
        Entry.objects.get_or_create(
            category='ADV', user=users[2], status='in_progress'
        )
        Entry.objects.get_or_create(
            category='BEG', user=users[3], status='submitted',
            video_url='https://www.youtube.com/watch?v=58-atNakMWw'
        )
        Entry.objects.get_or_create(
            category='BEG', user=users[4], status='submitted',
            video_entry_paid=True,
            video_url='https://www.youtube.com/watch?v=0Bmhjf0rKe8'
        )
        Entry.objects.get_or_create(
            category='DOU', user=users[0], status='submitted',
            partner_name='{}'.format(users[1].first_name),
            partner_email=users[1].email,
            video_url='https://www.youtube.com/watch?v=Psv5dmrs3U0'
        )
        Entry.objects.get_or_create(
            category='DOU', user=users[2], status='submitted',
            partner_name='{}'.format(users[3].first_name),
            partner_email=users[3].email,
            video_entry_paid=True,
            video_url='https://www.youtube.com/watch?v=Psv5dmrs3U0'
        )
