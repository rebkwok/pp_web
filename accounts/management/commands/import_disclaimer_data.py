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
                        log_msg = "Disclaimer for {} already exists and has " \
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
                            name=row[4],
                            dob=datetime.strptime(row[5], '%Y-%m-%d').date(),
                            gender=row[6],
                            address=row[7],
                            postcode=row[8],
                            home_phone=row[9],
                            mobile_phone=row[10],
                            emergency_contact1_name=row[11],
                            emergency_contact1_relationship=row[12],
                            emergency_contact1_phone=row[13],
                            emergency_contact2_name=row[14],
                            emergency_contact2_relationship=row[15],
                            emergency_contact2_phone=row[16],
                            medical_conditions=True
                            if row[17] == "Yes" else False,
                            medical_conditions_details=row[18],
                            joint_problems=True if row[19] == "Yes" else False,
                            joint_problems_details=row[20],
                            allergies=True if row[21] == "Yes" else False,
                            allergies_details=row[22],
                            medical_treatment_terms=row[23],
                            medical_treatment_permission=True
                            if row[24] == "Yes" else False,
                            disclaimer_terms=row[25],
                            terms_accepted=True
                            if row[26] == "Yes" else False,
                            over_18_statement=row[27],
                            age_over_18_confirmed=True
                            if row[28] == "Yes" else False,
                        )
                        log_msg = "Disclaimer for {} imported from " \
                                   "backup.".format(user.username)
                        self.stdout.write(log_msg)
                        logger.info(log_msg)
