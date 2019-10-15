import shortuuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.functional import cached_property
from django.utils import timezone


STATUS_CHOICES = (
    ('in_progress', 'In Progress'),
    ('submitted', 'Submitted'),
    ('selected', 'Selected'),
    ('selected_confirmed', 'Selected - confirmed'),
    ('rejected', 'Rejected')
)
STATUS_CHOICES_DICT = dict(STATUS_CHOICES)

CATEGORY_CHOICES = (
    ('BEG', 'Beginner'),
    ('INT', 'Intermediate'),
    ('ADV', 'Advanced'),
    ('SMP', 'Semi-Pro'),
    ('PRO', 'Professional'),
    ('MEN', 'Mens'),
    ('DOU', 'Doubles'),
)
CATEGORY_CHOICES_DICT = dict(CATEGORY_CHOICES)

LATE_ENTRY_CATEGORY_CHOICES = (
    ('DOU', 'Doubles'),
)

# This is so we can keep/view old entries for old categories, but choose not to display invalid ones on a new entry form
INVALID_CATEGORIES = ['MEN']

VIDEO_ENTRY_FEES = {
    'BEG': 15,
    'INT': 15,
    'ADV': 15,
    'DOU': 15,
    'SMP': 15,
    'PRO': 15,
    'MEN': 15,
}

SELECTED_ENTRY_FEES = {
    'BEG': 15,
    'INT': 15,
    'ADV': 15,
    'DOU': 20,
    'SMP': 15,
    'PRO': 15,
    'MEN': 15,
}

WITHDRAWAL_FEE = 25

YEAR_CHOICES = (
    ('2017', '2017'),
    ('2018', '2018'),
    ('2019', '2019'),
    ('2020', '2020'),
    ('2021', '2021'),
    ('2022', '2022'),
    ('2023', '2023'),
    ('2024', '2024'),
    ('2025', '2025'),
    ('2026', '2026'),
    ('2027', '2027'),
    ('2028', '2028'),
    ('2029', '2029'),
    ('2030', '2030'),
)


class Entry(models.Model):
    entry_ref = models.CharField(max_length=22)
    entry_year = models.CharField(
        choices=YEAR_CHOICES, default=settings.CURRENT_ENTRY_YEAR, max_length=4
    )  # so we can use this system for future comp entries too
    user = models.ForeignKey(User, related_name="entries", on_delete=models.CASCADE)
    stage_name = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(
        choices=CATEGORY_CHOICES, default='BEG', max_length=3
    )
    status = models.CharField(
        choices=STATUS_CHOICES, default='in_progress', max_length=20
    )
    # keep withdrawn as boolean so we can track last status before withdrawing
    withdrawn = models.BooleanField(default=False)

    song = models.CharField(max_length=255, blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, default='')
    biography = models.TextField(
        verbose_name='Short bio',
        help_text='How long have you been poling? Previous titles? Why you '
                  'have entered? Any relevant information about yourself? '
                  'How would you describe your style?',
        blank=True, null=True
    )

    # for doubles entry
    partner_name = models.CharField(
        max_length=255, blank=True, null=True,

    )
    partner_email = models.EmailField(
        blank=True, null=True,
        help_text='Ensure this is the email your doubles partner has used '
                  'for their account. We will use it to ensure registration '
                  'and waiver information has been received for your partner '
                  'also.'
    )

    # payment
    video_entry_paid = models.BooleanField(default=False)
    selected_entry_paid = models.BooleanField(default=False)
    withdrawal_fee_paid = models.BooleanField(default=False)

    date_submitted = models.DateTimeField(null=True, blank=True)

    # selection flags
    notified = models.BooleanField(default=False)
    notified_date = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ('entry_year', 'user', 'category')
        verbose_name_plural = 'entries'

    def __str__(self):
        return "{first} {last} - {ref} - {cat} - {yr} - {status}{wd}".format(
            first=self.user.first_name, last=self.user.last_name,
            ref=self.entry_ref,
            cat=CATEGORY_CHOICES_DICT[self.category],
            yr=self.entry_year,
            status=STATUS_CHOICES_DICT[self.status],
            wd=' (withdrawn)' if self.withdrawn else ''
        )

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.entry_ref = shortuuid.ShortUUID().random(length=22)

        if self.status == 'submitted' and not self.date_submitted:
            self.date_submitted = timezone.now()

        if self.notified and not self.notified_date:
            self.notified_date = timezone.now()

        super(Entry, self).save(
            force_insert, force_update, using, update_fields
        )
