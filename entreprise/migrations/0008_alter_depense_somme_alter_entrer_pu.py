# Generated by Django 5.1.2 on 2024-12-27 23:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entreprise', '0007_alter_depense_somme_alter_entrer_pu'),
    ]

    operations = [
        migrations.AlterField(
            model_name='depense',
            name='somme',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='entrer',
            name='pu',
            field=models.IntegerField(default=0),
        ),
    ]