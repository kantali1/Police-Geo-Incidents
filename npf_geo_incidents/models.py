"""
NPF Geo Incidents — GeoDjango models.

Uses `django.contrib.gis.db` for spatial fields.
"""
from django.contrib.gis.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from .encryption_utils import encryptor


class EncryptedCharField(models.CharField):
    """CharField that encrypts values in database and decrypts on retrieval."""
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return encryptor.encrypt(value)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return encryptor.decrypt(value)

    def to_python(self, value):
        if value is None:
            return None
        return encryptor.decrypt(value)


class EncryptedTextField(models.TextField):
    """TextField that encrypts values in database and decrypts on retrieval."""
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return encryptor.encrypt(value)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return encryptor.decrypt(value)

    def to_python(self, value):
        if value is None:
            return None
        return encryptor.decrypt(value)


class NigeriaState(models.Model):
    """Represents a Nigerian state polygon boundary."""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=10, blank=True)
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = "Nigerian State"
        verbose_name_plural = "Nigerian States"
        ordering = ['name']

    def __str__(self):
        return self.name


class NigeriaLGA(models.Model):
    """Represents a Nigerian Local Government Area (LGA) polygon boundary."""
    name = models.CharField(max_length=150, db_index=True)
    state = models.ForeignKey(
        NigeriaState,
        on_delete=models.CASCADE,
        related_name='lgas',
        null=True,
        blank=True,
    )
    state_name = models.CharField(max_length=100, blank=True)  # denormalised for quick lookup
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = "LGA"
        verbose_name_plural = "LGAs"
        ordering = ['state_name', 'name']

    def __str__(self):
        return f"{self.name} ({self.state_name})"


class UserProfile(models.Model):
    """User profile mapping official to geographical scope (RLAC)."""
    ROLE_CHOICES = [
        ('national', 'National Officer'),
        ('state', 'State Officer'),
        ('lga', 'LGA Officer'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='national')
    assigned_state = models.ForeignKey(NigeriaState, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_lga = models.ForeignKey(NigeriaLGA, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


INCIDENT_TYPES = [
    ('theft',            'Theft / Robbery'),
    ('assault',          'Assault / Violence'),
    ('kidnapping',       'Kidnapping / Abduction'),
    ('terrorism',        'Terrorism / Insurgency'),
    ('fraud',            'Fraud / Cybercrime'),
    ('homicide',         'Homicide'),
    ('vandalism',        'Vandalism / Property Damage'),
    ('drug',             'Drug-Related'),
    ('sexual_offence',   'Sexual Offence'),
    ('traffic_offence',  'Traffic Offence'),
    ('other',            'Other'),
]

SEVERITY_LEVELS = [
    ('low',      'Low'),
    ('medium',   'Medium'),
    ('high',     'High'),
    ('critical', 'Critical'),
]


class Incident(models.Model):
    """A crime / security incident report with geographic coordinates."""
    # Spatial
    location = models.PointField(srid=4326, help_text="Incident GPS coordinates (longitude, latitude)")
    lga = models.ForeignKey(
        NigeriaLGA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents',
    )
    state = models.ForeignKey(
        NigeriaState,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents',
    )

    # Descriptive
    title = models.CharField(max_length=200)
    incident_type = models.CharField(max_length=50, choices=INCIDENT_TYPES, default='other')
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
    description = EncryptedTextField(blank=True)

    # Meta
    reported_by = EncryptedCharField(max_length=255, blank=True, help_text="Reporter name / badge number")
    contact_details = EncryptedCharField(max_length=255, blank=True, help_text="Reporter phone / email")
    date_occurred = models.DateTimeField(default=timezone.now)
    date_reported = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ['-date_reported']

    def __str__(self):
        return f"[{self.get_incident_type_display()}] {self.title} — {self.date_occurred.strftime('%Y-%m-%d')}"


class Suspect(models.Model):
    """Represents a suspect or person of interest (POI)."""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    name = models.CharField(max_length=200, db_index=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Arrest location
    state_of_arrest = models.ForeignKey(NigeriaState, on_delete=models.SET_NULL, null=True, blank=True)
    lga_of_arrest = models.ForeignKey(NigeriaLGA, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Face Search (simulated embeddings)
    face_embedding = models.TextField(blank=True, help_text="JSON array representing the facial feature vector")
    face_image = models.ImageField(upload_to='suspects/faces/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Fingerprint(models.Model):
    """Represents a suspect's fingerprint minutiae template."""
    FINGER_CHOICES = [
        ('R_thumb',  'Right Thumb'),
        ('R_index',  'Right Index'),
        ('R_middle', 'Right Middle'),
        ('R_ring',   'Right Ring'),
        ('R_little', 'Right Little'),
        ('L_thumb',  'Left Thumb'),
        ('L_index',  'Left Index'),
        ('L_middle', 'Left Middle'),
        ('L_ring',   'Left Ring'),
        ('L_little', 'Left Little'),
    ]
    suspect = models.ForeignKey(Suspect, on_delete=models.CASCADE, related_name='fingerprints')
    finger = models.CharField(max_length=10, choices=FINGER_CHOICES)
    
    # Minutiae template stored as JSON array: [{"x": 100, "y": 150, "type": "ridge_ending", "angle": 0.45}, ...]
    minutiae_template = models.TextField(help_text="JSON representation of minutiae points")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.suspect.name} — {self.get_finger_display()}"

