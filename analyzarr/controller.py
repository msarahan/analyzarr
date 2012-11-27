
import traits.api as t
from plotting.image import ImagePlot
from plotting.ucc import CellCropper

# essential tasks:

class HighSeasAdventure(t.HasTraits):
    # traits of importance:
    # current image index
    selected_image = t.Int(0)
    # current cell index
    selected_cell = t.Int(0)
    # where plot data should come from
    active_data_source = t.Str("rawdata")
    # definition of any attribute or combination of attributes to be mapped
    
    
    def __init__(self, treasure_chest, *args, **kw):
        self.chest = treasure_chest

    def set_active_index(self, img_idx):
        if self.active_data_source is "rawdata":
            self.selected_image = img_idx
        elif self.active_data_source is 'cells':
            self.selected_cell = img_idx
            
    def get_active_data(self):
        nodes = self.chest.listNodes('/%s' % self.active_data_source)
        if self.active_data_source is 'rawdata':
            return nodes[self.selected_image]
        elif self.active_data_source is 'cells':
            return nodes[self.selected_cell]

    # get plots
    def spyglass(self):
        chaco_plot = ImagePlot(self)
        chaco_plot.configure_traits()
    # run analyses
        
    ## fire up cell cropper
    def cell_cropper(self):
        ui = CellCropper(self)
        ui.configure_traits()

    def _get_image_data(self, datatype, slab=[]):
        """
        Gets some slab of data from the HDF5 file
        @param rawdata: string; one of 
            'rawdata' - the collection of raw images
            'cells' - the cells cropped from the raw images
            'mda_image_results' - mda results (eigenimages and scores) from the raw images
            'mda_cells_results' - mda results (eigenimages and scores) from the cell stacks
        @param slab: list of tuples; the first is the origin to start slicing from; the second 
            is the coordinate to slice to.
            for example, given a 3D stack, dimensions (10, 512, 512), which would be a stack of 512x512 images, 10 deep:
            slab = [(0,0,0), (5,512,512)]  # will give you the first five images
            slab = [(0,128,128), (10, 384, 384)] #will give you the central 256x256 area of the whole stack
        """
        pass
    
    def plot_images():
        _img_plot(window = main_window, data = _get_image_data("rawdata"))

    def plot_cells():
        _img_plot(window = main_window, data = _get_image_data("cells"))