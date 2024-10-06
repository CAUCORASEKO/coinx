from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
from django.conf import settings
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Campos adicionales
    real_name = models.CharField(max_length=100, null=True)
    last_name = models.CharField(max_length=100, null=True)
    country = models.CharField(max_length=100, null=True)
    city = models.CharField(max_length=100, null=True)
    postal_code = models.CharField(max_length=20, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # Claves API y plataforma
    platform = models.CharField(max_length=100, default='binance')
    api_key_encrypted = models.BinaryField(default=b'')
    api_secret_encrypted = models.BinaryField(default=b'')
    email_confirmation_token = models.UUIDField(default=uuid.uuid4)

    # Sobrescribir el método save() para cifrar las claves API
    def save(self, *args, **kwargs):
        # Verificamos si las claves API están presentes
        if self.api_key_encrypted and self.api_secret_encrypted:
            fernet = Fernet(settings.ENCRYPTION_KEY)
            
            # Cifrar solo si se pasaron nuevas claves API en los kwargs
            if 'api_key' in kwargs:
                self.api_key_encrypted = fernet.encrypt(kwargs['api_key'].encode())
            if 'api_secret' in kwargs:
                self.api_secret_encrypted = fernet.encrypt(kwargs['api_secret'].encode())

        super().save(*args, **kwargs)

    # Obtener la clave API descifrada
    def get_api_key(self):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        if self.api_key_encrypted:
            return fernet.decrypt(self.api_key_encrypted).decode()
        return None

    # Obtener el API Secret descifrado
    def get_api_secret(self):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        if self.api_secret_encrypted:
            return fernet.decrypt(self.api_secret_encrypted).decode()
        return None

    def __str__(self):
        return self.user.username

