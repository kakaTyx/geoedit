# shapefileIO.py
#
# This module implements the import/export logic for transferring shapefiles
# into our database.

from geoedit.shapeEditor.models import Shapefile, Attribute
from geoedit.shapeEditor.models import Feature, AttributeValue

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse

from osgeo import ogr,osr

import os
import os.path
import shutil
import tempfile
import traceback
import zipfile

import utils

#############################################################################

def importData(shapefile, characterEncoding):
    """ Attempt to import the contents of a shapefile into our database.

        'shapefile' is the Django UploadedFile object that was uploaded, and
        'characterEncoding' is the character encoding to use for interpreting
        the shapefile's string attributes.

        We return None if the import succeeded.  Otherwise we return a string
        containing a suitable error message explaining why the shapefile can't
        be imported.
    """
    # Copy the zip archive into a temporary file.

    fd,fname = tempfile.mkstemp(suffix=".zip")
    os.close(fd)

    f = open(fname, "wb")
    for chunk in shapefile.chunks():
        f.write(chunk)
    f.close()

    # Open the zip file and check its contents.

    if not zipfile.is_zipfile(fname):
        os.remove(fname)
        return "Not a valid zip archive."

    zip = zipfile.ZipFile(fname)

    required_suffixes = [".shp", ".shx", ".dbf", ".prj"]
    hasSuffix = {}
    for suffix in required_suffixes:
        hasSuffix[suffix] = False

    for info in zip.infolist():
        extension = os.path.splitext(info.filename)[1].lower()
        if extension in required_suffixes:
            hasSuffix[extension] = True
        else:
            print "Extraneous file: " + info.filename

    for suffix in required_suffixes:
        if not hasSuffix[suffix]:
            zip.close()
            os.remove(fname)
            return "Archive missing required " + suffix + " file."

    # Decompress the zip archive into a temporary directory.  At the same
    # time, we get the name of the main ".shp" file.

    zip = zipfile.ZipFile(fname)
    shapefileName = None
    dirname = tempfile.mkdtemp()
    for info in zip.infolist():
        if info.filename.endswith(".shp"):
            shapefileName = info.filename

        dstFile = os.path.join(dirname, info.filename)
        f = open(dstFile, "wb")
        f.write(zip.read(info.filename))
        f.close()
    zip.close()

    # Attempt to open the shapefile.

    try:
        datasource  = ogr.Open(os.path.join(dirname, shapefileName))
        layer       = datasource.GetLayer(0)
        shapefileOK = True
    except:
        traceback.print_exc()
        shapefileOK = False

    if not shapefileOK:
        os.remove(fname)
        shutil.rmtree(dirname)
        return "Not a valid shapefile."

    # Import the data from the opened shapefile.

    geometryType  = layer.GetLayerDefn().GetGeomType()
    geometryName  = utils.ogrTypeToGeometryName(geometryType)
    srcSpatialRef = layer.GetSpatialRef()
    dstSpatialRef = osr.SpatialReference()
    dstSpatialRef.ImportFromEPSG(4326)

    shapefile = Shapefile(filename=shapefileName,
                          srs_wkt=srcSpatialRef.ExportToWkt(),
                          geom_type=geometryName,
                          encoding=characterEncoding)
    shapefile.save()

    attributes = []
    layerDef = layer.GetLayerDefn()
    for i in range(layerDef.GetFieldCount()):
        fieldDef = layerDef.GetFieldDefn(i)
        attr = Attribute(shapefile=shapefile,
                         name=fieldDef.GetName(),
                         type=fieldDef.GetType(),
                         width=fieldDef.GetWidth(),
                         precision=fieldDef.GetPrecision())
        attr.save()
        attributes.append(attr)

    coordTransform = osr.CoordinateTransformation(srcSpatialRef,
                                                  dstSpatialRef)

    for i in range(layer.GetFeatureCount()):
        srcFeature = layer.GetFeature(i)
        srcGeometry = srcFeature.GetGeometryRef()
        srcGeometry.Transform(coordTransform)
        geometry = GEOSGeometry(srcGeometry.ExportToWkt())
        geometry = utils.wrapGEOSGeometry(geometry)
        geometryField = utils.calcGeometryField(geometryName)
        args = {}
        args['shapefile'] = shapefile
        args[geometryField] = geometry
        feature = Feature(**args)
        feature.save()

        for attr in attributes:
            success,result = \
                    utils.getOGRFeatureAttribute(attr, srcFeature,
                                                 characterEncoding)
            if not success:
                os.remove(fname)
                shutil.rmtree(dirname)
                shapefile.delete()
                return result

            attrValue = AttributeValue(feature=feature,
                                       attribute=attr,
                                       value=result)
            attrValue.save()

    # Finally, clean everything up.

    os.remove(fname)
    shutil.rmtree(dirname)

    return None # success.

