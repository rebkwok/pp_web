# Generated by Django 2.0.3 on 2018-05-08 20:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entries', '0003_auto_20170815_2248'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='entry_year',
            field=models.CharField(choices=[('2017', '2017'), ('2018', '2018'), ('2019', '2019'), ('2020', '2020'), ('2021', '2021')], default='2019', max_length=4),
        ),
    ]
