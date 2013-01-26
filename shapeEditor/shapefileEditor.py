# shapefileEditor.py
#
# This module implements the necessary logic to allow users to view and edit
# the features from a Shapefile using an OpenLayers map widget.

from django import forms
from django.contrib.gis import admin

from models import Feature
import utils

#############################################################################

# This subclass of GeoModelAdmin allows us to plug in our customized version of
# the openlayers.html template.

class OurGeoModelAdmin(admin.GeoModelAdmin):
    map_template = 'ourOpenlayers.html'

# The following classes tell GeoDjango how to setup an admin interface for a
# Feature while editing various feature types.

class PointAdmin(OurGeoModelAdmin):
    fields = ['geom_singlepoint']

class LineStringAdmin(OurGeoModelAdmin):
    fields = ['geom_linestring']

class PolygonAdmin(OurGeoModelAdmin):
    fields = ['geom_polygon']

class MultiPointAdmin(OurGeoModelAdmin):
    fields = ['geom_multipoint']

class MultiLineStringAdmin(OurGeoModelAdmin):
    fields = ['geom_multilinestring']

class MultiPolygonAdmin(OurGeoModelAdmin):
    fields = ['geom_multipolygon']

class GeometryCollectionAdmin(OurGeoModelAdmin):
    fields = ['geom_geometrycollection']

#############################################################################

def getMapForm(shapefile):
    """ Return a form.Form subclass for editing the given shapefile's features.

        The form will have a single field, 'geometry', which lets the user edit
        the feature's geometry.
    """
    # Setup a dummy admin instance to auto-generate our map widget.

    geometryField = utils.calcGeometryField(shapefile.geom_type)
    geometryType  = utils.calcGeometryFieldType(shapefile.geom_type)

    if geometryType == "Point":
        adminType = PointAdmin
    elif geometryType == "LineString":
        adminType = LineStringAdmin
    elif geometryType == "Polygon":
        adminType = PolygonAdmin
    elif geometryType == "MultiPoint":
        adminType = MultiPointAdmin
    elif geometryType == "MultiLineString":
        adminType = MultiLineStringAdmin
    elif geometryType == "MultiPolygon":
        adminType = MultiPolygonAdmin
    elif geometryType == "GeometryCollection":
        adminType = GeometryCollectionAdmin

    adminInstance = adminType(Feature, admin.site)
    field  = Feature._meta.get_field(geometryField)

    widgetType = adminInstance.get_map_widget(field)

    # Define a form which encapsulates the desired editing field.

    class MapForm(forms.Form):
        geometry = forms.CharField(widget=widgetType(),
                                   label="")

    return MapForm

