# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-08-17 11:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('entries', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaypalEntryTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('payment_type', models.CharField(choices=[('video', 'video'), ('selected', 'selected')], max_length=255)),
                ('transaction_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('entry', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='entries.Entry')),
            ],
        ),
    ]
