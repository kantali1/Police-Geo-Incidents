"""Admin registration for NPF Geo Incidents models."""
from django.contrib.gis import admin
from .models import NigeriaState, NigeriaLGA, Incident, UserProfile


@admin.register(NigeriaState)
class NigeriaStateAdmin(admin.GISModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name',)


@admin.register(NigeriaLGA)
class NigeriaLGAAdmin(admin.GISModelAdmin):
    list_display = ('name', 'state_name')
    search_fields = ('name', 'state_name')
    list_filter = ('state_name',)


@admin.register(Incident)
class IncidentAdmin(admin.GISModelAdmin):
    list_display = ('title', 'incident_type', 'severity', 'date_occurred', 'is_verified')
    search_fields = ('title', 'description')
    list_filter = ('incident_type', 'severity', 'is_verified')
    date_hierarchy = 'date_occurred'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_state', 'assigned_lga')
    list_filter = ('role',)
    search_fields = ('user__username',)
