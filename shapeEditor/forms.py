# forms.py
#
# This module contains the various forms used by the shapeEditor application.

from django import forms

#############################################################################

# List of character encodings the user can choose between:

CHARACTER_ENCODINGS = [("ascii",  "ASCII"),
                       ("latin1", "Latin-1"),
                       ("utf8",   "UTF-8")]

#############################################################################

class ImportShapefileForm(forms.Form):
    """ This form defines the parameters used to import a shapefile.
    """
    import_file        = forms.FileField(label="Select a Zipped Shapefile")
    character_encoding = forms.ChoiceField(choices=CHARACTER_ENCODINGS,
                                           initial="utf8")

