import enaml
from enaml.stdlib.sessions import simple_session
from enaml.qt.qt_application import QtApplication
with enaml.imports():
    from main_view import Main

# test import of multiple image files
#a = file_import.import_files("*.dm3",output_filename='wing_test')
# load existing chest file:
#a = file_import.open_treasure_chest('wing_test.chest')

qtapp = QtApplication([])
session = simple_session('bonerfart', 'The main UI window', Main)
qtapp.add_factories([session])
qtapp.start_session('bonerfart')
qtapp.start()
