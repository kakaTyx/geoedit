# Model definition for the ShapeEditor's database objects.

from django.contrib.gis.db import models

#############################################################################

class Shapefile(models.Model):
    """ The Shapefile object holds all the features imported from a single
        shapefile.
    """
    filename  = models.CharField(max_length=255)
    srs_wkt   = models.CharField(max_length=255)
    geom_type = models.CharField(max_length=50)
    encoding  = models.CharField(max_length=20)


    def __unicode__(self):
        return self.filename

#############################################################################

class Attribute(models.Model):
    """ The definition for a single attribute within a shapefile.

        Note that there will be one of these for each of the shapefile's
        attribute definitions.
    """
    shapefile = models.ForeignKey(Shapefile)
    name      = models.CharField(max_length=255)
    type      = models.IntegerField()
    width     = models.IntegerField()
    precision = models.IntegerField()


    def __unicode__(self):
        return self.name

#############################################################################

class Feature(models.Model):
    """ The Feature object holds a single geographic feature imported from
        the Shapefile.

        Note that there is a many-to-one relationship between features and
        shapefiles -- that is, each shapefile can have multiple features.

        Because we don't know what type of geometry we will be storing, we
        define separate fields for each of the geometry types the user can
        edit.
    """
    shapefile               = models.ForeignKey(Shapefile)
    geom_singlepoint              = models.PointField(srid=4326, null=True,
                                                blank=True)
    geom_multipoint         = models.MultiPointField(srid=4326, null=True,
                                                     blank=True)
    geom_multilinestring    = models.MultiLineStringField(srid=4326,
                                                          null=True,
                                                          blank=True)
    geom_multipolygon       = models.MultiPolygonField(srid=4326,
                                                       null=True, blank=True)
    geom_geometrycollection = models.GeometryCollectionField(srid=4326,
                                                             null=True,
                                                             blank=True)

    # The following is required to do spatial queries on Features.

    objects = models.GeoManager()


    def __unicode__(self):
        for geom in [self.geom_singlepoint, self.geom_multipoint,
                     self.geom_multilinestring, self.geom_multipolygon,
                     self.geom_geometrycollection]:
            if geom != None:
                return str(geom)
        return "id " + str(self.id)

#############################################################################

class AttributeValue(models.Model):
    """ The AttributeValue object holds a single attribute value for a
        geographic feature.

        Note that there is a many-to-one relationship between attributes and
        features -- that is, each feature can have multiple attributes.
        Similarly, the AttributeValue links to the Attribute the value is for.
    """
    feature   = models.ForeignKey(Feature)
    attribute = models.ForeignKey(Attribute)
    value     = models.CharField(max_length=255, null=True)


    def __unicode__(self):
        return self.value

#############################################################################

class BaseMap(models.Model):
    """ The BaseMap object holds MultiPolyons for display as a base map.

        This is used by our Tile Map Server (tms.py) to render a base map on
        top of which the various imported Shapefile features can be drawn.
    """
    name     = models.CharField(max_length=50)
    geometry = models.MultiPolygonField(srid=4326)

    objects = models.GeoManager()


    def __unicode__(self):
        return self.name
