# forms.py 
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class RegistrationForm(forms.ModelForm):
    # Valintavaihtoehdot kaupankäyntialustoille
    platform_choices = [
        ('binance', 'Binance'),
        ('bybit', 'Bybit'),
        ('bingx', 'BingX'),
    ]
    
    # Käyttäjän rekisteröinnin kentät
    real_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    country = forms.CharField(max_length=100, required=True)
    city = forms.CharField(max_length=100, required=True)
    postal_code = forms.CharField(max_length=20, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)  # Valinnainen kenttä
    platform = forms.ChoiceField(choices=platform_choices, required=True)
    
    # API-avainten kentät
    api_key = forms.CharField(max_length=255, required=True)
    api_secret = forms.CharField(max_length=255, required=True, widget=forms.PasswordInput)
    
    # Salasanakentät
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['username', 'real_name', 'last_name', 'country', 'city', 'postal_code', 'email', 'phone_number', 'password', 'confirm_password']
    
    def clean_username(self):
        # Tarkista, onko käyttäjänimi jo olemassa
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists")  # Käyttäjänimi on jo olemassa
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # Varmista, että salasanat täsmäävät
        if password != confirm_password:
            raise ValidationError("Passwords do not match")  # Salasanat eivät täsmää

        return cleaned_data

# Lomake API-avainten päivittämistä varten
class ApiKeyForm(forms.Form):
    api_key = forms.CharField(max_length=255, required=True)
    api_secret = forms.CharField(max_length=255, required=True, widget=forms.PasswordInput)
