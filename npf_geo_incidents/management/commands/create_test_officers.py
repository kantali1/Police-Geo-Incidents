from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from npf_geo_incidents.models import UserProfile, NigeriaState, NigeriaLGA

class Command(BaseCommand):
    help = 'Create test officer accounts for national, state, and LGA scopes.'

    def handle(self, *args, **options):
        # Ensure we have states and LGAs to bind to
        state = NigeriaState.objects.all().first()
        if not state:
            self.stdout.write(self.style.ERROR('No states found in the database. Please run load_nigeria_geodata first.'))
            return
        
        lga = NigeriaLGA.objects.filter(state=state).first()
        if not lga:
            self.stdout.write(self.style.ERROR(f'No LGAs found for state {state.name}. Please load data first.'))
            return

        password = 'NPFpassword123'
        
        # 1. National Officer
        u_nat, created = User.objects.get_or_create(username='national_officer')
        if created or not hasattr(u_nat, 'profile'):
            u_nat.set_password(password)
            u_nat.save()
            UserProfile.objects.update_or_create(
                user=u_nat,
                defaults={'role': 'national', 'assigned_state': None, 'assigned_lga': None}
            )
            self.stdout.write(self.style.SUCCESS(f'Created national_officer (pass: {password})'))
        else:
            self.stdout.write('national_officer already exists')

        # 2. State Officer (Assigned to the first state)
        u_state, created = User.objects.get_or_create(username='state_officer')
        if created or not hasattr(u_state, 'profile'):
            u_state.set_password(password)
            u_state.save()
            UserProfile.objects.update_or_create(
                user=u_state,
                defaults={'role': 'state', 'assigned_state': state, 'assigned_lga': None}
            )
            self.stdout.write(self.style.SUCCESS(f'Created state_officer (pass: {password}, state: {state.name})'))
        else:
            self.stdout.write('state_officer already exists')

        # 3. LGA Officer (Assigned to the first LGA of that state)
        u_lga, created = User.objects.get_or_create(username='lga_officer')
        if created or not hasattr(u_lga, 'profile'):
            u_lga.set_password(password)
            u_lga.save()
            UserProfile.objects.update_or_create(
                user=u_lga,
                defaults={'role': 'lga', 'assigned_state': state, 'assigned_lga': lga}
            )
            self.stdout.write(self.style.SUCCESS(f'Created lga_officer (pass: {password}, LGA: {lga.name} in {state.name})'))
        else:
            self.stdout.write('lga_officer already exists')

        # Create a superuser too for testing admin
        u_admin, created = User.objects.get_or_create(username='admin', is_staff=True, is_superuser=True)
        if created:
            u_admin.set_password(password)
            u_admin.save()
            UserProfile.objects.update_or_create(
                user=u_admin,
                defaults={'role': 'national', 'assigned_state': None, 'assigned_lga': None}
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin superuser (pass: {password})'))
