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

    # Guardar claves API cifradas
    def save(self, *args, **kwargs):
        api_key = kwargs.pop('api_key', None)
        api_secret = kwargs.pop('api_secret', None)

        if api_key and api_secret:
            fernet = Fernet(settings.ENCRYPTION_KEY)
            # Verificar el cifrado
            self.api_key_encrypted = fernet.encrypt(api_key.encode())
            self.api_secret_encrypted = fernet.encrypt(api_secret.encode())

            print(f"API Key cifrada: {self.api_key_encrypted}")
            print(f"API Secret cifrada: {self.api_secret_encrypted}")

        super().save(*args, **kwargs)

    # Obtener la clave API descifrada
    def get_api_key(self):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        decrypted_api_key = fernet.decrypt(self.api_key_encrypted).decode()
        print(f"API Key descifrada desde el modelo: {decrypted_api_key}")
        return decrypted_api_key

    # Obtener el API Secret descifrado
    def get_api_secret(self):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        decrypted_api_secret = fernet.decrypt(self.api_secret_encrypted).decode()
        print(f"API Secret descifrada desde el modelo: {decrypted_api_secret}")
        return decrypted_api_secret

    def __str__(self):
        return self.user.username
