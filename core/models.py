from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings


class Profile(models.Model):
    """
    Perfil de usuario para IncluiMap:
    - avatar: foto de perfil
    - bio: pequeña descripción opcional
    - favorite_places: lugares marcados como favoritos por el usuario
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True
    )
    bio = models.TextField(blank=True)

    favorite_places = models.ManyToManyField(
        'Place',
        blank=True,
        related_name='favorited_by'
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Cada vez que se crea un usuario nuevo, se crea su Profile.
    Si ya existe, se asegura que esté guardado.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()


class Place(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    tags = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def clean(self):
        """
        Valida que las coordenadas estén dentro del cuadrante de Maipú
        (los mismos límites que usas en el mapa con Leaflet).
        """
        super().clean()

        if self.lat is None or self.lng is None:
            return

        lat = float(self.lat)
        lng = float(self.lng)

        MIN_LAT = -33.585
        MAX_LAT = -33.480
        MIN_LNG = -70.835
        MAX_LNG = -70.700

        if not (MIN_LAT <= lat <= MAX_LAT and MIN_LNG <= lng <= MAX_LNG):
            raise ValidationError({
                'lat': (
                    "Las coordenadas deben estar dentro de la comuna de Maipú "
                    f"(lat entre {MIN_LAT} y {MAX_LAT}, lng entre {MIN_LNG} y {MAX_LNG})."
                ),
                'lng': (
                    "Las coordenadas deben estar dentro de la comuna de Maipú "
                    f"(lat entre {MIN_LAT} y {MAX_LAT}, lng entre {MIN_LNG} y {MAX_LNG})."
                ),
            })

    def save(self, *args, **kwargs):
        """
        Asegura que siempre se ejecute la validación (clean) antes de guardar,
        incluso si se guarda desde código sin pasar por un formulario.
        """
        self.full_clean()
        return super().save(*args, **kwargs)


class Report(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(default=3)
    tags = models.CharField(max_length=255, blank=True)
    photo = models.ImageField(upload_to='reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.place.name} — {self.rating}/5"


class Notification(models.Model):
    """
    Notificaciones para avisar al usuario de actividad en sus lugares favoritos.
    Por ahora: nuevos reportes en lugares favoritos.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notificación para {self.user.username}: {self.message[:40]}..."


@receiver(post_save, sender=Report)
def create_favorite_place_notifications(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo Report, se notifica a los usuarios que tienen
    ese Place marcado como favorito (excepto al autor del reporte).
    """
    if not created:
        return

    place = instance.place
    author = instance.author

    # Perfiles que tienen este lugar como favorito
    favorites_qs = (
        Profile.objects
        .filter(favorite_places=place)
        .exclude(user=author)
        .select_related("user")
    )

    if not favorites_qs.exists():
        return

    for profile in favorites_qs:
        user = profile.user
        msg = f"Se ha creado un nuevo reporte en tu lugar favorito '{place.name}'."
        if instance.description:
            msg += f"\n\nDescripción: {instance.description[:200]}"

        # Crear la notificación en la BD
        Notification.objects.create(
            user=user,
            place=place,
            report=instance,
            message=msg,
        )

        # Enviar correo si el usuario tiene email configurado
        if user.email:
            try:
                send_mail(
                    subject=f"Nuevo reporte en tu lugar favorito: {place.name}",
                    message=msg,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                # Para el proyecto de título, registraría en logs;
                # aquí simplemente lo ignoramos.
                pass


class Comment(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comentario de {self.author} en {self.report}'
