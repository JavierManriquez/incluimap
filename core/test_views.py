from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages

from .models import Place, Report, Comment, Profile


class ReportDetailTest(TestCase):
    """
    Pruebas de caja blanca sobre la vista report_detail:
    - GET debe responder 200 y usar el template correcto.
    - POST con comentario válido crea un Comment.
    - POST con comentario vacío no crea Comment y muestra mensaje de error.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            "ignacio", "ignacio@test.com", "123456"
        )
        self.client.login(username="ignacio", password="123456")

        self.place = Place.objects.create(
            name="Estación",
            address="Metro Maipú",
            lat=Decimal("-33.520000"),
            lng=Decimal("-70.770000"),
            tags="baño adaptado"
        )

        self.report = Report.objects.create(
            place=self.place,
            author=self.user,
            description="Baño adaptado cerrado",
            rating=4,
            tags="baño"
        )

    def test_report_detail_get(self):
        """La vista debe cargar correctamente en GET."""
        url = reverse("report_detail", kwargs={"pk": self.report.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/report_detail.html")
        self.assertContains(response, "Baño adaptado cerrado")

    def test_comentario_valido(self):
        """Debe crear comentario si el texto es válido."""
        url = reverse("report_detail", kwargs={"pk": self.report.id})
        response = self.client.post(url, {"text": "Esto sigue malo"})

        # Redirige de vuelta al detalle
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)
        comentario = Comment.objects.first()
        self.assertEqual(comentario.text, "Esto sigue malo")
        self.assertEqual(comentario.report, self.report)

    def test_comentario_vacio(self):
        """Un comentario vacío NO debe crearse y debe mostrar mensaje de error."""
        url = reverse("report_detail", kwargs={"pk": self.report.id})
        response = self.client.post(url, {"text": ""})

        # No se crea comentario
        self.assertEqual(Comment.objects.count(), 0)

        # Se debe haber agregado un mensaje de error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("vacío" in str(m) for m in messages))


class ToggleFavoriteTest(TestCase):
    """
    Pruebas de caja blanca para toggle_favorite_place:
    - Agrega un lugar a favoritos.
    - Vuelve a quitarlo de favoritos.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("user", "u@test.com", "123456")
        self.client.login(username="user", password="123456")

        self.place = Place.objects.create(
            name="Mall Arauco",
            address="Av. Américo",
            lat=Decimal("-33.520000"),
            lng=Decimal("-70.770000"),
            tags="rampa"
        )

    def test_toggle_favorite_agrega_y_quita(self):
        url = reverse("toggle_favorite_place", kwargs={"place_id": self.place.id})

        # Primero: agregar a favoritos
        self.client.post(url)
        self.assertIn(self.place, self.user.profile.favorite_places.all())

        # Segundo: quitar de favoritos
        self.client.post(url)
        self.assertNotIn(self.place, self.user.profile.favorite_places.all())


class PlacesAPITest(TestCase):
    """
    Pruebas de caja blanca sobre el endpoint places_api:
    - Responde con JSON válido.
    - Filtra por tag correctamente.
    """

    def setUp(self):
        self.client = Client()
        Place.objects.create(
            name="Plaza Baquedano",
            address="Providencia",
            # Coordenadas dentro del rango de Maipú para no romper la validación
            lat=Decimal("-33.520000"),
            lng=Decimal("-70.770000"),
            tags="ascensor"
        )

    def test_places_api_responds(self):
        """El API debe responder 200 y entregar JSON."""
        url = reverse("places_api")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-type"], "application/json")

        data = response.json()
        self.assertIn("places", data)

    def test_places_api_filtra_por_tag(self):
        """Debe filtrar correctamente por el tag entregado en la URL."""
        url = reverse("places_api") + "?tags=ascensor"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data["places"]), 1)
        self.assertEqual(data["places"][0]["tags"], "ascensor")

