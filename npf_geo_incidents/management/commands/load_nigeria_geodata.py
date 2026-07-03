"""
Management command: load_nigeria_geodata

Downloads Nigeria state + LGA boundary GeoJSON from a verified GitHub source
(qedsoftware/geojson_data) and loads them into the database.
Also seeds a set of realistic sample incidents for demo purposes.
"""
import json
import random
import urllib.request
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, Point, MultiPolygon, Polygon
from django.utils import timezone

from npf_geo_incidents.models import NigeriaState, NigeriaLGA, Incident


# ─── GeoJSON sources (verified, public domain) ──────────────────────────────
STATES_GEOJSON_URL = 'https://raw.githubusercontent.com/qedsoftware/geojson_data/main/nigeria-states.geojson'
LGA_GEOJSON_URL    = 'https://raw.githubusercontent.com/qedsoftware/geojson_data/main/nigeria-lga.geojson'


class Command(BaseCommand):
    help = 'Download Nigeria state & LGA boundaries and seed sample incidents.'

    def add_arguments(self, parser):
        parser.add_argument('--skip-incidents', action='store_true', help='Skip seeding sample incidents')
        parser.add_argument('--incidents', type=int, default=120, help='Number of sample incidents to create')

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('-- Loading Nigeria boundary data --'))
        self._load_states()
        self._load_lgas()

        if not options['skip_incidents']:
            self._seed_incidents(options['incidents'])

        self.stdout.write(self.style.SUCCESS('[OK] Done.'))

    # --- States ------------------------------------------------------
    def _load_states(self):
        self.stdout.write('Downloading states GeoJSON...')
        data = self._fetch_json(STATES_GEOJSON_URL)
        if not data:
            return

        count = 0
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            name = props.get('NAME_1') or props.get('name') or props.get('admin1Name') or props.get('Name') or ''
            if not name:
                # Try to find any name-like key
                for k, v in props.items():
                    if isinstance(v, str) and len(v) > 2 and 'name' in k.lower():
                        name = v
                        break
            if not name:
                continue

            geom = self._make_multipolygon(feature.get('geometry'))
            state, created = NigeriaState.objects.update_or_create(
                name=name,
                defaults={'geom': geom},
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] {count} states loaded'))

    # --- LGAs --------------------------------------------------------
    def _load_lgas(self):
        self.stdout.write('Downloading LGA GeoJSON...')
        data = self._fetch_json(LGA_GEOJSON_URL)
        if not data:
            return

        # Build state name -> pk lookup
        state_map = {s.name.lower(): s for s in NigeriaState.objects.all()}

        count = 0
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            lga_name   = props.get('NAME_2') or props.get('name') or props.get('admin2Name') or props.get('Name') or ''
            state_name = props.get('NAME_1') or props.get('admin1Name') or props.get('state') or ''

            if not lga_name:
                for k, v in props.items():
                    if isinstance(v, str) and len(v) > 2 and 'name' in k.lower() and '2' in k:
                        lga_name = v
                        break
            if not state_name:
                for k, v in props.items():
                    if isinstance(v, str) and len(v) > 2 and ('state' in k.lower() or '1' in k):
                        state_name = v
                        break
            if not lga_name:
                continue

            geom = self._make_multipolygon(feature.get('geometry'))
            state_obj = state_map.get(state_name.lower())

            NigeriaLGA.objects.update_or_create(
                name=lga_name,
                state_name=state_name,
                defaults={
                    'state': state_obj,
                    'geom': geom,
                },
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] {count} LGAs loaded'))

    # --- Sample incidents --------------------------------------------
    def _seed_incidents(self, n):
        if Incident.objects.exists():
            self.stdout.write(self.style.WARNING('  [SKIP] Incidents already exist -- skipping seed.'))
            return

        self.stdout.write(f'Seeding {n} sample incidents...')

        lgas = list(NigeriaLGA.objects.exclude(geom__isnull=True).select_related('state'))
        if not lgas:
            self.stdout.write(self.style.WARNING('  [SKIP] No LGA geometries found -- cannot seed.'))
            return

        types = ['theft', 'assault', 'kidnapping', 'terrorism', 'fraud', 'homicide',
                 'vandalism', 'drug', 'sexual_offence', 'traffic_offence', 'other']
        severities = ['low', 'medium', 'high', 'critical']
        sev_weights = [30, 40, 20, 10]

        titles = [
            'Armed robbery on highway', 'Motorcycle theft at market', 'House break-in reported',
            'Street assault near campus', 'Domestic violence incident', 'Bar fight with injuries',
            'Kidnapping of school children', 'Abduction near border region', 'Ransom demand reported',
            'IED device found', 'Attack on village', 'Militant activity observed',
            'Online scam ring busted', 'ATM card fraud', 'Identity theft scheme',
            'Fatal stabbing incident', 'Drive-by shooting', 'Murder investigation opened',
            'Public property vandalized', 'Pipeline sabotage', 'Market stalls destroyed',
            'Drug trafficking intercepted', 'Cannabis farm raided', 'Substance abuse incident',
            'Sexual harassment case', 'Assault on minor reported',
            'Traffic accident with fatality', 'Hit-and-run incident', 'DUI checkpoint arrest',
            'Suspicious package reported', 'Disturbance at polling station',
        ]

        created = 0
        for _ in range(n):
            lga = random.choice(lgas)
            centroid = lga.geom.centroid
            # Jitter the point within ~0.1 degrees of the centroid
            lat = centroid.y + random.uniform(-0.08, 0.08)
            lng = centroid.x + random.uniform(-0.08, 0.08)
            pt = Point(lng, lat, srid=4326)

            days_ago = random.randint(0, 180)
            Incident.objects.create(
                location=pt,
                lga=lga,
                state=lga.state,
                title=random.choice(titles),
                incident_type=random.choice(types),
                severity=random.choices(severities, weights=sev_weights, k=1)[0],
                description=f'Auto-generated sample incident in {lga.name}, {lga.state_name}.',
                reported_by=f'Officer {random.randint(1000,9999)}',
                date_occurred=timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23)),
                is_verified=random.random() > 0.4,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] {created} sample incidents created'))

    # --- Helpers -----------------------------------------------------
    def _fetch_json(self, url):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'  [ERROR] Failed to download: {e}'))
            return None

    def _make_multipolygon(self, geom_dict):
        if not geom_dict:
            return None
        try:
            geom = GEOSGeometry(json.dumps(geom_dict))
            if isinstance(geom, Polygon):
                geom = MultiPolygon(geom)
            return geom
        except Exception:
            return None
