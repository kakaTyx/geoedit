# import.py
#
# This standalone program imports the base map into the database.
#
# After running this, create the fixture from the initial data using:
#
#     python manage.py dumpdata shapeEditor shapeEditor.BaseMap
#            > shapeEditor/fixtures/initial_data.json
#
# This will set up the initial_data.json fixture, which will be automatically
# loaded whenever the database is sync'd.  This ensures that the base map data
# is available for the map generator to use.

from django.contrib.gis.utils import LayerMapping
from geoedit.shapeEditor.models import BaseMap

shapefile = "/Users/erik/Desktop/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp" 
fieldMapping = {'name' : "NAME", 'geometry' : "MULTIPOLYGON"}

def run():
    mapping = LayerMapping(BaseMap, shapefile, fieldMapping,
                           transform=False, encoding="iso-8859-1")
    mapping.save(strict=True, verbose=True)
