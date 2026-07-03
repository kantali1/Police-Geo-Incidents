"""
NPF Geo Incidents — Views.

1. heatmap_view       — main page: Leaflet heatmap + drill-down
2. report_incident    — form to input a new incident
3. lga_incidents_api  — AJAX JSON: incidents in a given LGA
4. state_lgas_api     — AJAX JSON: LGAs (bounds) for a clicked state
5. incident_frequency_api — AJAX JSON: heat-intensity per LGA
"""

import json
import math
import random
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views import View

from .models import Incident, NigeriaLGA, NigeriaState, UserProfile, INCIDENT_TYPES, SEVERITY_LEVELS
from .forms import IncidentForm


# ─────────────────────────────────────────────────────────────────────────────
# RLAC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_visible_incidents(user):
    """Filters Incident queryset based on the user's role and geographic scope (RLAC)."""
    qs = Incident.objects.all()
    if user.is_authenticated:
        try:
            profile = user.profile
            if profile.role == 'lga':
                qs = qs.filter(lga=profile.assigned_lga)
            elif profile.role == 'state':
                qs = qs.filter(state=profile.assigned_state)
        except UserProfile.DoesNotExist:
            pass
    return qs


# ─────────────────────────────────────────────────────────────────────────────
# 1. MAIN HEATMAP VIEW
# ─────────────────────────────────────────────────────────────────────────────
def heatmap_view(request):
    """Renders the full-screen Leaflet heatmap dashboard."""
    visible_qs = get_visible_incidents(request.user)
    incident_counts = {
        'total':    visible_qs.count(),
        'verified': visible_qs.filter(is_verified=True).count(),
    }
    return render(request, 'npf_geo_incidents/heatmap.html', {
        'incident_counts': incident_counts,
        'page_title': 'NPF Geo Incidents — Crime Heatmap',
    })


# ─────────────────────────────────────────────────────────────────────────────
# 2. REPORT INCIDENT VIEW
# ─────────────────────────────────────────────────────────────────────────────
class ReportIncidentView(View):
    template_name = 'npf_geo_incidents/report_incident.html'

    def get(self, request):
        form = IncidentForm()
        return render(request, self.template_name, {
            'form': form,
            'page_title': 'Report a New Incident',
        })

    def post(self, request):
        form = IncidentForm(request.POST)
        if form.is_valid():
            incident = form.save(commit=False)
            # Auto-assign LGA and State based on point location
            lat = form.cleaned_data.get('latitude')
            lng = form.cleaned_data.get('longitude')
            if lat and lng:
                from django.contrib.gis.geos import Point
                pt = Point(float(lng), float(lat), srid=4326)
                incident.location = pt
                # Spatial lookup: find LGA containing this point
                lga_qs = NigeriaLGA.objects.filter(geom__contains=pt)
                if lga_qs.exists():
                    lga = lga_qs.first()
                    incident.lga = lga
                    incident.state = lga.state
            incident.save()
            messages.success(request, f'Incident "{incident.title}" reported successfully.')
            return redirect('npf_geo_incidents:heatmap')
        return render(request, self.template_name, {
            'form': form,
            'page_title': 'Report a New Incident',
        })


