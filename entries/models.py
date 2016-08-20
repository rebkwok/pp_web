import shortuuid

from django.contrib.auth.models import User
from django.db import models
from django.utils.functional import cached_property
from django.utils import timezone


STATUS_CHOICES = (
    ('in_progress', 'In Progress'),
    ('submitted', 'Submitted'),
    ('selected', 'Selected'),
    ('rejected', 'Unsuccessful')
)
STATUS_CHOICES_DICT = dict(STATUS_CHOICES)

CATEGORY_CHOICES = (
    ('BEG', 'Beginner'),
    ('INT', 'Intermediate'),
    ('ADV', 'Advanced'),
    ('DOU', 'Doubles'),
    ('PRO', 'Professional'),
    ('MEN', 'Mens')
)
CATEGORY_CHOICES_DICT = dict(CATEGORY_CHOICES)

ENTRY_FEES = {
    'BEG': 25,
    'INT': 25,
    'ADV': 25,
    'DOU': 30,
    'PRO': 25,
    'MEN': 25,
}

YEAR_CHOICES = (
    ('2017', '2017'),
    ('2018', '2018'),
    ('2019', '2019'),
    ('2020', '2020'),
    ('2021', '2021'),
)


class Entry(models.Model):
    entry_ref = models.CharField(max_length=22)
    entry_year = models.CharField(
        choices=YEAR_CHOICES, default='2017', max_length=4
    )  # so we can use this system for future comp entries too
    user = models.ForeignKey(User)
    stage_name = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(
        choices=CATEGORY_CHOICES, default='BEG', max_length=3
    )
    status = models.CharField(
        choices=STATUS_CHOICES, default='in_progress', max_length=20
    )
    # keep withdrawn as boolean so we can track last status before withdrawing
    withdrawn = models.BooleanField(default=False)

    song = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Can be submitted later')
    video_url = models.URLField(blank=True, null=True)
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
        verbose_name='Doubles partner name'
    )
    partner_email = models.EmailField(
        blank=True, null=True, verbose_name='Doubles partner email',
        help_text='Ensure this is the email your doubles partner has used '
                  'for their account. We will use it to ensure disclaimer '
                  'information has been received for your partner also.'
    )

    # payment
    video_entry_paid = models.BooleanField(default=False)
    selected_entry_paid = models.BooleanField(default=False)

    date_submitted = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('entry_year', 'user', 'category')
        verbose_name_plural = 'entries'

    @cached_property
    def fee(self):
        return ENTRY_FEES[self.category]

    def __str__(self):
        return "{first} {last} - {ref} - {cat} - {yr} - {status}".format(
            first=self.user.first_name, last=self.user.last_name,
            ref=self.entry_ref,
            cat=CATEGORY_CHOICES_DICT[self.category],
            yr=self.entry_year,
            status=STATUS_CHOICES_DICT[self.status]
        )

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.entry_ref = shortuuid.ShortUUID().random(length=22)

        if self.status == 'submitted' and not self.date_submitted:
            self.date_submitted = timezone.now()
        super(Entry, self).save(
            force_insert, force_update, using, update_fields
        )
