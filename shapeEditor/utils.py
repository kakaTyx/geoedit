# utils.py
#
# This module implements various utility functions for the ShapeEditor
# application.

from django.contrib.gis.geos.collections import MultiPolygon, MultiLineString
from osgeo import ogr
import pyproj

#############################################################################

def ogrTypeToGeometryName(ogrType):
    """ Convert an OGR geometry type to its corresponding geometry name.
    
        This function re-implements the OGRGeometryTypeToName() function,
        which isn't included in the OGR Python bindings.
    """
    return {ogr.wkbUnknown            : 'Unknown',
            ogr.wkbPoint              : 'Point',
            ogr.wkbLineString         : 'LineString',
            ogr.wkbPolygon            : 'Polygon',
            ogr.wkbMultiPoint         : 'MultiPoint',
            ogr.wkbMultiLineString    : 'MultiLineString',
            ogr.wkbMultiPolygon       : 'MultiPolygon',
            ogr.wkbGeometryCollection : 'GeometryCollection',
            ogr.wkbNone               : 'None',
            ogr.wkbLinearRing         : 'LinearRing'}.get(ogrType)


def geometryNameToOGRType(geometryName):
    """ Convert a geometry name back to its corresponding OGR geometry type.

        This is the inverse of ogrTypeToGeometryName().
    """
    return {'Unknown'            : ogr.wkbUnknown,
            'Point'              : ogr.wkbPoint,
            'LineString'         : ogr.wkbLineString,
            'Polygon'            : ogr.wkbPolygon,
            'MultiPoint'         : ogr.wkbMultiPoint,
            'MultiLineString'    : ogr.wkbMultiLineString,
            'MultiPolygon'       : ogr.wkbMultiPolygon,
            'GeometryCollection' : ogr.wkbGeometryCollection,
            'None'               : ogr.wkbNone,
            'LinearRing'         : ogr.wkbLinearRing}.get(geometryName)


def getOGRFeatureAttribute(attr, feature, encoding):
    """ Extract an attribute value from the given OGR feature.

        The parameters are as follows:

            'attr'

                The Attribute object describing the attribute to extract.

            'feature'

                The OGR Feature object which we want to extract the attribute
                value from.

            'encoding'

                The character encoding to use for string values.

        We attempt to extract the given attribute from the given feature, and
        convert it to a string for storage in the database.

        Upon completion, we return a (success, result) tuple, where 'success'
        will be True iff the attribute was successfully extracted, and 'result'
        is either the attribute's value converted to a string or a suitable
        error message explaining why the attribute could not be extracted.
    """
    attrName = str(attr.name)

    if not feature.IsFieldSet(attrName):
        return (True, None)

    needsEncoding = False
    if attr.type == ogr.OFTInteger:
        value = str(feature.GetFieldAsInteger(attrName))
    elif attr.type == ogr.OFTIntegerList:
        value = repr(feature.GetFieldAsIntegerList(attrName))
    elif attr.type == ogr.OFTReal:
        value = feature.GetFieldAsDouble(attrName)
        value = "%*.*f" % (attr.width, attr.precision, value)
    elif attr.type == ogr.OFTRealList:
        values = feature.GetFieldAsDoubleList(attrName)
        sValues = []
        for value in values:
            sValues.append("%*.*f" % (attr.width, attr.precision, value))
        value = repr(sValues)
    elif attr.type == ogr.OFTString:
        value = feature.GetFieldAsString(attrName)
        needsEncoding = True
    elif attr.type == ogr.OFTStringList:
        value = repr(feature.GetFieldAsStringList(attrName))
        needsEncoding = True
    elif attr.type == ogr.OFTDate:
        parts = feature.GetFieldAsDateTime(attrName)
        year,month,day,hour,minute,second,tzone = parts
        value = "%d,%d,%d,%d" % (year,month,day,tzone)
    elif attr.type == ogr.OFTTime:
        parts = feature.GetFieldAsDateTime(attrName)
        year,month,day,hour,minute,second,tzone = parts
        value = "%d,%d,%d,%d" % (hour,minute,second,tzone)
    elif attr.type == ogr.OFTDateTime:
        parts = feature.GetFieldAsDateTime(attrName)
        year,month,day,hour,minute,second,tzone = parts
        value = "%d,%d,%d,%d,%d,%d,%d,%d" % (year,month,day,
                                             hour,minute,second,tzone)
    else:
        return (False, "Unsupported attribute type: "+str(attr.type))

    if needsEncoding:
        try:
            value = value.decode(encoding)
        except UnicodeDecodeError:
            return (False, "Unable to decode value in " +
                    repr(attrName) + " attribute.&nbsp; " +
                    "Are you sure you're using the right " +
                    "character encoding?")

    return (True, value)


