from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Q, Avg, Count
from django.views.decorators.http import require_GET, require_POST
from django.core.mail import send_mail
from django.conf import settings
import json

from .models import Place, Report, Profile, Notification, Comment
from .forms import ReportForm, SignupForm, UserForm, ProfileForm


def map_view(request):
    return render(request, "core/map.html")


def places_view(request):
    """
    Lista de lugares, mostrando cuáles son favoritos para el usuario autenticado.
    """
    qs = Place.objects.all().order_by("-created_at")[:100]

    favorite_ids = set()
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        favorite_ids = set(profile.favorite_places.values_list("id", flat=True))

    return render(request, "core/places.html", {
        "places": qs,
        "favorite_ids": favorite_ids,
    })


def reports_view(request):
    """
    Lista de reportes públicos, con opción de orden por fecha y rango de fechas.
    """
    DATE_FIELD = "created_at"

    qs = (
        Report.objects
        .select_related("place", "author")
    )

    
    order = (request.GET.get("orden") or "newest").strip()
    if order == "oldest":
        qs = qs.order_by(DATE_FIELD)
    else:
        order = "newest"
        qs = qs.order_by(f"-{DATE_FIELD}")

    
    date_from = (request.GET.get("desde") or "").strip()
    date_to = (request.GET.get("hasta") or "").strip()

    if date_from:
        qs = qs.filter(**{f"{DATE_FIELD}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{DATE_FIELD}__date__lte": date_to})

    qs = qs[:24]

    return render(request, "core/reports.html", {
        "reports": qs,
        "order": order,
        "date_from": date_from,
        "date_to": date_to,
    })


@login_required
def my_reports_view(request):
    """
    Lista solo los reportes creados por el usuario actual.
    Permite ordenar y filtrar por fecha, reutilizando el mismo template.
    """
    DATE_FIELD = "created_at"

    qs = (
        Report.objects
        .filter(author=request.user)
        .select_related("place", "author")
    )

    order = (request.GET.get("orden") or "newest").strip()
    if order == "oldest":
        qs = qs.order_by(DATE_FIELD)
    else:
        order = "newest"
        qs = qs.order_by(f"-{DATE_FIELD}")

    date_from = (request.GET.get("desde") or "").strip()
    date_to = (request.GET.get("hasta") or "").strip()

    if date_from:
        qs = qs.filter(**{f"{DATE_FIELD}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{DATE_FIELD}__date__lte": date_to})

    qs = qs[:50]

    return render(request, "core/reports.html", {
        "reports": qs,
        "show_only_mine": True,
        "order": order,
        "date_from": date_from,
        "date_to": date_to,
    })


@login_required
def report_view(request):
    """
    Formulario para crear reportes. Si viene ?place=<id>, precarga el lugar.
    Se hace robusto frente a valores inválidos (p.ej. '${p.id}').
    """
    initial = {}
    raw_place_id = request.GET.get("place")

    if raw_place_id:
        try:
            place_id = int(raw_place_id)
            initial["place"] = Place.objects.get(pk=place_id)
        except (TypeError, ValueError, Place.DoesNotExist):
            
            pass

    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.author = request.user
            report.save()
            #  Etiquetamos este mensaje como "report"
            messages.success(
                request,
                "¡Reporte enviado! Gracias por colaborar.",
                extra_tags="report",
            )
            return redirect("home")
        messages.error(request, "Revisa los campos marcados.", extra_tags="report")
    else:
        form = ReportForm(initial=initial)

    return render(request, "core/report_form.html", {"form": form})


@login_required
def report_edit_view(request, pk):
    """
    Editar un reporte propio.
    Solo el autor puede editarlo.
    """
    report = get_object_or_404(Report, pk=pk, author=request.user)

    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Reporte actualizado correctamente.",
                extra_tags="report",
            )
            return redirect("my_reports")
        messages.error(request, "Revisa los campos marcados.", extra_tags="report")
    else:
        form = ReportForm(instance=report)

    return render(request, "core/report_form.html", {
        "form": form,
        "is_edit": True,
        "report": report,
    })