#############################################################################

def exportData(shapefile):
    """ Export the contents of the given shapefile.

        'shapefile' is the Shapefile object to export.

        We create a shapefile which holds the contents of the given shapefile,
        then copy the shapefile into a temporary zip archive.  Upon completion,
        we return a Django HttpResponse object which can be used to send the
        zipped shapefile to the user's web browser.
    """
    # Create an OGR shapefile to hold the data we're exporting.

    dstDir = tempfile.mkdtemp()
    dstFile = str(os.path.join(dstDir, shapefile.filename))

    srcSpatialRef = osr.SpatialReference()
    srcSpatialRef.ImportFromEPSG(4326)

    dstSpatialRef = osr.SpatialReference()
    dstSpatialRef.ImportFromWkt(shapefile.srs_wkt)

    coordTransform = osr.CoordinateTransformation(srcSpatialRef,
                                                  dstSpatialRef)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    datasource = driver.CreateDataSource(dstFile)
    layer = datasource.CreateLayer(str(shapefile.filename),
                                   dstSpatialRef)

    # Define the various fields which will hold our attributes.

    for attr in shapefile.attribute_set.all():
        field = ogr.FieldDefn(str(attr.name), attr.type)
        field.SetWidth(attr.width)
        field.SetPrecision(attr.precision)
        layer.CreateField(field)

    # Save the feature geometries and attributes into the shapefile.

    geomField = utils.calcGeometryField(shapefile.geom_type)

    for feature in shapefile.feature_set.all():
        geometry = getattr(feature, geomField)
        geometry = utils.unwrapGEOSGeometry(geometry)
        dstGeometry = ogr.CreateGeometryFromWkt(geometry.wkt)
        dstGeometry.Transform(coordTransform)

        dstFeature = ogr.Feature(layer.GetLayerDefn())
        dstFeature.SetGeometry(dstGeometry)

        for attrValue in feature.attributevalue_set.all():
            utils.setOGRFeatureAttribute(attrValue.attribute,
                                         attrValue.value,
                                         dstFeature,
                                         shapefile.encoding)

        layer.CreateFeature(dstFeature)
        dstFeature.Destroy()

    datasource.Destroy() # Close the file, write everything to disk.

    # Compress the shapefile into a ZIP archive.

    temp = tempfile.TemporaryFile()
    zip = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

    shapefileBase = os.path.splitext(dstFile)[0]
    shapefileName = os.path.splitext(shapefile.filename)[0]

    for fName in os.listdir(dstDir):
        zip.write(os.path.join(dstDir, fName), fName)

    zip.close()

    # Clean up our temporary files.

    shutil.rmtree(dstDir)

    # Create an HttpResponse object to send the ZIP file back to the user's web
    # browser.

    f = FileWrapper(temp)
    response = HttpResponse(f, content_type="application/zip")
    response['Content-Disposition'] = "attachment; filename=" \
                                    + shapefileName + ".zip"
    response['Content-Length'] = temp.tell()
    temp.seek(0)
    return response