# ─────────────────────────────────────────────────────────────────────────────
# 3. LGA INCIDENTS API  (AJAX)
# ─────────────────────────────────────────────────────────────────────────────
@require_GET
def lga_incidents_api(request, lga_id):
    """Returns a JSON list of incidents for a given LGA."""
    try:
        lga = NigeriaLGA.objects.get(pk=lga_id)
    except NigeriaLGA.DoesNotExist:
        return JsonResponse({'error': 'LGA not found'}, status=404)

    # Apply RLAC Check
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == 'lga' and profile.assigned_lga_id != lga.pk:
                return JsonResponse({'error': 'Permission Denied: Out of LGA scope'}, status=403)
            if profile.role == 'state' and profile.assigned_state_id != lga.state_id:
                return JsonResponse({'error': 'Permission Denied: Out of State scope'}, status=403)
        except UserProfile.DoesNotExist:
            pass

    qs = get_visible_incidents(request.user).filter(lga=lga).order_by('-date_reported')[:50]
    incidents = []
    for inc in qs:
        incidents.append({
            'id':           inc.id,
            'title':        inc.title,
            'type':         inc.get_incident_type_display(),
            'severity':     inc.get_severity_display(),
            'date':         inc.date_occurred.strftime('%Y-%m-%d %H:%M'),
            'reported_by':  inc.reported_by or 'Anonymous',
            'is_verified':  inc.is_verified,
            'description':  inc.description[:200],
            'lng':          inc.location.x if inc.location else None,
            'lat':          inc.location.y if inc.location else None,
        })

    return JsonResponse({
        'lga_name':   lga.name,
        'state_name': lga.state_name,
        'count':      qs.count(),
        'incidents':  incidents,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 4. STATE LGAs API (AJAX — returns LGA GeoJSON for a clicked state)
# ─────────────────────────────────────────────────────────────────────────────
@require_GET
def state_lgas_api(request, state_id):
    """Returns GeoJSON FeatureCollection of LGA polygons for a given state."""
    try:
        state = NigeriaState.objects.get(pk=state_id)
    except NigeriaState.DoesNotExist:
        return JsonResponse({'error': 'State not found'}, status=404)

    # Apply RLAC Check
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == 'state' and profile.assigned_state_id != state.pk:
                return JsonResponse({'error': 'Permission Denied: Out of State scope'}, status=403)
            if profile.role == 'lga' and profile.assigned_state_id != state.pk:
                return JsonResponse({'error': 'Permission Denied: Out of State scope'}, status=403)
        except UserProfile.DoesNotExist:
            pass

    lgas = NigeriaLGA.objects.filter(state=state).exclude(geom__isnull=True)
    
    # LGA level: only show their specific LGA boundary
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == 'lga':
                lgas = lgas.filter(pk=profile.assigned_lga_id)
        except UserProfile.DoesNotExist:
            pass

    features = []
    for lga in lgas:
        incident_count = get_visible_incidents(request.user).filter(lga=lga).count()
        features.append({
            'type': 'Feature',
            'id': lga.pk,
            'geometry': json.loads(lga.geom.geojson),
            'properties': {
                'lga_id':         lga.pk,
                'name':           lga.name,
                'state_name':     lga.state_name,
                'incident_count': incident_count,
            },
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'state_id':   state.pk,
        'state_name': state.name,
        'features':   features,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 5. INCIDENT FREQUENCY API (AJAX — heat intensity data for Leaflet.heat)
# ─────────────────────────────────────────────────────────────────────────────
@require_GET
def incident_frequency_api(request):
    """
    Returns [lat, lng, intensity] tuples for ALL incidents — used by Leaflet.heat.
    Optionally filtered by ?state_id=<id> or ?lga_id=<id>.
    """
    qs = get_visible_incidents(request.user).exclude(location__isnull=True)

    state_id = request.GET.get('state_id')
    lga_id   = request.GET.get('lga_id')

    if state_id:
        qs = qs.filter(state_id=state_id)
    if lga_id:
        qs = qs.filter(lga_id=lga_id)

    # Build heat array — weight by severity
    severity_weight = {'low': 0.3, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
    heat_points = []
    for inc in qs.values('location', 'severity'):
        if inc['location']:
            from django.contrib.gis.geos import GEOSGeometry
            pt = GEOSGeometry(inc['location'])
            w = severity_weight.get(inc['severity'], 0.5)
            heat_points.append([pt.y, pt.x, w])

    return JsonResponse({'heat_points': heat_points})


# ─────────────────────────────────────────────────────────────────────────────
# 6. STATES GEOJSON API
# ─────────────────────────────────────────────────────────────────────────────
@require_GET
def states_geojson_api(request):
    """Returns GeoJSON of all Nigerian states with incident counts."""
    states = NigeriaState.objects.exclude(geom__isnull=True)
    
    # Apply RLAC Check
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == 'state':
                states = states.filter(pk=profile.assigned_state_id)
            elif profile.role == 'lga':
                states = states.filter(pk=profile.assigned_state_id)
        except UserProfile.DoesNotExist:
            pass

    features = []
    for state in states:
        incident_count = get_visible_incidents(request.user).filter(state=state).count()
        features.append({
            'type': 'Feature',
            'id': state.pk,
            'geometry': json.loads(state.geom.geojson),
            'properties': {
                'state_id':       state.pk,
                'name':           state.name,
                'incident_count': incident_count,
            },
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 7. AUTHENTICATION VIEWS
# ─────────────────────────────────────────────────────────────────────────────
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    """Sleek dark-themed login view."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            messages.success(request, f"Logged in as {request.user.username}.")
            return redirect('npf_geo_incidents:heatmap')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'npf_geo_incidents/login.html', {
        'form': form,
        'page_title': 'Officer Sign In',
    })

def logout_view(request):
    """Logs out the user and redirects to heatmap."""
    auth_logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('npf_geo_incidents:heatmap')


# ─────────────────────────────────────────────────────────────────────────────
# 8. BIOMETRICS VIEWS
# ─────────────────────────────────────────────────────────────────────────────
import os
from django.conf import settings
from django.core.files.storage import default_storage
from .biometrics.matching import match_minutiae_templates
from .ml_services.face_matching import extract_face_vector, calculate_face_similarity
from .models import Suspect, Fingerprint

def biometrics_dashboard_view(request):
    """Officer biometrics portal: Suspect registration, fingerprint matching, and face recognition search."""
    # List of suspects
    suspects = Suspect.objects.all().select_related('state_of_arrest', 'lga_of_arrest')
    states = NigeriaState.objects.all().order_by('name')
    lgas = NigeriaLGA.objects.all().order_by('name')
    
    tab = request.GET.get('tab', 'directory')
    results = None
    search_type = None

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'register':
            name = request.POST.get('name')
            gender = request.POST.get('gender')
            dob = request.POST.get('date_of_birth') or None
            state_id = request.POST.get('state_of_arrest')
            lga_id = request.POST.get('lga_of_arrest')
            
            face_img = request.FILES.get('face_image')
            minutiae_str = request.POST.get('minutiae_template')
            
            suspect = Suspect(
                name=name,
                gender=gender,
                date_of_birth=dob,
                state_of_arrest_id=state_id,
                lga_of_arrest_id=lga_id
            )
            
            if face_img:
                suspect.face_image = face_img
                suspect.save()
                # Extract face embedding
                vec = extract_face_vector(suspect.face_image.path)
                suspect.face_embedding = json.dumps(vec)
            
            suspect.save()
            
            # Add fingerprint
            finger_type = request.POST.get('finger_type', 'R_thumb')
            # Fallback if no minutiae provided, generate mock minutiae template
            if not minutiae_str:
                import random
                mock_points = []
                for _ in range(random.randint(15, 30)):
                    mock_points.append({
                        'x': round(random.uniform(50, 450), 2),
                        'y': round(random.uniform(50, 450), 2),
                        'type': random.choice(['bifurcation', 'ridge_ending']),
                        'angle': round(random.uniform(0, 2*math.pi), 2)
                    })
                minutiae_str = json.dumps(mock_points)
                
            Fingerprint.objects.create(
                suspect=suspect,
                finger=finger_type,
                minutiae_template=minutiae_str
            )
            
            messages.success(request, f"Suspect '{name}' registered successfully.")
            return redirect('/biometrics/?tab=directory')

        elif action == 'search_fingerprint':
            search_type = 'fingerprint'
            tab = 'search'
            uploaded_file = request.FILES.get('fingerprint_file')
            manual_template = request.POST.get('fingerprint_template')
            
            query_template = ""
            if uploaded_file:
                try:
                    query_template = uploaded_file.read().decode('utf-8')
                except Exception:
                    messages.error(request, "Failed to read fingerprint file.")
            elif manual_template:
                query_template = manual_template
                
            if query_template:
                all_prints = Fingerprint.objects.all().select_related('suspect')
                match_results = []
                for fp in all_prints:
                    score = match_minutiae_templates(query_template, fp.minutiae_template)
                    if score > 5.0:
                        match_results.append({
                            'suspect': fp.suspect,
                            'finger': fp.get_finger_display(),
                            'score': score
                        })
                results = sorted(match_results, key=lambda x: x['score'], reverse=True)[:5]
            else:
                messages.error(request, "Please provide a fingerprint template.")

        elif action == 'search_face':
            search_type = 'face'
            tab = 'search'
            face_img = request.FILES.get('search_face_image')
            if face_img:
                # Save temp file
                temp_path = default_storage.save('temp/search_face.jpg', face_img)
                full_temp_path = os.path.join(settings.MEDIA_ROOT, temp_path)
                try:
                    query_vec = extract_face_vector(full_temp_path)
                    all_suspects = Suspect.objects.exclude(face_embedding="")
                    match_results = []
                    for suspect in all_suspects:
                        try:
                            s_vec = json.loads(suspect.face_embedding)
                            score = calculate_face_similarity(query_vec, s_vec)
                            match_results.append({
                                'suspect': suspect,
                                'score': score
                            })
                        except Exception:
                            continue
                    results = sorted(match_results, key=lambda x: x['score'], reverse=True)[:5]
                finally:
                    if os.path.exists(full_temp_path):
                        os.remove(full_temp_path)
                    default_storage.delete(temp_path)
            else:
                messages.error(request, "Please upload a face image for search.")

    return render(request, 'npf_geo_incidents/biometrics_dashboard.html', {
        'suspects': suspects,
        'states': states,
        'lgas': lgas,
        'tab': tab,
        'results': results,
        'search_type': search_type,
        'page_title': 'Officer Biometrics & Suspect Directory'
    })


# ─────────────────────────────────────────────────────────────────────────────
# 9. ML HOTSPOTS API
# ─────────────────────────────────────────────────────────────────────────────
from .ml_services.hotspots import get_predictive_hotspots

@require_GET
def predictive_hotspots_api(request):
    """Returns predictive hotspots as GeoJSON FeatureCollection."""
    state_id = request.GET.get('state_id')
    lga_id = request.GET.get('lga_id')
    
    data = get_predictive_hotspots(state_id=state_id, lga_id=lga_id)
    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────────────────────
# 10. ANALYTICS VIEW
# ─────────────────────────────────────────────────────────────────────────────
from django.db.models import Count
from django.db.models.functions import TruncMonth

def analytics_dashboard_view(request):
    """Analytics view compiling statistics for Chart.js dashboard."""
    visible_qs = get_visible_incidents(request.user)
    
    # 1. Incidents by Type
    type_counts = list(visible_qs.values('incident_type').annotate(count=Count('id')).order_by('-count'))
    type_dict = dict(INCIDENT_TYPES)
    type_labels = [type_dict.get(item['incident_type'], item['incident_type']) for item in type_counts]
    type_data = [item['count'] for item in type_counts]
    
    # 2. Incidents by Severity
    severity_counts = list(visible_qs.values('severity').annotate(count=Count('id')).order_by('-count'))
    severity_dict = dict(SEVERITY_LEVELS)
    severity_labels = [severity_dict.get(item['severity'], item['severity']) for item in severity_counts]
    severity_data = [item['count'] for item in severity_counts]
    
    # 3. Monthly Trend
    trend_counts = list(
        visible_qs.annotate(month=TruncMonth('date_occurred'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    trend_labels = [item['month'].strftime('%b %Y') if item['month'] else 'Unknown' for item in trend_counts]
    trend_data = [item['count'] for item in trend_counts]

    # 4. State distribution (top 10 states)
    state_counts = list(
        visible_qs.values('state__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    state_labels = [item['state__name'] or 'Unknown' for item in state_counts]
    state_data = [item['count'] for item in state_counts]

    context = {
        'page_title': 'Crime Analytics Dashboard',
        'type_labels': json.dumps(type_labels),
        'type_data': json.dumps(type_data),
        'severity_labels': json.dumps(severity_labels),
        'severity_data': json.dumps(severity_data),
        'trend_labels': json.dumps(trend_labels),
        'trend_data': json.dumps(trend_data),
        'state_labels': json.dumps(state_labels),
        'state_data': json.dumps(state_data),
    }
    return render(request, 'npf_geo_incidents/analytics.html', context)