@login_required
def report_delete_view(request, pk):
    """
    Eliminar un reporte propio.
    Pide confirmación y luego redirige a Mis reportes.
    """
    report = get_object_or_404(Report, pk=pk, author=request.user)

    if request.method == "POST":
        report.delete()
        messages.success(
            request,
            "Reporte eliminado correctamente.",
            extra_tags="report",
        )
        return redirect("my_reports")

    return render(request, "core/report_confirm_delete.html", {
        "report": report,
    })


@login_required
def favorites_view(request):
    """
    Muestra los lugares marcados como favoritos por el usuario.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    qs = profile.favorite_places.all().order_by("name")
    return render(request, "core/favorites.html", {"places": qs})


@require_POST
@login_required
def toggle_favorite_place(request, place_id):
    """
    Marca o desmarca un lugar como favorito para el usuario actual.
    """
    place = get_object_or_404(Place, pk=place_id)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if profile.favorite_places.filter(pk=place.pk).exists():
        profile.favorite_places.remove(place)
        messages.info(request, f"Quitaste '{place.name}' de tus favoritos.")
    else:
        profile.favorite_places.add(place)
        messages.success(request, f"Agregaste '{place.name}' a tus favoritos.")

    next_url = request.POST.get("next") or request.GET.get("next")
    return redirect(next_url or "places")


def about_view(request):
    return render(request, "core/about.html")


def contact_view(request):
    """
    Formulario de contacto:
    - Si es GET, muestra la página.
    - Si es POST, intenta enviar un correo y muestra mensajes de éxito/error.
    - Los mensajes se etiquetan con extra_tags="contact" para que solo se
      muestren en la vista de contacto.
    """
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        email = (request.POST.get("email") or "").strip()
        tipo = (request.POST.get("tipo") or "").strip()
        mensaje = (request.POST.get("mensaje") or "").strip()

        form_data = {
            "nombre": nombre,
            "email": email,
            "tipo": tipo or "Consulta general",
            "mensaje": mensaje,
        }

        if not nombre or not email or not mensaje:
            messages.error(
                request,
                "Por favor completa todos los campos obligatorios.",
                extra_tags="contact",
            )
            return render(request, "core/contact.html", {
                "form_data": form_data,
            })

        asunto = f"Nuevo mensaje de contacto — {tipo or 'Sin categoría'}"
        cuerpo = (
            f"Nombre: {nombre}\n"
            f"Email: {email}\n"
            f"Tipo de mensaje: {tipo}\n\n"
            f"Mensaje:\n{mensaje}"
        )

        try:
            destinatario = getattr(
                settings,
                "CONTACT_EMAIL",
                getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@incluimap.local")
            )

            send_mail(
                asunto,
                cuerpo,
                settings.DEFAULT_FROM_EMAIL,
                [destinatario],
                fail_silently=False,
            )

            messages.success(
                request,
                "¡Gracias! Tu mensaje fue enviado correctamente.",
                extra_tags="contact",
            )
            return redirect("contact")

        except Exception:
            messages.error(
                request,
                "Ocurrió un problema al enviar el mensaje. Intenta nuevamente más tarde.",
                extra_tags="contact",
            )
            return render(request, "core/contact.html", {
                "form_data": form_data,
            })

    return render(request, "core/contact.html", {
        "form_data": {},
    })


@require_GET
def places_api(request):
    """
    GET /api/places/?q=texto&tags=rampa,ascensor&commune=maipu
    """
    q = (request.GET.get("q") or "").strip()
    commune = (request.GET.get("commune") or "").strip().lower()
    tags_raw = (request.GET.get("tags") or "").strip().lower()
    tags_list = [t for t in tags_raw.split(",") if t]

    qs = Place.objects.all()

    if commune:
        try:
            field_names = {f.name for f in Place._meta.get_fields()}
            if "commune" in field_names:
                qs = qs.filter(commune__iexact=commune)
        except Exception:
            pass

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q))

    if tags_list:
        tag_q = Q()
        for t in tags_list:
            tag_q |= Q(tags__icontains=t)
        qs = qs.filter(tag_q)

    qs = (
        qs.annotate(
            avg_rating=Avg("report__rating"),
            reports_count=Count("report")
        )
        .values("id", "name", "address", "lat", "lng", "tags", "avg_rating", "reports_count")
        .order_by("-reports_count", "name")
    )

    data = []
    for p in qs:
        try:
            lat = float(p.get("lat"))
            lng = float(p.get("lng"))
        except (TypeError, ValueError):
            continue
        p["lat"] = lat
        p["lng"] = lng
        data.append(p)

    return JsonResponse({"places": data}, json_dumps_params={"ensure_ascii": False})


def signup_view(request):
    """
    Registro de usuario. Al crear la cuenta, inicia sesión y redirige al home.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "¡Cuenta creada! Bienvenido/a a IncluiMap.",
            )
            return redirect('home')
        messages.error(request, "Revisa los campos marcados.")
    else:
        form = SignupForm()

    return render(request, 'registration/signup.html', {'form': form})


