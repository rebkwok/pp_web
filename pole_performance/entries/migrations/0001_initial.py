# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-08-17 11:03
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_ref', models.CharField(max_length=22)),
                ('entry_year', models.CharField(choices=[(2017, 2017), (2018, 2018), (2019, 2019), (2020, 2020), (2021, 2021)], default=2017, max_length=4)),
                ('stage_name', models.CharField(blank=True, max_length=255, null=True)),
                ('category', models.CharField(choices=[('BEG', 'Beginner'), ('INT', 'Intermediate'), ('ADV', 'Advanced'), ('DOU', 'Doubles'), ('PRO', 'Professional'), ('MEN', 'Mens')], default='BEG', max_length=3)),
                ('status', models.CharField(choices=[('in_progress', 'In Progress'), ('submitted', 'Submitted'), ('withdrawn', 'Withdrawn'), ('selected', 'Selected'), ('rejected', 'Unsuccessful')], default='in_progress', max_length=20)),
                ('song', models.CharField(blank=True, help_text='Can be submitted later', max_length=255, null=True)),
                ('video_url', models.URLField()),
                ('biography', models.TextField(help_text='How long have you been poling? Previous titles? Why you have entered? Any relevant information about yourself? How would you describe your style?', verbose_name='Short bio')),
                ('partner_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Doubles partner name')),
                ('partner_email', models.EmailField(blank=True, help_text='Ensure this is the email your doubles partner has used for their account. We will use it to ensure disclaimer information has been received for your partner also.', max_length=254, null=True, verbose_name='Doubles partner email')),
                ('video_entry_paid', models.BooleanField(default=False)),
                ('selected_entry_paid', models.BooleanField(default=False)),
                ('date_submitted', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='entry',
            unique_together=set([('entry_year', 'user', 'category')]),
        ),
    ]
