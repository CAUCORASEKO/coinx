# Generated by Django 5.1 on 2024-09-15 15:58

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('real_name', models.CharField(max_length=100, null=True)),
                ('last_name', models.CharField(max_length=100, null=True)),
                ('country', models.CharField(max_length=100, null=True)),
                ('city', models.CharField(max_length=100, null=True)),
                ('postal_code', models.CharField(max_length=20, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('platform', models.CharField(default='binance', max_length=100)),
                ('api_key_encrypted', models.BinaryField(default=b'')),
                ('api_secret_encrypted', models.BinaryField(default=b'')),
                ('email_confirmation_token', models.UUIDField(default=uuid.uuid4)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
