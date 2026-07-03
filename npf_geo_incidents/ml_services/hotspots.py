import numpy as np
from shapely.geometry import box
from django.utils import timezone
from npf_geo_incidents.models import Incident

def get_predictive_hotspots(state_id=None, lga_id=None, threshold_pct=85.0):
    """
    Computes spatial crime hotspot grids with temporal decay weights.
    Returns a GeoJSON FeatureCollection containing cells of high crime density.
    """
    qs = Incident.objects.exclude(location__isnull=True)
    if state_id:
        qs = qs.filter(state_id=state_id)
    if lga_id:
        qs = qs.filter(lga_id=lga_id)

    incidents = list(qs)
    if not incidents:
        return {"type": "FeatureCollection", "features": []}

    severity_map = {'low': 1.0, 'medium': 2.0, 'high': 4.0, 'critical': 8.0}
    now = timezone.now()
    
    lats = []
    lngs = []
    weights = []
    
    for inc in incidents:
        pt = inc.location
        if pt:
            lats.append(pt.y)
            lngs.append(pt.x)
            
            # Temporal decay factor: older crimes carry less predictive weight (half-life of 30 days)
            days_diff = (now - inc.date_occurred).days
            if days_diff < 0:
                days_diff = 0
            decay = np.exp(-days_diff / 30.0)
            
            sev_w = severity_map.get(inc.severity, 2.0)
            weights.append(sev_w * decay)

    if not lats:
        return {"type": "FeatureCollection", "features": []}

    lats = np.array(lats)
    lngs = np.array(lngs)
    weights = np.array(weights)

    # Calculate grid bounds
    min_lat, max_lat = lats.min() - 0.05, lats.max() + 0.05
    min_lng, max_lng = lngs.min() - 0.05, lngs.max() + 0.05

    # 0.05 degrees is roughly 5.5 km grid spacing
    step = 0.05
    lat_grid = np.arange(min_lat, max_lat, step)
    lng_grid = np.arange(min_lng, max_lng, step)

    if len(lat_grid) == 0 or len(lng_grid) == 0:
        return {"type": "FeatureCollection", "features": []}

    grid_weights = np.zeros((len(lat_grid), len(lng_grid)))
    bandwidth = 0.08  # Spatial bandwidth in degrees (~9 km smoothing radius)
    
    for i, grid_lat in enumerate(lat_grid):
        for j, grid_lng in enumerate(lng_grid):
            # Compute Euclidean distance in degrees to all incidents
            dists_sq = (lats - grid_lat)**2 + (lngs - grid_lng)**2
            # Apply Gaussian Kernel density function
            kernel_vals = np.exp(-dists_sq / (2 * (bandwidth**2)))
            # Compute sum of kernel density values multiplied by temporal weights
            grid_weights[i, j] = np.sum(kernel_vals * weights)

    max_weight = grid_weights.max()
    if max_weight == 0:
        return {"type": "FeatureCollection", "features": []}

    threshold = np.percentile(grid_weights, threshold_pct)
    features = []
    cell_id = 1
    
    for i, grid_lat in enumerate(lat_grid):
        for j, grid_lng in enumerate(lng_grid):
            w = grid_weights[i, j]
            if w >= threshold and w > 0.01:
                rel_weight = w / max_weight
                if rel_weight > 0.75:
                    risk_level = "Critical Hotspot"
                    color = "#ef4444" # red
                    opacity = 0.4
                elif rel_weight > 0.45:
                    risk_level = "High Risk Area"
                    color = "#f59e0b" # amber
                    opacity = 0.3
                else:
                    risk_level = "Medium Risk Area"
                    color = "#22d3ee" # cyan
                    opacity = 0.2
                
                # Construct bounds for the grid cell polygon
                w_lng = float(grid_lng - step/2)
                e_lng = float(grid_lng + step/2)
                s_lat = float(grid_lat - step/2)
                n_lat = float(grid_lat + step/2)
                
                poly = box(w_lng, s_lat, e_lng, n_lat)
                
                features.append({
                    "type": "Feature",
                    "id": f"hotspot-{cell_id}",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [list(poly.exterior.coords)]
                    },
                    "properties": {
                        "risk_level": risk_level,
                        "intensity": float(round(w, 2)),
                        "color": color,
                        "fillOpacity": opacity
                    }
                })
                cell_id += 1

    return {
        "type": "FeatureCollection",
        "features": features
    }
