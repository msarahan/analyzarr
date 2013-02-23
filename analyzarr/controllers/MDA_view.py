from chaco.api import ArrayPlotData, BasePlotContainer, Plot
from traits.api import Instance, Bool, Int, List, String, Array, \
     Float, on_trait_change
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
    _selected_context = Int(-1)
    dimensionality = Int(1)
    _characteristics = List(["Height", "Orientation", "Eccentricity"])
    _characteristic = Int(0)    
    _show_shift = Bool(False)
    shift_scale = Float(1.0)   
    _can_map_peaks = Bool(False)

    def __init__(self, treasure_chest=None, data_path='/rawdata',
                 *args, **kw):
        super(MDAViewController, self).__init__(*args, **kw)
        self.factor_plotdata = ArrayPlotData()
        self.score_plotdata = ArrayPlotData()
        if treasure_chest is not None:
            self.numfiles = len(treasure_chest.listNodes(data_path))
            self.chest = treasure_chest
            self.data_path = data_path
            # populate the list of available contexts (if any)
            if self.chest.root.mda_description.nrows>0:
                self.contexts = self.chest.root.mda_description.col('context')
                self.context = str(self.contexts[self._selected_context])
                self.dimensionality = self.chest.getNodeAttr('/mda_results/'+self.context, 
                                                             'dimensionality')
                self.update_image()
    
    def _selected_context_changed(self):
        self.context = str(self.contexts[self._selected_context])
        self.dimensionality = self.chest.getNodeAttr('/mda_results/'+context, 
                                                     'dimensionality')
        
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

    def render_active_factor_image(self, context):
        if self.chest.getNodeAttr('/mda_results/'+context, 'on_peaks'):
            factors = self.chest.getNode('/mda_results/'+context+'/peak_factors')
            # return average cell image (will be overlaid with peak info)
            self.factor_plotdata.set_data('imagedata', 
                                          self.chest.root.cells.average[:])
            component = factors.read(start = self.component_index,
                             stop = self.component_index+1,
                             step = 1,)[:]
            numpeaks = self.chest.root.cell_peaks.getAttr('number_of_peaks')
            index_keys = ['x%i' % i for i in xrange(numpeaks)]
            value_keys = ['y%i' % i for i in xrange(numpeaks)]
            color_prefix = self._characteristics[self._characteristic][0].lower()
            color_keys = ['%s%i' % (color_prefix, i) for i in xrange(numpeaks)]
            values = np.array(component[value_keys]).view(float)
            indices = np.array(component[index_keys]).view(float)
            color = np.array(component[color_keys]).view(float)
            self.factor_plotdata.set_data('value', values)
            self.factor_plotdata.set_data('index', indices)
            self.factor_plotdata.set_data('color', color)
            
            if self._show_shift:
                shift_x_keys = ['dx%i' % i for i in xrange(numpeaks)]
                shift_y_keys = ['dy%i' % i for i in xrange(numpeaks)]
                x_comp = np.array(component[shift_x_keys]).view(float).reshape((-1,1))
                y_comp = np.array(component[shift_y_keys]).view(float).reshape((-1,1))
                vectors = np.hstack((x_comp,y_comp))
                vectors *= self.shift_scale
                self.factor_plotdata.set_data('vectors',vectors)            
            else:
                if 'vectors' in self.factor_plotdata.arrays:
                    self.factor_plotdata.del_data('vectors')
            self.factor_plot = self.get_scatter_quiver_plot(self.factor_plotdata,
                                                          tool='inspector')
            self._can_map_peaks=True
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
                field='y_coordinate',)
    
        indices = self.chest.root.cell_description.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='x_coordinate',)
        if self.chest.getNodeAttr('/mda_results/'+context, 'on_peaks'):
            scores = self.chest.getNode('/mda_results/'+context+'/peak_scores')          
        else:
            scores = self.chest.getNode('/mda_results/'+context+'/image_scores')
        color = scores.readWhere(
            'filename == "%s"' % self.get_active_name(),
            field='c%i' % self.component_index,
        )
        self.score_plotdata.set_data('index', values)
        self.score_plotdata.set_data('value', indices)
        self.score_plotdata.set_data('color', color)
        self.score_plot = self.get_scatter_overlay_plot(self.score_plotdata, tool="colorbar")

    @on_trait_change("selected_index, component_index, characteristic, _show_shift,\
                         shift_scale")
    def update_image(self):
        self.render_active_factor_image(self.context)
        self.render_active_score_image(self.context)
        
    def open_factor_save_UI(self):
        self.open_save_UI(plot_id = 'factor_plot')
    
    def open_score_save_UI(self):
        self.open_save_UI(plot_id = 'score_plot')