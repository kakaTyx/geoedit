from django.conf.urls.defaults import *

# Our main ShapeEditor URLs:

urlpatterns = patterns('geoedit.shapeEditor.views',
       (r'^shape-editor$',
            'listShapefiles'),
       (r'^shape-editor/import$',
            'importShapefile'),
       (r'^shape-editor/export/(?P<shapefile_id>\d+)$',
            'exportShapefile'),
       (r'^shape-editor/edit/(?P<shapefile_id>\d+)$',
            'editShapefile'),
       (r'^shape-editor/delete/(?P<shapefile_id>\d+)$',
            'deleteShapefile'),
       (r'^shape-editor/findFeature$',
            'findFeature'),
       (r'^shape-editor/addFeature/(?P<shapefile_id>\d+)$',
            'editFeature'), # feature_id = None -> add.
       (r'^shape-editor/editFeature/(?P<shapefile_id>\d+)/' +
        r'(?P<feature_id>\d+)$',
            'editFeature'),
       (r'^shape-editor/deleteFeature/(?P<shapefile_id>\d+)/' +
        r'(?P<feature_id>\d+)$',
            'deleteFeature'),
)

# Our TMS Server URLs:

urlpatterns += patterns('geoedit.shapeEditor.tms',
       (r'^shape-editor/tms$',
            'root'), # "shape-editor/tms" calls root()
       (r'^shape-editor/tms/(?P<version>[0-9.]+)$',
            'service'), # "shape-editor/tms/1.0" calls service(version=1.0)
       (r'^shape-editor/tms/(?P<version>[0-9.]+)/' +
        r'(?P<shapefile_id>\d+)$',
            'tileMap'), # "shape-editor/tms/1.0/2" calls
                        # tileMap(version=1.0, shapefile_id=2)
       (r'^shape-editor/tms/(?P<version>[0-9.]+)/' +
        r'(?P<shapefile_id>\d+)/(?P<zoom>\d+)/' +
        r'(?P<x>\d+)/(?P<y>\d+)\.png$',
            'tile'), # "shape-editor/tms/1.0/2/3/4/5" calls
                     # tile(version=1.0, shapefile_id=2, zoom=3, x=4, y=5)
)

# Testing: Admin.

from django.contrib.gis import admin

admin.autodiscover()

urlpatterns += patterns('',
        (r'^admin/', include(admin.site.urls)),
)

