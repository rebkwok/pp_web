import csv
from datetime import datetime
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from accounts.models import OnlineDisclaimer


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import disclaimer data from decrypted csv backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            help='File path of input file'
        )

    def handle(self, *args, **options):

        inputfilepath = options.get('file')

        with open(inputfilepath, 'r') as file:
            reader = csv.reader(file)
            # rows = list(reader)

            for i, row in enumerate(reader):
                if i == 0:
                    pass
                else:
                    try:
                        user = User.objects.get(username=row[1])
                    except User.DoesNotExist:
                        self.stdout.write(
                            "Unknown user {} in backup data; data on "
                            "row {} not imported".format(row[1], i)
                        )
                        logger.warning("Unknown user {} in backup data; data on "
                            "row {} not imported".format(row[1], i))
                        continue

                    bu_date_updated = datetime.strptime(
                        row[3], '%Y-%m-%d %H:%M:%S:%f %z'
                    ) if row[3] else None

                    try:
                        disclaimer = OnlineDisclaimer.objects.get(user=user)
                    except OnlineDisclaimer.DoesNotExist:
                        disclaimer = None

                    if disclaimer:
                        if disclaimer.date == datetime.strptime(
                                row[2], '%Y-%m-%d %H:%M:%S:%f %z'
                        ) and disclaimer.date_updated == bu_date_updated:
                            dates_match = True
                        else:
                            dates_match = False
                        log_msg = "Waiver for {} already exists and has " \
                                  "not been overwritten with backup data. " \
                                  "Dates in db and back up {}match.".format(
                                        user.username,
                                        'DO NOT ' if not dates_match else ''
                                    )
                        self.stdout.write(log_msg)
                        logger.warning(log_msg)

                    else:
                        OnlineDisclaimer.objects.create(
                            user=user,
                            date=datetime.strptime(
                                row[2], '%Y-%m-%d %H:%M:%S:%f %z'
                            ),
                            date_updated=bu_date_updated,
                            emergency_contact_name=row[4],
                            emergency_contact_relationship=row[5],
                            emergency_contact_phone=row[6],
                            waiver_terms=row[7],
                            terms_accepted=True
                            if row[8] == "Yes" else False,
                        )
                        log_msg = "Waiver for {} imported from " \
                                   "backup.".format(user.username)
                        self.stdout.write(log_msg)
                        logger.info(log_msg)
