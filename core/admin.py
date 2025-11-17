from django.contrib import admin
from .models import Place, Report

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "address", "lat", "lng", "tags", "created_at")
    search_fields = ("name", "address", "tags")
    list_filter = ()
    ordering = ("-created_at",)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "place", "author", "rating", "tags", "created_at")
    search_fields = ("place__name", "author__username", "tags", "description")
    list_filter = ("rating",)
    ordering = ("-created_at",)
