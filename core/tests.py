from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Place, Report, Comment, Profile, Notification
from django.core.exceptions import ValidationError


class PlaceModelTest(TestCase):
    def test_crear_place_valido(self):
        lugar = Place.objects.create(
            name="Plaza de Maipú",
            address="Av. Pajaritos 123",
            lat=Decimal("-33.520000"),   # 6 decimales
            lng=Decimal("-70.770000"),   # 6 decimales
            tags="rampa, ascensor"
        )

        self.assertIsNotNone(lugar.id)
        self.assertEqual(lugar.name, "Plaza de Maipú")

    def test_place_fuera_de_maipu(self):
        """Debe fallar si las coordenadas están fuera del rango."""
        with self.assertRaises(ValidationError):
            lugar = Place(
                name="Lugar Invalido",
                lat=Decimal("-10.000000"),    # fuera del rango
                lng=Decimal("-10.000000"),
            )
            lugar.full_clean()


class ReportModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="levis", password="123456")
        self.place = Place.objects.create(
            name="Estación Maipú",
            address="Av. Pajaritos",
            lat=Decimal("-33.520000"),
            lng=Decimal("-70.770000")
        )

    def test_crear_reporte_valido(self):
        reporte = Report.objects.create(
            place=self.place,
            author=self.user,
            description="Rampa en mal estado",
            rating=4
        )

        self.assertIsNotNone(reporte.id)
        self.assertEqual(reporte.author, self.user)
        self.assertEqual(reporte.place, self.place)


class CommentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alex", password="123456")
        self.place = Place.objects.create(
            name="Plaza Monumental",
            address="5 de Abril",
            lat=Decimal("-33.520000"),
            lng=Decimal("-70.770000")
        )
        self.reporte = Report.objects.create(
            place=self.place,
            author=self.user,
            description="Baño adaptado cerrado"
        )

    def test_crear_comentario_valido(self):
        comentario = Comment.objects.create(
            report=self.reporte,
            author=self.user,
            text="Lo revisé hoy y sigue cerrado"
        )

        self.assertIsNotNone(comentario.id)
        self.assertEqual(comentario.report, self.reporte)
        self.assertEqual(comentario.author, self.user)


class ProfileModelTest(TestCase):
    def test_profile_se_crea_automatico(self):
        user = User.objects.create_user(username="testuser", password="123456")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(str(user.profile), "Perfil de testuser")


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="levis", password="123456")
        self.user2 = User.objects.create_user(username="ignacio", password="123456")

        # place favorito de ignacio
        self.place = Place.objects.create(
            name="Espacio Urbano",
            address="Pajaritos",
            lat=Decimal("-33.520000"),
            lng=Decimal("-70.770000")
        )
        self.user2.profile.favorite_places.add(self.place)

    def test_se_crea_notificacion_por_reporte_en_favorito(self):
        Report.objects.create(
            place=self.place,
            author=self.user1,
            description="Rampa bloqueada"
        )

        self.assertEqual(Notification.objects.count(), 1)
        notificacion = Notification.objects.first()
        self.assertEqual(notificacion.user, self.user2)
