from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from .models import Report, Place, Profile


only_letters_spaces = RegexValidator(
    r'^[A-Za-zÀ-ÿñÑ\s]+$',
    'Solo se permiten letras y espacios.'
)


class SignupForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        label="Usuario",
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'usuario'})
    )

    first_name = forms.CharField(
        max_length=30,
        label="Nombre",
        validators=[only_letters_spaces],
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Tu nombre'})
    )

    last_name = forms.CharField(
        max_length=150,
        label="Apellido",
        validators=[only_letters_spaces],
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Tu apellido'})
    )

    email = forms.EmailField(
        required=True,
        label="Correo",
        widget=forms.EmailInput(attrs={'class': 'input', 'placeholder': 'tu@correo.cl'})
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': '••••••••'})
    )
    password2 = forms.CharField(
        label="Repite la contraseña",
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': '••••••••'})
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def save(self, commit=True):
        """
        Guarda el usuario y asegura que nombre, apellido y correo queden limpios.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.first_name = ' '.join(self.cleaned_data['first_name'].split()).title()
        user.last_name = ' '.join(self.cleaned_data['last_name'].split()).title()
        if commit:
            user.save()
        return user


TAGS_CHOICES = [
    ('rampa', 'Rampa'),
    ('ascensor', 'Ascensor'),
    ('bano', 'Baño adaptado'),
    ('estacionamiento', 'Estacionamiento PMR'),
]


class ReportForm(forms.ModelForm):
    place = forms.ModelChoiceField(
        queryset=Place.objects.all().order_by('name'),
        label="Lugar",
        widget=forms.Select(attrs={'class': 'input'})
    )
    rating = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 6)],
        label="Evaluación (1–5)",
        widget=forms.Select(attrs={'class': 'input'})
    )
    tags = forms.MultipleChoiceField(
        choices=TAGS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    photo = forms.ImageField(required=False, label="Foto (máx. 5MB, jpg/png/webp)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

       
        if self.instance and self.instance.pk and self.instance.tags:
            stored_tags = [
                t.strip()
                for t in self.instance.tags.split(',')
                if t.strip()
            ]
            
            valid_values = {value for value, _ in self.fields['tags'].choices}
            initial_tags = [t for t in stored_tags if t in valid_values]
            if initial_tags:
                self.initial.setdefault('tags', initial_tags)

    class Meta:
        model = Report
        fields = ['place', 'description', 'rating', 'tags', 'photo']
        widgets = {
            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'class': 'input',
                    'placeholder': 'Describe lo observado'
                }
            ),
        }

    def clean_photo(self):
        img = self.cleaned_data.get('photo')
        if not img:
            return img
        if img.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen supera 5MB.")
        ctype = (getattr(img, 'content_type', '') or '').lower()
        if not (ctype.startswith('image/') and any(t in ctype for t in ('jpeg', 'jpg', 'png', 'webp'))):
            raise forms.ValidationError("Formato no soportado. Usa JPG, PNG o WEBP.")
        return img

    def clean_tags(self):
        """
        El campo del formulario es una lista (MultipleChoiceField),
        pero en la BD lo guardamos como un string separado por comas.
        """
        tags = self.cleaned_data.get('tags') or []
        return ','.join(tags)


class UserForm(forms.ModelForm):
    """
    Edita los datos básicos del usuario logueado.
    """
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Tu nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Tu apellido'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input',
                'placeholder': 'tu@correo.cl'
            }),
        }


class ProfileForm(forms.ModelForm):
    """
    Edita los datos del perfil (foto y bio).
    """
    class Meta:
        model = Profile
        fields = ("avatar", "bio")
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'input',
                'rows': 3,
                'placeholder': 'Cuéntanos algo sobre ti (opcional)'
            }),
        }

