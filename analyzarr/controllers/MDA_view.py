from chaco.api import ArrayPlotData, BasePlotContainer, Plot
from traits.api import Instance, Bool, Int, List, String, Array, on_trait_change
from BaseImage import BaseImageController
import tables as tb
# how much to compress the data
from analyzarr.lib.io.data_structure import filters

import numpy as np

class MDAViewController(BaseImageController):
    # the image data for the factor plot (including any scatter data and
    #    quiver data)
    factor_plotdata = Instance(ArrayPlotData)
    # the actual plot object
    factor_plot = Instance(BasePlotContainer)
    # the image data for the score plot (may be a parent image for scatter overlays)
    score_plotdata = Instance(ArrayPlotData)
    score_plot = Instance(BasePlotContainer)
    component_index = Int(0)
    _selected_peak = Int(0)
    contexts = Array()
    context = String('')
    _selected_context = Int(0)

    def __init__(self, treasure_chest=None, data_path='/rawdata',
                 *args, **kw):
        super(MDAViewController, self).__init__(*args, **kw)
        self.factor_plotdata = ArrayPlotData()
        self.score_plotdata = ArrayPlotData()
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.data_path = data_path
            # populate the list of available contexts (if any)
            if self.chest.root.mda_description.nrows>0:
                self.contexts = self.chest.root.mda_description.col('context')
                self.context = str(self.contexts[self._selected_context])
                self.init_plots()
    
    def increase_selected_component(self):
        # TODO: need to measure dimensionality somehow (node attribute, or array size?)
        if self.component_index == (self.dimensionality - 1):
            self.component_index = 0
        else:
            self.component_index += 1
    
    def decrease_selected_component(self):
        if self.component_index == 0:
            self.component_index = int(self.dimensionality - 1)
        else:
            self.component_index -= 1    

    # TODO: need to rethink how to set_data for these things, since we have so
    #    many different places to put data.
    def init_plots(self):
        self.render_active_factor_image(self.context)
        self.render_active_score_image(self.context)

    def render_active_factor_image(self, context):
        if self.chest.getNodeAttr('/mda_results/'+context, 'on_peaks'):
            factors = self.chest.getNode('/mda_results/'+context+'/peak_factors')
            # return average cell image (will be overlaid with peak info)
            self.factor_plotdata.set_data('imagedata', 
                                          self.chest.root.cells.average[:])
            values = \
                factors.read(start = self.component_index,
                             stop = self.component_index+1,
                             step = 1,
                             field='x_coordinate',) \
                + \
                factors.read(start = self.component_index,
                             stop = self.component_index+1,
                             step = 1,
                             field='y%i'%self._selected_peak,)
            
            indices = \
                factors.read(start = self.component_index,
                             stop = self.component_index+1,
                             step = 1,
                             field='y_coordinate',) \
                + \
                factors.read(start = self.component_index,
                             stop = self.component_index+1,
                             step = 1,
                             field='x%i'%self._selected_peak,)
            self.plotdata.set_data('value', values)
            self.plotdata.set_data('index', indices)
            
            if self._show_shift:
                x_comp = factors.read(start = self.component_index,
                                      stop = self.component_index+1,
                                      step = 1,
                                      field='dx%i'%self._selected_peak,
                                      ).reshape((-1,1))
                y_comp = factors.read(start = self.component_index,
                                      stop = self.component_index+1,
                                      step = 1,
                                      field='dy%i'%self._selected_peak,
                                      ).reshape((-1,1))
                vectors = np.hstack((x_comp,y_comp))
                vectors *= self.shift_scale
                self.plotdata.set_data('vectors',vectors)            
            self.factor_plot = self.get_scatter_quiver_plot(self.factor_plotdata,
                                                          tool='inspector')
        else:
            factors = self.chest.getNode('/mda_results/'+context+'/image_factors')
            # return current factor image (MDA on images themselves)
            self.factor_plotdata.set_data('imagedata', 
                                          factors[self.component_index,:,:])
            # return current factor image (MDA on images themselves)
            self.factor_plot = self.get_simple_image_plot(self.factor_plotdata)
            
    def render_active_score_image(self, context):
        self.score_plotdata.set_data('imagedata', self.get_active_image())
        values = self.chest.root.cell_description.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='x_coordinate',)
    
        indices = self.chest.root.cell_description.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='y_coordinate',)
        if self.chest.getNodeAttr('/mda_results/'+context, 'on_peaks'):
            scores = self.chest.getNode('/mda_results/'+context+'/peak_scores')
            # if we're on peaks, then we can localize further, overlaying the
            #   score right on top of the peak it applies to.
            values += self.chest.root.cell_peaks.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='y%i'%self._selected_peak,)
            indices += self.chest.root.cell_peaks.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='x%i'%self._selected_peak,)            
        else:
            scores = self.chest.getNode('/mda_results/'+context+'/image_scores')
        color = scores.readWhere(
            'filename == "%s"' % self.get_active_name(),
            field='c%i' % self.component_index,
        )
        self.score_plotdata.set_data('index', values)
        self.score_plotdata.set_data('value', indices)
        self.score_plotdata.set_data('color', color)
        self.get_scatter_overlay_plot(self.score_plotdata, tool="colorbar")

    @on_trait_change("selected_index")
    def update_image(self):
        self.render_active_factor_image()
        self.render_active_score_image()
        # TODO: customize this to change the factor data and plot data
        self.factor_plotdata.set_data("imagedata", self.get_active_factor_image())
        self.set_factor_plot_title("Factor %s of %s: " % (self.selected_index + 1,
                                          self.numfactors) + self.get_active_name())
        self.score_plotdata.set_data("imagedata", self.get_active_score_image())
        self.set_score_plot_title("Score %s of %s: " % (self.selected_index + 1,
                                          self.numfactors) + self.get_active_name())