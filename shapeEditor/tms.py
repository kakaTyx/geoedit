# tms.py
#
# This module implements our custom Tile Map Server.

from django.http import HttpResponse,Http404
from django.conf import settings

import mapnik2 as mapnik

import traceback
import math

from geoedit.shapeEditor.models import Shapefile
import utils

#############################################################################

# The following constants define how our tile maps are built.

MAX_ZOOM_LEVEL = 10
TILE_WIDTH     = 256
TILE_HEIGHT    = 256

#############################################################################

def root(request):
    """ Return the root resource for our Tile Map Server.

        This tells the TMS client about our one and only TileMapService.
    """
    try:
        baseURL = request.build_absolute_uri()
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8" ?>')
        xml.append('<Services>')
        xml.append('  <TileMapService title="ShapeEditor Tile Map Service"')
        xml.append('                  version="1.0"')
        xml.append('                  href="' + baseURL + '/1.0"/>')
        xml.append('</Services>')
        return HttpResponse("\n".join(xml), mimetype="text/xml")
    except:
        traceback.print_exc()
        raise

#############################################################################

def service(request, version):
    """ Return the TileMapService resource for our Tile Map Server.

        This tells the TMS client about the tile maps available within our Tile
        Map Service.  Note that each tile map corresponds to a shapefile in our
        database.
    """
    try:
        if version != "1.0":
            raise Http404

        baseURL = request.build_absolute_uri()
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8" ?>')
        xml.append('<TileMapService version="1.0" services="' + baseURL + '">')
        xml.append('  <Title>ShapeEditor Tile Map Service</Title>')
        xml.append('  <Abstract></Abstract>')
        xml.append('  <TileMaps>')
        for shapefile in Shapefile.objects.all():
            id = str(shapefile.id)
            xml.append('    <TileMap title="' + shapefile.filename + '"')
            xml.append('             srs="EPSG:4326"')
            xml.append('             href="' + baseURL + '/' + id + '"/>')
        xml.append('  </TileMaps>')
        xml.append('</TileMapService>')
        return HttpResponse("\n".join(xml), mimetype="text/xml")
    except:
        traceback.print_exc()
        raise

#############################################################################

def tileMap(request, version, shapefile_id):
    """ Return a TileMap resource for our Tile Map Server.

        This returns information about a single TileMap within our Tile Map
        Service.  Note that each TileMap corresponds to a single shapefile in
        our database.
    """
    try:
        if version != "1.0":
            raise Http404

        shapefile = Shapefile.objects.get(id=shapefile_id)
        if shapefile == None:
            raise Http404

        baseURL = request.build_absolute_uri()
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8" ?>')
        xml.append('<TileMap version="1.0" ' +
                   'tilemapservice="' + baseURL + '">')
        xml.append('  <Title>' + shapefile.filename + '</Title>')
        xml.append('  <Abstract></Abstract>')
        xml.append('  <SRS>EPSG:4326</SRS>')
        xml.append('  <BoundingBox minx="-180" miny="-90" ' +
                                  'maxx="180" maxy="90"/>')
        xml.append('  <Origin x="-180" y="-90"/>')
        xml.append('  <TileFormat width="' + str(TILE_WIDTH) +
                   '" height="' + str(TILE_HEIGHT) + '" ' +
                   'mime-type="image/png" extension="png"/>')
        xml.append('  <TileSets profile="global-geodetic">')
        for zoomLevel in range(0, MAX_ZOOM_LEVEL+1):
            unitsPerPixel = _unitsPerPixel(zoomLevel)
            xml.append('    <TileSet href="' + baseURL+'/'+str(zoomLevel) +
                       '" units-per-pixel="' + str(unitsPerPixel) +
                       '" order="' + str(zoomLevel) + '"/>')
        xml.append('  </TileSets>')
        xml.append('</TileMap>')
        return HttpResponse("\n".join(xml), mimetype="text/xml")
    except:
        traceback.print_exc()
        raise

#############################################################################

