import csv
import logging
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.encoding import smart_str

from accounts.models import OnlineDisclaimer


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Export waiver data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=os.path.join(settings.LOG_FOLDER, 'waivers_bu.csv'),
            help='File path of output file; if not provided, '
                 'will be stored in log folder as "waivers_bu.csv"'
        )

    def handle(self, *args, **options):

        outputfile = options.get('file')

        with open(outputfile, 'wt') as out:
            wr = csv.writer(out)

            wr.writerow([
                smart_str(u"ID"),
                smart_str(u"User"),
                smart_str(u"Date"),
                smart_str(u"Date Updated"),
                smart_str(u"Emergency Contact: Name"),
                smart_str(u"Emergency Contact: Relationship"),
                smart_str(u"Emergency Contact: Phone"),
                smart_str(u"Waiver Terms"),
                smart_str(u"Waiver Terms Accepted"),
            ])
            for obj in OnlineDisclaimer.objects.all():
                wr.writerow([
                    smart_str(obj.pk),
                    smart_str(obj.user),
                    smart_str(obj.date.strftime('%Y-%m-%d %H:%M:%S:%f %z')),
                    smart_str(obj.date_updated.strftime(
                        '%Y-%m-%d %H:%M:%S:%f %z') if obj.date_updated else ''
                    ),
                    smart_str(obj.emergency_contact_name),
                    smart_str(obj.emergency_contact_relationship),
                    smart_str(obj.emergency_contact_phone),
                    smart_str(obj.waiver_terms),
                    smart_str('Yes' if obj.terms_accepted else 'No'),
                ])

        self.stdout.write(
            '{} waiver records written to {}'.format(
                OnlineDisclaimer.objects.count(), outputfile
            )
        )