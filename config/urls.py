from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),

    
    path('', core_views.map_view, name='home'),
    path('lugares/', core_views.places_view, name='places'),
    path('reportar/', core_views.report_view, name='report'),
    path('reportes/', core_views.reports_view, name='reports'),
    path('reportes/mios/', core_views.my_reports_view, name='my_reports'),
    path('reportes/<int:pk>/', core_views.report_detail, name='report_detail'),
    path('reportes/<int:pk>/editar/', core_views.report_edit_view, name='report_edit'),
    path('reportes/<int:pk>/eliminar/', core_views.report_delete_view, name='report_delete'),
    path('acerca/', core_views.about_view, name='about'),
    path('contacto/', core_views.contact_view, name='contact'),

    
    path('favoritos/', core_views.favorites_view, name='favorites'),
    path('lugares/<int:place_id>/favorito/', core_views.toggle_favorite_place, name='toggle_favorite_place'),

    
    path('perfil/', core_views.profile_view, name='profile'),
    path('notificaciones/', core_views.notifications_view, name='notifications'),

    
    path('dashboard/', core_views.dashboard_view, name='dashboard'),

    
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login'
    ),
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout'
    ),
    path('accounts/signup/', core_views.signup_view, name='signup'),
    path(
        'accounts/password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html'
        ),
        name='password_reset'
    ),
    path(
        'accounts/password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'accounts/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),
    path(
        'accounts/reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    
    path('api/places/', core_views.places_api, name='places_api'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