def tile(request, version, shapefile_id, zoom, x, y):
    """ Return a single Tile resource for our Tile Map Server.

        This returns the rendered map tile for a given zoom level, x and y
        coordinate.
    """
    try:
        # Parse the supplied parameters to see which area of the map to
        # generate.

        if version != "1.0":
            raise Http404

        shapefile = Shapefile.objects.get(id=shapefile_id)
        if shapefile == None:
            raise Http404

        geometryField = utils.calcGeometryField(shapefile.geom_type)
        geometryType  = utils.calcGeometryFieldType(shapefile.geom_type)

        zoom = int(zoom)
        x    = int(x)
        y    = int(y)

        if zoom < 0 or zoom > MAX_ZOOM_LEVEL:
            raise Http404

        xExtent = _unitsPerPixel(zoom) * TILE_WIDTH
        yExtent = _unitsPerPixel(zoom) * TILE_HEIGHT

        minLong = x * xExtent - 180.0
        minLat  = y * yExtent - 90.0
        maxLong = minLong + xExtent
        maxLat  = minLat  + yExtent

        if (minLong < -180 or maxLong > 180 or
            minLat < -90 or maxLat > 90):
            print "Map extent out of bounds:",minLong,minLat,maxLong,maxLat
            raise Http404

        # Prepare to display the map.

        map = mapnik.Map(TILE_WIDTH, TILE_HEIGHT,
                         "+proj=longlat +datum=WGS84")
        map.background = mapnik.Color("#7391ad")

        dbSettings = settings.DATABASES['default']

        # Setup our base layer, which displays the base map.

        datasource = mapnik.PostGIS(user=dbSettings['USER'],
                                    password=dbSettings['PASSWORD'],
                                    dbname=dbSettings['NAME'],
                                    table='"shapeEditor_basemap"',
                                    srid=4326,
                                    geometry_field="geometry",
                                    geometry_table='"shapeEditor_basemap"')

        baseLayer = mapnik.Layer("baseLayer")
        baseLayer.datasource = datasource
        baseLayer.styles.append("baseLayerStyle")

        rule = mapnik.Rule()

        rule.symbols.append(
            mapnik.PolygonSymbolizer(mapnik.Color("#b5d19c")))
        rule.symbols.append(
            mapnik.LineSymbolizer(mapnik.Color("#404040"), 0.2))

        style = mapnik.Style()
        style.rules.append(rule)

        map.append_style("baseLayerStyle", style)
        map.layers.append(baseLayer)

        # Setup our feature layer, which displays the features from the
        # shapefile.

        query = '(select ' + geometryField + ' from "shapeEditor_feature" where shapefile_id=' + str(shapefile.id) + ') as geom'

	print "QUERY: " + query +":" + geometryField+":" + geometryType

        datasource = mapnik.PostGIS(user=dbSettings['USER'],
                                    password=dbSettings['PASSWORD'],
                                    dbname=dbSettings['NAME'],
                                    table=query,
                                    srid=4326,
                                    geometry_field=geometryField,
                                    geometry_table='"shapeEditor_feature"')

	print "DATA SOURCE IS " + str(datasource)
        featureLayer = mapnik.Layer("featureLayer")
        featureLayer.datasource = datasource
        featureLayer.styles.append("featureLayerStyle")

        rule = mapnik.Rule()

        if geometryType in ["Point", "MultiPoint"]:
            rule.symbols.append(mapnik.PointSymbolizer())
        elif geometryType in ["LineString", "MultiLineString"]:
            rule.symbols.append(
                mapnik.LineSymbolizer(mapnik.Color("#000000"), 0.5))
        elif geometryType in ["Polygon", "MultiPolygon"]:
            rule.symbols.append(
                mapnik.PolygonSymbolizer(mapnik.Color("#f7edee")))
            rule.symbols.append(
                mapnik.LineSymbolizer(mapnik.Color("#000000"), 0.5))

        style = mapnik.Style()
        style.rules.append(rule)

        map.append_style("featureLayerStyle", style)
        map.layers.append(featureLayer)

        # Finally, render the map.

        map.zoom_to_box(mapnik.Envelope(minLong, minLat, maxLong, maxLat))
        image = mapnik.Image(TILE_WIDTH, TILE_HEIGHT)
        mapnik.render(map, image)
        imageData = image.tostring('png')

        return HttpResponse(imageData, mimetype="image/png")
    except:
        traceback.print_exc()
        raise

#############################################################################
#
# Private definitions:

def _unitsPerPixel(zoomLevel):
    """ Return the units-per-pixel value to use for the given zoom level.

        'zoomLevel' should be an integer in the range 0..MAX_ZOOM_LEVEL.  We
        return the units-per-pixel value to use for the specified zoom level.
    """
    return 0.703125 / math.pow(2, zoomLevel)


