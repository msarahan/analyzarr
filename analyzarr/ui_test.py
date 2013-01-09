import file_import
import controller
#from ui.ucc import CellCropper
from matplotlib import pyplot as plt

import enaml
from enaml.stdlib.sessions import simple_session
from enaml.qt.qt_application import QtApplication
with enaml.imports():
    from ui.main_view import Main



# test import of multiple image files
#a = file_import.import_files("*.dm3",output_filename='wing_test')
# load existing chest file:
a = file_import.open_treasure_chest('wing_test.chest')

adv = controller.HighSeasAdventure(a)

qtapp = QtApplication([])
session = simple_session('bonerfart', 'The main UI window', Main, 
                         controller = adv)
qtapp.add_factories([session])
qtapp.start_session('bonerfart')
qtapp.start()


# test plotting images
#adv.plot_images()
# test cell cropper
#adv.cell_cropper()
# test plotting of cropped cells
#adv.plot_cells()

#adv.plot_cells()
#factors, scores = adv.PCA()

#plt.imshow(factors[0])

#adv.characterize_cells(10)

#print a.getNode('/cells','2int_63_bin')