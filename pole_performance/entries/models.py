from django.contrib.auth.models import User
from django.db import models
from django.utils.functional import cached_property
from django.utils import timezone


STATUS_CHOICES = (
    ('in_progress', 'In Progress'),
    ('submitted', 'Submitted'),
    ('withdrawn', 'Withdrawn'),
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


class Entry(models.Model):
    user = models.ForeignKey(User)
    stage_name = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(
        choices=CATEGORY_CHOICES, default='BEG', max_length=3
    )
    status = models.CharField(
        choices=STATUS_CHOICES, default='in_progress', max_length=20
    )

    song = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Can be submitted later')
    video_url = models.URLField()
    biography = models.TextField(
        verbose_name='Short bio',
        help_text='How long have you been poling? Previous titles? Why you '
                  'have entered? Any relevant information about yourself? '
                  'How would you describe your style?'
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

    @cached_property
    def fee(self):
        return ENTRY_FEES[self.category]

    def __str__(self):
        return "{} - {} - {}".format(
            self.user.first_name, CATEGORY_CHOICES_DICT[self.category],
            STATUS_CHOICES_DICT[self.status]
        )

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.status == 'submitted' and not self.date_submitted:
            self.date_submitted = timezone.now()
        super(Entry, self).save(
            force_insert, force_update, using, update_fields
        )