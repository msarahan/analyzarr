from traits.api import Instance, Range, Dict, Bool, Int, String, \
     on_trait_change
from BaseImage import BaseImageController

from chaco.default_colormaps import gray
from chaco.api import ArrayPlotData, BasePlotContainer, Plot

from analyzarr import peak_char as pc
from analyzarr import cv_funcs
from analyzarr.file_import import filters
from analyzarr import data_structure

import numpy as np
import tables as tb

from enaml.application import Application

class CellCropController(BaseImageController):
    zero=Int(0)
    template_plot = Instance(BasePlotContainer)
    template_data = Instance(ArrayPlotData)
    template_size = Range(low=2, high=512, value=64, cols=4)
    template_top = Range(low='zero',high='max_pos_y', value=20, cols=4)
    template_left = Range(low='zero',high='max_pos_x', value=20, cols=4)
    peaks = Dict({})
    ShowCC = Bool(False)
    max_pos_x = Int(256)
    max_pos_y = Int(256)
    is_square = Bool(True)
    peak_width = Range(low=2, high=200, value=10)
    numpeaks_total = Int(0,cols=5)
    numpeaks_img = Int(0,cols=5)
    _session_id = String('')

    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', 
                 *args, **kw):
        super(CellCropController, self).__init__(parent, treasure_chest, 
                                                 data_path, *args, **kw)
        
        if self.chest is not None:
            self.numfiles = len(self.nodes)
            if self.numfiles > 0:
                self.init_plot()
                print "initialized plot for data in %s" % data_path
    
    def data_updated(self):
        # reinitialize data
        self.__init__(parent = self.parent, treasure_chest=self.chest,
                      data_path=self.data_path)
        
    
    def init_plot(self):
        self.plotdata.set_data('imagedata', self.get_active_image())
        self.plot = self.get_scatter_overlay_plot(array_plot_data=self.plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name(),
                tool='colorbar',
                    )
        # pick an initial template with default parameters
        self.template_data = ArrayPlotData()
        self.template_plot = Plot(self.template_data, default_origin="top left")
        self.template_data.set_data('imagedata',
                    self.get_active_image()[
                        self.template_top:self.template_top + self.template_size,
                        self.template_left:self.template_left + self.template_size
                    ]
                    )
        self.template_plot.img_plot('imagedata', title = "Template")
        self.template_plot.aspect_ratio=1 #square templates
        self._get_max_positions()

    @on_trait_change("selected_index, ShowCC")
    def update_image(self):
        if self.ShowCC:
            CC = cv_funcs.xcorr(self.template_data.get_data('imagedata'),
                                     self.get_active_image())
            self.plotdata.set_data("imagedata",CC)
            self.set_plot_title("Cross correlation of " + self.get_active_name())
            grid_data_source = self._base_plot.range2d.sources[0]
            grid_data_source.set_data(np.arange(CC.shape[1]), 
                                      np.arange(CC.shape[0]))
        else:            
            self.plotdata.set_data("imagedata", self.get_active_image())
            self.set_plot_title("%s of %s: " % (self.selected_index + 1,
                                          self.numfiles) + self.get_active_name())
            grid_data_source = self._base_plot.range2d.sources[0]
            grid_data_source.set_data(np.arange(self.get_active_image().shape[1]), 
                                      np.arange(self.get_active_image().shape[0]))

    @on_trait_change('template_left, template_top, template_size')
    def update_template_data(self):
        self.template_data.set_data('imagedata',
                    self.get_active_image()[
                        self.template_top:self.template_top + self.template_size,
                        self.template_left:self.template_left + self.template_size
                    ]
                    )
        if self.numpeaks_total>0:
            print "clearing peaks"
            self.peaks={}

    def add_cursor_tool(self):    
        self._csr = CursorTool(self._base_plot, drag_button='left', color='white',
                                 line_width=2.0)
        self._base_plot.overlays.append(self._csr)
    
    @on_trait_change('selected_index, template_size')
    def _get_max_positions(self):
        max_pos_x=self.get_active_image().shape[-1]-self.template_size-1
        if max_pos_x>0:
            self.max_pos_x = int(max_pos_x)
        max_pos_y=self.get_active_image().shape[-2]-self.template_size-1
        if max_pos_y>0:
            self.max_pos_y = int(max_pos_y)

    @on_trait_change('template_left, template_top')
    def update_csr_position(self):
        #if self.template_left>0:        
            #self._csr.current_position=self.template_left,self.template_top
        pass

    @on_trait_change('_csr:current_position')
    def update_top_left(self):
        if self._csr.current_position[0]>0 or self._csr.current_position[1]>0:
            if self._csr.current_position[0]>self.max_pos_x:
                if self._csr.current_position[1]<self.max_pos_y:
                    self.template_top=self._csr.current_position[1]
                else:
                    self._csr.current_position=self.max_pos_x, self.max_pos_y
            elif self._csr.current_position[1]>self.max_pos_y:
                self.template_left,self.template_top=self._csr.current_position[0],self.max_pos_y
            else:
                self.template_left,self.template_top=self._csr.current_position

    @on_trait_change('_colorbar_selection:selection')
    def update_thresh(self):
        try:
            thresh=self._colorbar_selection.selection
            self.thresh=thresh
            scatter_renderer=self._scatter_plot.plots['scatter_plot'][0]
            scatter_renderer.color_data.metadata['selections']=thresh
            self.thresh_lower=thresh[0]
            self.thresh_upper=thresh[1]
            scatter_renderer.color_data.metadata_changed={'selections':thresh}
            self.plot.request_redraw()
        except:
            pass

    @on_trait_change('thresh_upper,thresh_lower')
    def manual_thresh_update(self):
        self.thresh=[self.thresh_lower,self.thresh_upper]
        scatter_renderer=self._scatter_plot.plots['scatter_plot'][0]
        scatter_renderer.color_data.metadata['selections']=self.thresh
        scatter_renderer.color_data.metadata_changed={'selections':self.thresh}
        self.plot.request_redraw()

    @on_trait_change('peaks, _colorbar_selection:selection, selected_index')
    def calc_numpeaks(self):
        try:
            thresh=self._colorbar_selection.selection
            self.thresh=thresh
        except:
            thresh=[]
        if thresh==[] or thresh==() or thresh==None:
            thresh=(-1,1)
        self.numpeaks_total=int(np.sum([np.sum(np.ma.masked_inside(
            self.peaks[image_id][:,2], thresh[0], thresh[1]).mask) 
                                        for image_id in self.peaks.keys()
                                        ]
                                       )
                                )
        try:
            self.numpeaks_img=int(np.sum(np.ma.masked_inside(
                self.peaks[self.get_active_name()][:,2],
                thresh[0],thresh[1]).mask))
        except:
            self.numpeaks_img=0

    @on_trait_change('peaks, selected_index')
    def update_scatter_plot(self):
        if self.get_active_name() in self.peaks:
            self.plotdata.set_data("index",self.peaks[self.get_active_name()][:,0])
            self.plotdata.set_data("value",self.peaks[self.get_active_name()][:,1])
            self.plotdata.set_data("color",self.peaks[self.get_active_name()][:,2])
            self.plot = self.get_scatter_overlay_plot(array_plot_data=self.plotdata,
                                                      tool='colorbar',
                                                      )
            scatter_renderer = self._scatter_plot.plots['scatter_plot'][0]
            scatter_renderer.color_data.metadata['selections']=self.thresh
            scatter_renderer.color_data.metadata_changed={'selections':self.thresh}
        else:
            if 'index' in self.plotdata.arrays:
                self.plotdata.del_data('index')
                # value will implicitly exist if value exists.
                self.plotdata.del_data('value')
            if 'color' in self.plotdata.arrays:
                self.plotdata.del_data('color')
            self.plot = self.get_scatter_overlay_plot(array_plot_data=self.plotdata,
                                                      tool=None,
                                                      )
            
    def locate_peaks(self):
        peaks={}
        for idx in xrange(self.numfiles):
            self.set_active_index(idx)
            CC = cv_funcs.xcorr(self.template_data.get_data("imagedata"),
                                    self.get_active_image())
            # peak finder needs peaks greater than 1.  Multiply by 255 to scale them.
            pks=pc.two_dim_findpeaks(CC*255, peak_width=self.peak_width, medfilt_radius=None)
            pks[:,2]=pks[:,2]/255.
            peaks[self.get_active_name()]=pks
        self.peaks=peaks
        
    def mask_peaks(self,image_id):
        mpeaks=np.ma.asarray(self.peaks[image_id])
        mpeaks[:,2]=np.ma.masked_outside(mpeaks[:,2],self.thresh[0],self.thresh[1])
        return mpeaks

    def crop_cells(self):
        rows = self.chest.root.cell_description.nrows
        if rows > 0:
            # remove the table
            self.chest.removeNode('/cell_description')
            try:
                # remove the table of peak characteristics - they are not valid.
                self.chest.removeNode('/cell_peaks')
            except:
                pass
            # recreate it
            self.chest.createTable('/', 'cell_description', 
                                   data_structure.CellsTable)
            # remove all existing entries in the data group
            for node in self.chest.listNodes('/cells'):
                self.chest.removeNode('/cells/' + node.name)
        # store the template
        template_data = self.template_data.get_data('imagedata')
        template_array = self.chest.createCArray(self.chest.root.cells,
                                             'template',
                                             tb.Atom.from_dtype(template_data.dtype),
                                             template_data.shape,
                                             filters = filters,
                                             )
        template_array[:] = template_data
        # TODO: set attribute that tells where the template came from
        row = self.chest.root.cell_description.row
        average_data = np.zeros(template_data.shape, dtype=template_data.dtype)
        for idx in xrange(self.numfiles):
            # filter the peaks that are outside the selected threshold
            self.set_active_index(idx)
            active_image = self.get_active_image()
            peaks=np.ma.compress_rows(self.mask_peaks(self.get_active_name()))
            tmp_sz=self.template_size
            data=np.zeros((peaks.shape[0],tmp_sz,tmp_sz), 
                          dtype=active_image.dtype)
            if data.shape[0] >0:
                for i in xrange(peaks.shape[0]):
                    # store the peak in the table
                    row['file_idx'] = i
                    row['input_data'] = self.data_path
                    row['filename'] = self.get_active_name()
                    row['x_coordinate'] = peaks[i, 1]
                    row['y_coordinate'] = peaks[i, 0]
                    row.append()
                    # crop the cells from the given locations
                    data[i,:,:]=active_image[peaks[i, 1]:peaks[i, 1] + tmp_sz,
                                      peaks[i, 0]:peaks[i, 0] + tmp_sz]
                average_data += np.average(data, axis=0)
                # insert the data (one 3d array per file)
                cell_array = self.chest.createCArray(self.chest.root.cells,
                                        self.get_active_name(),
                                        tb.Atom.from_dtype(data.dtype),
                                        data.shape,
                                        filters = filters,
                                        )
                cell_array[:] = data
                self.chest.root.cell_description.flush()
                self.chest.flush()
        average_data /= self.numfiles
        average_array = self.chest.createCArray(self.chest.root.cells,
                                                 'average',
                                                 tb.Atom.from_dtype(average_data.dtype),
                                                 average_data.shape,
                                                 filters = filters,
                                                 )
        average_array[:] = average_data
        self.chest.flush()
        self.parent.update_cell_data()
        Application.instance().end_session(self._session_id)
