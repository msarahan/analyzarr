from traits.api import Int, Bool
from analyzarr.ui.renderers import HasRenderer

class ControllerBase(HasRenderer):
    # current image index
    selected_index = Int(0)
    numfiles = Int(0)
    _can_save = Bool(False)
    _can_change_idx = Bool(False)

    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', *args, **kw):
        super(ControllerBase, self).__init__(*args, **kw)
        self.chest = None
        self.numfiles = 0
        self.data_path = data_path
        self.parent = parent
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.nodes = self.chest.listNodes(data_path)

    # used by the cell cropper
    def set_active_index(self, idx):
        self.selected_index = idx

    def increase_selected_index(self):
        if self.selected_index == (self.numfiles - 1):
            self.selected_index = 0
        else:
            self.selected_index += 1

    def decrease_selected_index(self):
        if self.selected_index == 0:
            self.selected_index = int(self.numfiles - 1)
        else:
            self.selected_index -= 1

    # TODO: this is for defining MDA's kind of data it's handling.  It might
    #   eventually be used for spectroscopy data.
    def get_active_data_type(self):
        return "image"

    def _get_image_data(self, datatype, slab=[]):
        """
        Gets some slab of data from the HDF5 file
        @param rawdata: string; one of:
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
