# admin.py

from django.contrib.gis import admin
from models import Feature

class MultiPolygonAdmin(admin.GeoModelAdmin):
    fields = ['geom_multipolygon']


