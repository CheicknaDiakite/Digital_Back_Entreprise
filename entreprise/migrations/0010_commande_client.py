# Generated by Django 5.1.2 on 2024-12-07 22:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entreprise', '0009_commande'),
    ]

    operations = [
        migrations.AddField(
            model_name='commande',
            name='client',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='entreprise.client'),
            preserve_default=False,
        ),
    ]