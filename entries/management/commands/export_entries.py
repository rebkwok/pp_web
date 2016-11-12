import csv
import logging
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail.message import EmailMessage
from django.utils.encoding import smart_str

from entries.models import Entry, CATEGORY_CHOICES_DICT


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Export entries to csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            help='File path of output file; if not provided, '
                 'will be stored in current wd as "submitted_<category>.csv"'
        )
        parser.add_argument(
            'category',
            choices=CATEGORY_CHOICES_DICT.keys(), help='Category to export'
        )
        parser.add_argument(
            '--save', action='store_true',
            help='Save the exported file.  If not included, file will be '
                 'emailed to support email and then deleted.'
        )

    def handle(self, *args, **options):
        category = options.get('category')
        outputfile = options.get('file')
        save = options.get('save')

        if not outputfile:
            outputfile = os.path.join(
                os.getcwd(),
                'submitted_{}.csv'.format(
                    CATEGORY_CHOICES_DICT[category].lower()
                )
            )

        entries = Entry.objects.filter(
            category=category, entry_year=settings.CURRENT_ENTRY_YEAR,
            status='submitted', withdrawn=False, video_entry_paid=True
        )
        with open(outputfile, 'wt') as out:
            wr = csv.writer(out)
            header_row = [
                smart_str(u"ID"),
                smart_str(u"Name"),
                smart_str(u"Stage Name"),
                smart_str(u"Category"),
                smart_str(u"Status"),
                smart_str(u"Video URL"),
            ]
            if category == 'DOU':
                header_row.insert(3, smart_str(u"Doubles Partner"))
            wr.writerow(header_row)

            for obj in entries:
                entry_data = [
                    smart_str(obj.pk),
                    smart_str(' '.join([obj.user.first_name, obj.user.last_name])),
                    smart_str(obj.stage_name),
                    smart_str(CATEGORY_CHOICES_DICT[obj.category]),
                    smart_str(obj.status),
                    smart_str(obj.video_url),
                    smart_str('Yes' if obj.video_entry_paid else 'No'),
                ]
                if category == 'DOU':
                    entry_data.insert(3, smart_str(obj.partner_name))
                wr.writerow(entry_data)

        with open(outputfile, 'rb') as file:
            filename = os.path.split(outputfile)[1]
            msg = EmailMessage(
                '{} submitted entries for {}'.format(
                    settings.ACCOUNT_EMAIL_SUBJECT_PREFIX,
                    CATEGORY_CHOICES_DICT[category]
                ),
                'Submitted entry data attached. '
                '{} entr{}.'.format(
                    entries.count(), 'y' if entries.count() == 1 else 'ies'),
                settings.DEFAULT_FROM_EMAIL,
                to=[settings.SUPPORT_EMAIL],
                attachments=[(filename, file.read(), 'bytes/bytes')]
            )
            msg.send(fail_silently=True)

        if not save:
            os.unlink(outputfile)
            self.stdout.write(
                '{} entry records written to {}; file deleted'.format(
                    entries.count(), outputfile
                )
            )

        else:
            self.stdout.write(
                '{} entry records written to {}'.format(
                    entries.count(), outputfile
                )
            )