@login_required
def profile_view(request):
    """
    Vista de perfil del usuario.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        u_form = UserForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            
            messages.success(
                request,
                "Perfil actualizado correctamente.",
                extra_tags="profile",
            )
            return redirect('profile')
        messages.error(request, "Revisa los campos marcados.", extra_tags="profile")
    else:
        u_form = UserForm(instance=request.user)
        p_form = ProfileForm(instance=profile)

    return render(request, "core/profile.html", {
        "u_form": u_form,
        "p_form": p_form,
        
        "hide_activity_messages": True,
    })


@login_required
def notifications_view(request):
    """
    Lista las notificaciones del usuario actual.
    Marca todas las no leídas como leídas al abrir la página.
    """
    qs = (
        Notification.objects
        .filter(user=request.user)
        .select_related("place", "report")
        .order_by("-created_at")[:50]
    )

    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    return render(request, "core/notifications.html", {
        "notifications": qs,
    })


@login_required
def dashboard_view(request):
    """
    Dashboard con métricas de accesibilidad basadas en:
    - rating promedio y cantidad de reportes por lugar
    - cantidad de reportes y rating promedio por tag
    """
    places_stats = (
        Place.objects
        .annotate(
            avg_rating=Avg("report__rating"),
            reports_count=Count("report")
        )
        .order_by("-avg_rating", "name")
    )

    tags_qs = (
        Report.objects
        .values("tags")
        .annotate(
            total_reportes=Count("id"),
            avg_rating=Avg("rating")
        )
        .order_by("avg_rating", "tags")
    )

    tag_labels = [row["tags"] or "Sin tag" for row in tags_qs]
    tag_counts = [row["total_reportes"] for row in tags_qs]
    tag_avg_ratings = [float(row["avg_rating"] or 0) for row in tags_qs]

    return render(request, "core/dashboard.html", {
        "places_stats": places_stats,
        "tags_stats": tags_qs,
        "tag_labels_json": json.dumps(tag_labels, ensure_ascii=False),
        "tag_counts_json": json.dumps(tag_counts),
        "tag_avg_ratings_json": json.dumps(tag_avg_ratings),
    })


def report_detail(request, pk):
    """
    Muestra el detalle de un reporte y permite agregar comentarios.
    """
    report = get_object_or_404(Report, pk=pk)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(
                request,
                "Debes iniciar sesión para comentar.",
                extra_tags="comment",
            )
            return redirect('login')

        text = request.POST.get('text', '').strip()
        if not text:
            messages.error(
                request,
                "El comentario no puede estar vacío.",
                extra_tags="comment",
            )
        else:
            Comment.objects.create(
                report=report,
                author=request.user,
                text=text
            )
            messages.success(
                request,
                "Comentario publicado.",
                extra_tags="comment",
            )
            return redirect('report_detail', pk=report.pk)

    comments = report.comments.select_related('author')

    return render(request, 'core/report_detail.html', {
        'report': report,
        'comments': comments,
    })

