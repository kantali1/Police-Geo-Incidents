"""Forms for the NPF Geo Incidents app."""
from django import forms
from django.contrib.gis.geos import Point
from .models import Incident, INCIDENT_TYPES, SEVERITY_LEVELS


class IncidentForm(forms.ModelForm):
    """
    Incident input form. Lat/lng are plain FloatFields that get converted
    to a PostGIS Point in the view before saving.
    """
    latitude = forms.FloatField(
        min_value=4.0, max_value=14.0,
        widget=forms.NumberInput(attrs={
            'id': 'id_latitude',
            'class': 'form-input',
            'placeholder': 'e.g. 6.5244',
            'step': '0.0001',
        }),
        help_text='Latitude (4° – 14° N for Nigeria)',
    )
    longitude = forms.FloatField(
        min_value=2.0, max_value=15.0,
        widget=forms.NumberInput(attrs={
            'id': 'id_longitude',
            'class': 'form-input',
            'placeholder': 'e.g. 3.3792',
            'step': '0.0001',
        }),
        help_text='Longitude (2° – 15° E for Nigeria)',
    )

    class Meta:
        model = Incident
        fields = [
            'title', 'incident_type', 'severity',
            'description', 'reported_by', 'contact_details',
            'date_occurred', 'is_verified',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Short incident title'}),
            'incident_type': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Detailed description...'}),
            'reported_by': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Officer name / badge number'}),
            'contact_details': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Reporter phone / email'}),
            'date_occurred': forms.DateTimeInput(
                attrs={'class': 'form-input', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
