import json
from django.test import TestCase
from django.contrib.gis.geos import Point
from .models import Incident
from django.db import connection
from .encryption_utils import encryptor

class EncryptionTestCase(TestCase):
    def test_field_encryption(self):
        # Create an incident
        loc = Point(8.6753, 9.0820)
        inc = Incident.objects.create(
            title="Armed Robbery Test",
            location=loc,
            description="Highly sensitive details of armed robbery",
            reported_by="Inspector Gadget",
            contact_details="08012345678"
        )
        
        # 1. Verify object retrieval decrypts successfully
        fetched = Incident.objects.get(pk=inc.pk)
        self.assertEqual(fetched.description, "Highly sensitive details of armed robbery")
        self.assertEqual(fetched.reported_by, "Inspector Gadget")
        self.assertEqual(fetched.contact_details, "08012345678")
        
        # 2. Verify raw DB contents are encrypted
        with connection.cursor() as cursor:
            cursor.execute("SELECT description, reported_by, contact_details FROM npf_geo_incidents_incident WHERE id = %s", [inc.pk])
            row = cursor.fetchone()
            raw_desc, raw_rep, raw_contact = row
            
            # The raw values in DB should NOT contain the plain texts
            self.assertNotIn("sensitive", raw_desc)
            self.assertNotIn("Gadget", raw_rep)
            self.assertNotIn("08012345678", raw_contact)
            
            # Decrypting them directly via encryptor should work
            self.assertEqual(encryptor.decrypt(raw_desc), "Highly sensitive details of armed robbery")
            self.assertEqual(encryptor.decrypt(raw_rep), "Inspector Gadget")
            self.assertEqual(encryptor.decrypt(raw_contact), "08012345678")


from .biometrics.matching import match_minutiae_templates
from .ml_services.face_matching import calculate_face_similarity
from .ml_services.hotspots import get_predictive_hotspots

class BiometricsAndKDETestCase(TestCase):
    def test_minutiae_matching(self):
        t1 = json.dumps([
            {"x": 100, "y": 120, "type": "bifurcation", "angle": 0.5},
            {"x": 200, "y": 250, "type": "ridge_ending", "angle": 1.2}
        ])
        t2 = json.dumps([
            {"x": 102, "y": 122, "type": "bifurcation", "angle": 0.52},
            {"x": 200, "y": 250, "type": "ridge_ending", "angle": 1.2}
        ])
        t3 = json.dumps([
            {"x": 50, "y": 50, "type": "ridge_ending", "angle": 0.0}
        ])
        
        # Identical matches should be 100
        score_self = match_minutiae_templates(t1, t1)
        self.assertEqual(score_self, 100.0)
        
        # Close matches should be high
        score_close = match_minutiae_templates(t1, t2)
        self.assertTrue(score_close > 80.0)
        
        # Different matches should be low/0
        score_diff = match_minutiae_templates(t1, t3)
        self.assertEqual(score_diff, 0.0)

    def test_face_similarity(self):
        v1 = [0.1] * 64
        v2 = [0.1] * 64
        
        score_self = calculate_face_similarity(v1, v2)
        self.assertTrue(score_self > 95.0)

    def test_predictive_hotspots(self):
        # Create an incident to compute hotspots
        loc = Point(8.6753, 9.0820)
        Incident.objects.create(
            title="Hotspot Test Incident",
            location=loc,
            severity="critical"
        )
        
        res = get_predictive_hotspots()
        self.assertEqual(res["type"], "FeatureCollection")
        self.assertTrue(len(res["features"]) > 0)

    def test_analytics_dashboard_view(self):
        response = self.client.get('/analytics/')
        self.assertEqual(response.status_code, 200)
