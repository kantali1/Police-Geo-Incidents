import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.utils.timezone import make_aware
from npf_geo_incidents.models import Incident, NigeriaLGA

class Command(BaseCommand):
    help = 'ETL pipeline to import historical crime incidents from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the historical incidents CSV file')

    def handle(self, *args, **options):
        csv_filepath = options['csv_file']
        self.stdout.write(f"Starting import of historical incidents from: {csv_filepath}")

        success_count = 0
        skip_count = 0

        try:
            with open(csv_filepath, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check required headers
                headers = reader.fieldnames
                required = {'title', 'incident_type', 'severity', 'latitude', 'longitude'}
                missing = required - set(headers or [])
                if missing:
                    self.stdout.write(self.style.ERROR(f"Missing required CSV columns: {missing}"))
                    return

                for row_idx, row in enumerate(reader, start=1):
                    title = row.get('title', '').strip()
                    inc_type = row.get('incident_type', 'other').strip()
                    severity = row.get('severity', 'medium').strip()
                    desc = row.get('description', '').strip()
                    rep_by = row.get('reported_by', '').strip()
                    contact = row.get('contact_details', '').strip()
                    is_ver = row.get('is_verified', 'false').lower() == 'true'
                    
                    # Parse date
                    date_str = row.get('date_occurred', '').strip()
                    if date_str:
                        try:
                            # Try standard formats: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
                            if ' ' in date_str:
                                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                            else:
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                            date_occurred = make_aware(dt)
                        except Exception:
                            # Fallback if parsing fails, use standard timezone now
                            from django.utils import timezone
                            date_occurred = timezone.now()
                    else:
                        from django.utils import timezone
                        date_occurred = timezone.now()

                    # Parse coordinates
                    try:
                        lat = float(row.get('latitude', 0))
                        lng = float(row.get('longitude', 0))
                        if not (4.0 <= lat <= 14.0) or not (2.0 <= lng <= 15.0):
                            self.stdout.write(self.style.WARNING(f"Row {row_idx}: Coordinates ({lat}, {lng}) out of bounds for Nigeria. Skipping."))
                            skip_count += 1
                            continue
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"Row {row_idx}: Invalid latitude/longitude format. Skipping."))
                        skip_count += 1
                        continue

                    # Create GIS Point
                    pt = Point(lng, lat, srid=4326)

                    # Spatial lookup: find containing LGA and State
                    lga = NigeriaLGA.objects.filter(geom__contains=pt).first()
                    state = lga.state if lga else None

                    # Save incident
                    Incident.objects.create(
                        title=title,
                        incident_type=inc_type,
                        severity=severity,
                        description=desc,
                        reported_by=rep_by,
                        contact_details=contact,
                        date_occurred=date_occurred,
                        location=pt,
                        lga=lga,
                        state=state,
                        is_verified=is_ver
                    )
                    success_count += 1

            self.stdout.write(self.style.SUCCESS(
                f"Import complete. Successfully imported {success_count} incidents. Skipped {skip_count}."
            ))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {csv_filepath}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred during import: {e}"))
