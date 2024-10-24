# models.py
from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
from django.conf import settings
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Lisäkentät käyttäjäprofiilille
    real_name = models.CharField(max_length=100, null=True)
    last_name = models.CharField(max_length=100, null=True)
    country = models.CharField(max_length=100, null=True)
    city = models.CharField(max_length=100, null=True)
    postal_code = models.CharField(max_length=20, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # API-avaimet ja alusta
    platform = models.CharField(max_length=100, default='binance')
    api_key_encrypted = models.BinaryField(default=b'')
    api_secret_encrypted = models.BinaryField(default=b'')
    email_confirmation_token = models.UUIDField(default=uuid.uuid4)

    # save()-metodin ylikirjoitus API-avainten salaamiseksi
    def save(self, *args, **kwargs):
        # Tarkistetaan, ovatko API-avaimet olemassa
        if self.api_key_encrypted and self.api_secret_encrypted:
            fernet = Fernet(settings.ENCRYPTION_KEY)
            
            # Salaa vain, jos uusia API-avaimia annetaan kwargs:ssä
            if 'api_key' in kwargs:
                self.api_key_encrypted = fernet.encrypt(kwargs['api_key'].encode())
            if 'api_secret' in kwargs:
                self.api_secret_encrypted = fernet.encrypt(kwargs['api_secret'].encode())

        super().save(*args, **kwargs)

    # Palautetaan salattu API-avain
    def get_api_key(self):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        if self.api_key_encrypted:
            return fernet.decrypt(self.api_key_encrypted).decode()
        return None

    # Palautetaan salattu API-salaisuus
    def get_api_secret(self):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        if self.api_secret_encrypted:
            return fernet.decrypt(self.api_secret_encrypted).decode()
        return None

    def __str__(self):
        return self.user.username


# Maksutapahtumien malli

class PaymentTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=255, unique=True)
    plan = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.CharField(max_length=255)
    memo = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.transaction_id} for user {self.user.username}"


# Maksujen rekisteröinti käyttäjätietoineen

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.CharField(max_length=255)
    transaction_id = models.CharField(max_length=100)
    memo = models.CharField(max_length=100, null=True, blank=True)
    network = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, default='pending')

    def __str__(self):
        return f'{self.user.username} - {self.plan} - {self.amount} USDT'
