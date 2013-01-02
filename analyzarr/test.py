import file_import
import controller
from plotting.ucc import CellCropper
from matplotlib import pyplot as plt

# test import of multiple image files
#a = file_import.import_files("*.dm3",output_filename='wing_test')
# load existing chest file:
a=file_import.open_treasure_chest('wing_test.chest')

adv = controller.HighSeasAdventure(a)

# test plotting images
adv.plot_images()
# test cell cropper
#adv.cell_cropper()
# test plotting of cropped cells
#adv.plot_cells()

adv.plot_cells()
#factors, scores = adv.PCA()

#plt.imshow(factors[0])

#adv.characterize_cells(10)

#print a.getNode('/cells','2int_63_bin')