def setOGRFeatureAttribute(attr, value, feature, encoding):
    """ Store an attribute value into the given OGR feature.

        The parameters are as follows:

            'attr'

                The Attribute object describing the attribute to store.

            'value'

                The value to store, as a string.

            'feature'

                The OGR Feature object which we want to store the attribute
                value into.

            'encoding'

                The character encoding to use for string values.

        We convert the attribute value into the appropriate data type, and
        store it into the given feature.
    """
    attrName = str(attr.name)

    if value == None:
        feature.UnsetField(attrName)
        return

    if attr.type == ogr.OFTInteger:
        feature.SetField(attrName, int(value))
    elif attr.type == ogr.OFTIntegerList:
        integers = eval(value)
        feature.SetFieldIntegerList(attrName, integers)
    elif attr.type == ogr.OFTReal:
        feature.SetField(attrName, float(value))
    elif attr.type == ogr.OFTRealList:
        floats = []
        for s in eval(value):
            floats.append(eval(s))
        feature.SetFieldDoubleList(attrName, floats)
    elif attr.type == ogr.OFTString:
        feature.SetField(attrName, value.encode(encoding))
    elif attr.type == ogr.OFTStringList:
        strings = []
        for s in eval(value):
            strings.append(s.encode(encoding))
        feature.SetFieldStringList(attrName, strings)
    elif attr.type == ogr.OFTDate:
        parts = value.split(",")
        year  = int(parts[0])
        month = int(parts[1])
        day   = int(parts[2])
        tzone = int(parts[3])
        feature.SetField(attrName, year, month, day, 0, 0, 0, tzone)
    elif attr.type == ogr.OFTTime:
        parts  = value.split(",")
        hour   = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2])
        tzone  = int(parts[3])
        feature.SetField(attrName, 0, 0, 0, hour, minute, second, tzone)
    elif attr.type == ogr.OFTDateTime:
        parts = value.split(",")
        year   = int(parts[0])
        month  = int(parts[1])
        day    = int(parts[2])
        hour   = int(parts[3])
        minute = int(parts[4])
        second = int(parts[5])
        tzone  = int(parts[6])
        feature.SetField(attrName, year, month, day,
                         hour, minute, second, tzone)


def calcGeometryField(geometryType):
    """ Return the field to use to store the given type of geometry.

        'geometryType' is a string containing a geometry type, for example
        "Polygon", "Point", "GeometryCollection", etc.

        We return the name of the field within the Feature object to use to
        store the given type of geometry.

        Because shapefiles are unable to differentiate between Polygons and
        MultiPolygons, or between LineStrings and MultiLineStrings, we actually
        need to store a Polygon object into the MultiPolygon field, and
        LineString objects within the MultiLineString field.

        See [http://code.djangoproject.com/ticket/7218] for more details.

        To work around for this, the _calcGeometryField() function maps
        Polygons to MultiPolygons and LineStrings to MultiLineStrings.  Other
        geometry types are unchanged.

        Upon completion, we return the name of the field within the Feature
        database object to use to store geometries of the given type.
    """
    if geometryType == "Polygon":
        return "geom_multipolygon"
    elif geometryType == "LineString":
        return "geom_multilinestring"
    elif geometryType == "Point":
        return "geom_singlepoint"
    else:
        return "geom_" + geometryType.lower()


def calcGeometryFieldType(geometryType):
    """ Return the type of field used to store the given type of geometry.

        'geometry' is a string containing a geometry type, for example
        "Polygon", "Point", "GeometryCollection", etc.

        We return the name of the type of field which will be used to store
        this geometry in the database.

        This works in the same way as calcGeometryField(), above, except it
        returns the type of geometry rather than the field name.
    """
    if geometryType == "Polygon":
        return "MultiPolygon"
    elif geometryType == "LineString":
        return "MultiLineString"
    else:
        return geometryType


def wrapGEOSGeometry(geometry):
    """ Wrap the given GEOSGeometry object if required.

        If the given geometry object is a Polygon, we wrap the polygon in a
        MultiPolygon object.  Similarly, if the geometry is a LineString, we
        wrap it in a MultiLineString.

        This is used to ensure that imported Polygon and LineString objects can
        be stored into the appropriate field of the Feature database object.
        See the definition of the calcGeometryField() function, above, to see
        why this is necessary.

        Upon completion, we return the wrapped object, or the object unchanged
        if it does not need to be wrapped.
    """
    if geometry.geom_type == "Polygon":
        return MultiPolygon(geometry)
    elif geometry.geom_type == "LineString":
        return MultiLineString(geometry)
    else:
        return geometry


def unwrapGEOSGeometry(geometry):
    """ Unwrap the given GEOSGeometry object.

        If the given geometry object is a MultiPolygon which contains exactly
        one Polygon, we return the Polygon object.  Similarly, if the geometry
        is a MultiLineString containing exactly one LineString, we return the
        LineString object.  Otherwise, we return the geometry object unchanged.

        See the definition of the calcGeometryField() function, above, to see
        why wrapping and unwrapping Polygon and LineString fields is necessary.
    """
    if geometry.geom_type in ["MultiPolygon", "MultiLineString"]:
        if len(geometry) == 1:
            return geometry[0]
    return geometry


def calcSearchRadius(latitude, longitude, distance):
    """ Given a distance in meters, return the matching distance in "degrees".

        'latitude' and 'longitude' are the coordinates for a desired point on
        the Earth's surface, and 'distance' is a distance in meters.  We return
        the maximum number of degrees or latitude or longitude that are covered
        by heading 'distance' meters east, west, north or south of the
        specified starting point.
    """
    geod = pyproj.Geod(ellps="WGS84")

    radius = 0
    x,y,angle = geod.fwd(longitude, latitude, 0, distance)
    radius = max(radius, y-latitude)

    x,y,angle = geod.fwd(longitude, latitude, 90, distance)
    radius = max(radius, x-longitude)

    x,y,angle = geod.fwd(longitude, latitude, 180, distance)
    radius = max(radius, latitude-y)

    x,y,angle = geod.fwd(longitude, latitude, 270, distance)
    radius = max(radius, longitude-x)

    return radius

