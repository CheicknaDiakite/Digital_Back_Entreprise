# Generated by Django 5.1.2 on 2024-12-10 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entreprise', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historiqueentrer',
            name='ref',
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name='historiquesortie',
            name='ref',
            field=models.CharField(max_length=150),
        ),
    ]
