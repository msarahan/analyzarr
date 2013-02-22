from Base import ControllerBase
from chaco.api import ArrayPlotData, BasePlotContainer, Plot

from traits.api import Instance, on_trait_change
import numpy as np

class BaseImageController(ControllerBase):
    plot = Instance(BasePlotContainer)
    plotdata = Instance(ArrayPlotData)
    
    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', *args, **kw):
        super(BaseImageController, self).__init__(parent, treasure_chest, data_path,
                                              *args, **kw)
        self.plotdata = ArrayPlotData()
        self._can_save = True
        self._can_change_idx = True

    def init_plot(self):
        self.plotdata.set_data('imagedata', self.get_active_image())
        self.plot = self.get_simple_image_plot(array_plot_data = self.plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name()
                )
        
    def save_plot(self, filename):
        self._save_plot(self.plot, filename)

    def data_updated(self):
        # reinitialize data
        self.__init__(parent = self.parent, treasure_chest=self.chest,
                      data_path=self.data_path)

    # this is a 2D image for plotting purposes
    def get_active_image(self):
        nodes = self.chest.listNodes('/rawdata')
        return nodes[self.selected_index][:]

    # this is a potentially 3D image stack for feeding into analyses
    def get_active_image_set(self, names=None):
        # TODO: this isn't rational for non-3D data yet.
        if names is None:
            # query the raw data table for filenames
            nodes = self.chest.listNodes('/' + self.active_data_source)
            data = nodes[0][:]
            # collect all the cells
            for node in nodes[1:]:
                data = np.append(data, node[:], axis=0)
        else:
            # TODO: need to implement image selection
            data = None
        return data

    def get_active_name(self):
        nodes = self.chest.listNodes('/rawdata')
        return nodes[self.selected_index].name
    
    @on_trait_change("selected_index")
    def update_image(self):
        self.plotdata.set_data("imagedata", self.get_active_image())
        self.set_plot_title("%s of %s: " % (self.selected_index + 1,
                                          self.numfiles) + self.get_active_name())
