# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-08-29 19:09
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnlineDisclaimer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('date_updated', models.DateTimeField(blank=True, null=True)),
                ('emergency_contact_name', models.CharField(max_length=255, verbose_name='name')),
                ('emergency_contact_relationship', models.CharField(max_length=255, verbose_name='relationship')),
                ('emergency_contact_phone', models.CharField(max_length=255, verbose_name='contact number')),
                ('waiver_terms', models.CharField(default='\nI hereby declare that I have read and understood all the rules of the Pole Performance categories and agree to represent the competition in a professional manner during and prior to the event.\n\nI agree that I am available all day on March 12th 2017.\n\nI understand that my entry will not be accepted until I have paid the appropriate entry fee and that all judges’ decisions are final.\n\nI am taking part in Pole Performance entirely at my own risk. Pole Performance is not responsible for any injury/death caused by my participation in this event.\n\nI assume full responsibility for my participation, knowing the risks involved, and I hold Pole Performance and Carnegie Hall staff/volunteers free from any liability.\n\nI am not pregnant and have not been pregnant in the past three months.\n\nI am deemed physically fit to participate in exercise and have no health or heart conditions that may affect my ability to participate safely in a pole competition.\n\nI give permission for my photo to be taken and used for advertisement and promotional purposes for Pole Performance.\n\nI agree to the above T&amp;C’s and release of liability. I have fully read and understood all information given to me by Pole Performance and free and  voluntarily sign without any inducement.\n', max_length=2048)),
                ('terms_accepted', models.BooleanField()),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='online_disclaimer', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pole_school', models.CharField(blank=True, max_length=255, null=True)),
                ('dob', models.DateField(verbose_name='date of birth')),
                ('address', models.CharField(max_length=512)),
                ('postcode', models.CharField(max_length=10)),
                ('phone', models.CharField(max_length=255)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RemoveField(
            model_name='disclaimer',
            name='user',
        ),
        migrations.DeleteModel(
            name='Disclaimer',
        ),
    ]
