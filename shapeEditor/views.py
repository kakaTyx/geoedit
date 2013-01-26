# views.py
#
# This module contains the various views for the ShapeEditor application.

from django.http import HttpResponse,HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.gis.geos import Point

from geoedit.shapeEditor.models import Shapefile, Feature
from geoedit.shapeEditor.forms  import ImportShapefileForm

import traceback

import shapefileEditor
import shapefileIO
import utils

#############################################################################

def listShapefiles(request):
    """ Display a list of the available shapefiles.
    """
    shapefiles = Shapefile.objects.all().order_by('filename')
    return render_to_response("listShapefiles.html",
                              {'shapefiles' : shapefiles})

#############################################################################

def importShapefile(request):
    """ Let the user import a new shapefile.
    """
    if request.method == "GET":
        form = ImportShapefileForm()
        return render_to_response("importShapefile.html",
                                  {'form'   : form,
                                   'errMsg' : None})
    elif request.method == "POST":
        errMsg = None # initially.

        form = ImportShapefileForm(request.POST, request.FILES)
        if form.is_valid():
            shapefile = request.FILES['import_file']
            encoding = request.POST['character_encoding']
            errMsg = shapefileIO.importData(shapefile, encoding)
            if errMsg == None:
                return HttpResponseRedirect("/shape-editor")

        return render_to_response("importShapefile.html",
                                  {'form'   : form,
                                   'errMsg' : errMsg})

#############################################################################

def exportShapefile(request, shapefile_id):
    """ Let the user export the given shapefile.
    """
    shapefile = Shapefile.objects.get(id=shapefile_id)
    if shapefile != None:
        return shapefileIO.exportData(shapefile)
    else:
        return HttpResponseRedirect("/shape-editor")

#############################################################################

def editShapefile(request, shapefile_id):
    """ Let the user edit the given shapefile.

        We display an OpenLayers map showing the contents of the given
        shapefile.  If the user clicks on a feature, we redirect the user's web
        browser to an editing widget to edit the selected feature.
    """
    shapefile      = Shapefile.objects.get(id=shapefile_id)
    tmsURL         = "http://" + request.get_host()+"/shape-editor/tms/"
    findFeatureURL = "http://" + request.get_host()+"/shape-editor/findFeature"
    addFeatureURL  = "http://" + request.get_host() \
                   + "/shape-editor/addFeature/" + str(shapefile_id)

    return render_to_response("selectFeature.html",
                              {'shapefile'      : shapefile,
                               'tmsURL'         : tmsURL,
                               'findFeatureURL' : findFeatureURL,
                               'addFeatureURL'  : addFeatureURL})

#############################################################################

def deleteShapefile(request, shapefile_id):
    """ Let the user delete the given shapefile.
    """
    shapefile = Shapefile.objects.get(id=shapefile_id)

    if request.method == "POST":
        if request.POST['confirm'] == "1":
            shapefile.delete()
        return HttpResponseRedirect("/shape-editor")

    return render_to_response("deleteShapefile.html",
                              {'shapefile' : shapefile})

#############################################################################

def findFeature(request):
    """ See if the user clicked on a feature in our shapefile.
    """
    try:
        shapefile_id = int(request.GET['shapefile_id'])
        latitude     = float(request.GET['latitude'])
        longitude    = float(request.GET['longitude'])

        shapefile = Shapefile.objects.get(id=shapefile_id)
        pt = Point(longitude, latitude)
        radius = utils.calcSearchRadius(latitude, longitude, 100) # 100 meters.

        if shapefile.geom_type == "Point":
            query = Feature.objects.filter(
                geom_singlepoint__dwithin=(pt, radius))
        elif shapefile.geom_type in ["LineString", "MultiLineString"]:
            query = Feature.objects.filter(
                geom_multilinestring__dwithin=(pt, radius))
        elif shapefile.geom_type in ["Polygon", "MultiPolygon"]:
            query = Feature.objects.filter(
                geom_multipolygon__dwithin=(pt, radius))
        elif shapefile.geom_type == "MultiPoint":
            query = Feature.objects.filter(
                geom_multipoint__dwithin=(pt, radius))
        elif shapefile.geom_type == "GeometryCollection":
            query = feature.objects.filter(
                geom_geometrycollection__dwithin=(pt, radius))
        else:
            print "Unsupported geometry: " + feature.geom_type
            return ""

        if query.count() != 1:
            # We don't have exactly one hit -> ignore the click.
            return HttpResponse("")

        # Success!  Redirect the user to the "edit" view for the selected
        # feature.

        feature = query.all()[0]
        return HttpResponse("/shape-editor/editFeature/" +\
                            str(shapefile_id) + "/" + str(feature.id))
    except:
        traceback.print_exc()
        return HttpResponse("")

#############################################################################

def editFeature(request, shapefile_id, feature_id=None):
    """ Let the user add or edit a feature within the given shapefile.

        'feature_id' will be None if we are adding a new feature.
    """
    shapefile = Shapefile.objects.get(id=shapefile_id)

    if request.method == "POST" and "delete" in request.POST:
        # User clicked on the "Delete" button -> show "Delete Feature" page.
        return HttpResponseRedirect("/shape-editor/deleteFeature/" +
                                    shapefile_id + "/" + feature_id)

    geometryField = utils.calcGeometryField(shapefile.geom_type)

    formType = shapefileEditor.getMapForm(shapefile)

    if feature_id == None:
        # Adding a new feature.
        feature = Feature(shapefile=shapefile)
        attributes = []
    else:
        # Editing an existing feature.
        feature = Feature.objects.get(id=feature_id)

    # Get the attributes for this feature.

    attributes = [] # List of (name, value) tuples.
    for attrValue in feature.attributevalue_set.all():
        attributes.append([attrValue.attribute.name,
                           attrValue.value])
    attributes.sort()

    # Display the form.

    if request.method == "GET":
        wkt = getattr(feature, geometryField)
        form = formType({'geometry' : wkt})
        return render_to_response("editFeature.html",
                                  {'shapefile'  : shapefile,
                                   'form'       : form,
                                   'attributes' : attributes})
    elif request.method == "POST":
        form = formType(request.POST)
        try:
            if form.is_valid():
                wkt = form.cleaned_data['geometry']
                setattr(feature, geometryField, wkt)
                feature.save()
                # Return the user to the "select feature" page.
                return HttpResponseRedirect("/shape-editor/edit/" +
                                            shapefile_id)
        except ValueError:
            pass

        return render_to_response("editFeature.html",
                                  {'shapefile'  : shapefile,
                                   'form'       : form,
                                   'attributes' : attributes})

#############################################################################

def deleteFeature(request, shapefile_id, feature_id):
    """ Let the user delete the given feature.
    """
    feature = Feature.objects.get(id=feature_id)

    if request.method == "GET":
        return render_to_response("deleteFeature.html",
                                  {'feature' : feature})
    elif request.method == "POST":
        if request.POST['confirm'] == "1":
            feature.delete()
        # Return the user to the "select feature" page.
        return HttpResponseRedirect("/shape-editor/edit/" +
                                    shapefile_id)

