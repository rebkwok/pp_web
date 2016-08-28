import csv
import logging
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail.message import EmailMessage
from django.utils.encoding import smart_str

from simplecrypt import encrypt

from activitylog.models import ActivityLog
from accounts.models import OnlineDisclaimer

logger = logging.getLogger(__name__)

PASSWORD = os.environ.get('SIMPLECRYPT_PASSWORD')

class Command(BaseCommand):
    help = 'Encrypt and export disclaimers data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=os.path.join(settings.LOG_FOLDER, 'waivers.bu'),
            help='File path of output file; if not provided, '
                 'will be stored in log folder as "disclaimers.bu"'
        )

    def handle(self, *args, **options):
        outputfile = options.get('file')

        output_text = []

        output_text.append(
            '@@@@@'.join(
                [
                    smart_str(u"ID"),
                    smart_str(u"User"),
                    smart_str(u"Date"),
                    smart_str(u"Date Updated"),
                    smart_str(u"Emergency Contact: Name"),
                    smart_str(u"Emergency Contact: Relationship"),
                    smart_str(u"Emergency Contact: Phone"),
                    smart_str(u"Waiver Terms"),
                    smart_str(u"Waiver Terms Accepted"),
                ]
            )
        )

        for obj in OnlineDisclaimer.objects.all():
            output_text.append(
                '@@@@@'.join(
                    [
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
                    ]
                )
            )

        output_str = '&&&&&'.join(output_text)

        with open(outputfile, 'wb') as out:
            out.write(encrypt(PASSWORD, output_str))

        with open(outputfile, 'rb') as file:
            filename = os.path.split(outputfile)[1]
            try:
                msg = EmailMessage(
                    '{} waiver backup'.format(
                        settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
                    ),
                    'Encrypted waiver back up file attached. '
                    '{} records.'.format(OnlineDisclaimer.objects.count()),
                    settings.DEFAULT_FROM_EMAIL,
                    to=[settings.SUPPORT_EMAIL],
                    attachments=[(filename, file.read(), 'bytes/bytes')]
                )
                msg.send(fail_silently=False)
            except:
                pass

        self.stdout.write(
            '{} waiver records encrypted and written to {}'.format(
                OnlineDisclaimer.objects.count(), outputfile
            )
        )

        logger.info(
            '{} waiver records encrypted and backed up'.format(
                OnlineDisclaimer.objects.count()
            )
        )
        ActivityLog.objects.create(
            log='{} disclaimer records encrypted and backed up'.format(
                OnlineDisclaimer.objects.count()
            )
        )
