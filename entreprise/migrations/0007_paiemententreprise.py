# Generated by Django 5.1.2 on 2024-12-03 00:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entreprise', '0006_historiqueentrer_entreprise_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaiementEntreprise',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.CharField(max_length=512, unique=True)),
                ('payer', models.BooleanField(default=False)),
                ('moyen_paiement', models.CharField(choices=[('Orange Money', 'Orange Money'), ('Moov Money', 'Moov Money'), ('Sama Money', 'Sama Money'), ('Carte Visa', 'Carte Visa')], max_length=50)),
                ('date_soumission', models.DateTimeField(auto_now_add=True)),
                ('date_validation', models.DateTimeField(null=True)),
                ('montant', models.FloatField()),
                ('numero', models.CharField(max_length=30, null=True)),
                ('strip_link', models.URLField(null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('entreprise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entreprise.entreprise')),
            ],
        ),
    ]