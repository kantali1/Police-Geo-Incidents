"""URL configuration for the npf_geo_incidents app."""
from django.urls import path
from . import views

app_name = 'npf_geo_incidents'

urlpatterns = [
    # Main heatmap dashboard
    path('', views.heatmap_view, name='heatmap'),

    # Incident report form
    path('report/', views.ReportIncidentView.as_view(), name='report_incident'),

    # AJAX APIs
    path('api/heat/',                      views.incident_frequency_api, name='api_heat'),
    path('api/states/',                    views.states_geojson_api,     name='api_states'),
    path('api/state/<int:state_id>/lgas/', views.state_lgas_api,         name='api_state_lgas'),
    path('api/lga/<int:lga_id>/incidents/', views.lga_incidents_api,    name='api_lga_incidents'),

    # Auth
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Biometrics & ML hotspots
    path('biometrics/', views.biometrics_dashboard_view, name='biometrics_dashboard'),
    path('api/hotspots/predictive/', views.predictive_hotspots_api, name='api_predictive_hotspots'),

    # Analytics dashboard
    path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
]
