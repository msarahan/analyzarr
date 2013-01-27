# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import traits.api as t
from traits.api import on_trait_change
from data_structure import filters
import tables as tb
import numpy as np
from lib.mda import mda_sklearn as mda

import cv_funcs
import peak_char as pc

from chaco.default_colormaps import gray
from chaco.api import ArrayPlotData, BasePlotContainer, Plot

from ui.renderers import HasRenderer
import file_import

class ControllerBase(HasRenderer):
    # current image index
    selected_index = t.Int(0)

    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', *args, **kw):
        super(ControllerBase, self).__init__(*args, **kw)
        self.chest = None
        self.numfiles = 0
        self.data_path = data_path
        self.parent = parent
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.nodes = self.chest.listNodes(data_path)
            self.numfiles = len(self.nodes)

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

class BaseImageController(ControllerBase):
    plot = t.Instance(BasePlotContainer)
    plotdata = t.Instance(ArrayPlotData)
    show_crop_ui = t.Bool(False)

    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', *args, **kw):
        super(BaseImageController, self).__init__(parent, treasure_chest, data_path,
                                              *args, **kw)
        self.plotdata = ArrayPlotData()
        if self.numfiles > 0:
            self.init_plot()
            print "initialized plot for data in %s" % data_path

    def init_plot(self):
        self.plotdata.set_data('imagedata', self.get_active_image())
        self.plot = self.get_simple_image_plot(array_plot_data = self.plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name()
                )

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
        return self.nodes[self.selected_index].name
    
    @t.on_trait_change("selected_index")
    def update_image(self):
        self.plotdata.set_data("imagedata", self.get_active_image())
        self.set_plot_title("%s of %s: " % (self.selected_index + 1,
                                          self.numfiles) + self.get_active_name())
        
class CellController(BaseImageController):
    def __init__(self, parent, treasure_chest=None, data_path='/cells', *args, **kw):
        super(CellController, self).__init__(parent, treasure_chest, data_path,
                *args, **kw)
        if self.chest is not None:
            self.numfiles = self.chest.root.cell_description.nrows
            if self.numfiles > 0:
                self.init_plot()
                print "initialized plot for data in %s" % data_path

    def data_updated(self):
        # reinitialize data
        self.__init__(parent = self.parent, treasure_chest=self.chest,
                      data_path=self.data_path)

    def get_active_image(self):
        # Find this cell in the cell description table.  We use this to look
        # up the parent image and subsequently the local cell index (the
        # index among only the cells from that image)
        cell_record = self.chest.root.cell_description.read(
                            start=self.selected_index,
                            stop=self.selected_index + 1)[0]
        # find the parent that this cell comes from
        parent = cell_record['original_image']
        # select that parent as the selected image (int because it is an index)
        selected_image = int([x['idx'] for x in
                                       self.chest.root.image_description.where(
                                       'filename == "%s"' % parent)][0])

        # return the cell data - the index is the index of this cell
        #    among only its indexed cells - not the universal index!
        return self.nodes[selected_image][cell_record['idx'], :, :]

    def get_active_name(self):
        cell_record = self.chest.root.cell_description.read(
                            start=self.selected_index,
                            stop=self.selected_index + 1)[0]
        # find the parent that this cell comes from
        parent = cell_record['original_image']
        return '(from %s)' % parent

    def get_num_files(self):
        return self.chest.root.cell_description.nrows

    def characterize(self, peak_width, subpixel=False,
                     target_locations=None, peak_locations=None,
                     target_neighborhood=20, medfilt_radius=5):
        # get the peak attributes
        attribs = pc.peak_attribs_stack(self.get_cell_set(),
                        peak_width=peak_width, subpixel=subpixel,
                        target_locations=target_locations,
                        peak_locations=peak_locations,
                        target_neighborhood=target_neighborhood,
                        medfilt_radius=medfilt_radius)
        # transpose the results - they come in the form of one column per image
        #    Should be one row per image.
        attribs = attribs.T
        # generate a list of column names
        names = [('x%i, y%i, dx%i, dy%i, h%i, o%i, e%i' % ((x,)*7)).split(', ') for x in xrange(attribs.shape[1]//7)]
        # flatten that from a list of lists to a simple list
        names = [item for sublist in names for item in sublist]
        # make tuples of each column name and 'f8' for the data type
        dtypes = zip(names, ['f8', ] * attribs.shape[1])
        # prepend the index column
        dtypes = [('idx', "i4"), ] + dtypes
        # make a blank recarray with our column names and dtypes
        data = np.zeros((attribs.shape[0]), dtype=dtypes)
        # fill in the index column
        data['idx'] = np.arange(attribs.shape[0])
        # for each column name, copy in the data
        for name_idx in xrange(len(names)):
            data[names[name_idx]] = attribs[:, name_idx]
        # populate a table with the results
        self.chest.createTable(self.chest.root,
                               'cell_peaks', description=data)
        # add an attribute for the total number of peaks recorded
        self.chest.root.cell_peaks.number_of_peaks = attribs.shape[1] // 7
        #self.chest.root.cell_peaks.append([data[idx] for idx in xrange(1,attribs.shape[0])])
        self.chest.root.cell_peaks.flush()

    def get_peak_data(self, chars=[], indices=[]):
        """
        Get peak data from the table of peak data.

        Input:
        chars - a list of characteristic names (as string letters).
            For example, ['dx', 'dy', 'h'] selects x and y deviation from 
            average peak position and the peak height.
            
            Possible options include:
            x - the x position of a peak in a cell
            y - the y position of a peak in a cell
            dx - the difference between the x position of the peak in this cell
                 and the x position of the same peak in the average cell
            dy - the difference between the y position of the peak in this cell
                 and the y position of the same peak in the average cell
            h - the height of the peak
            o - if a peak is not perfectly symmetric, the orientation of the peak.
            e - the eccentricity of a peak.  i.e. how egg-shaped is it?
            
        indices - peak indices (integers) to select from.  Use this if you want to compare
            only a few peaks in the cell structure to compare.
            None selects all peaks.
        """
        if len(chars) > 0:
            if len(indices) is 0:
                indices = range(self.chest.root.cell_peaks.number_of_peaks)
            # the columns we get are the combination of the chars with the
            #   indices we want.
            cols = [['%s%i' % (c, i) for i in indices] for c in chars]
        else:
            chars = ['x', 'y', 'dx', 'dy', 'h', 'o', 'e']
            if len(indices) is 0:
                indices = range(self.chest.root.cell_peaks.number_of_peaks)
            # the columns we get are the combination of the chars with the
            #   indices we want.
            cols = [['%s%i' % (c, i) for c in chars] for i in indices]
        # make the cols a simple list, rather than a list of lists
        cols = [item for sublist in cols for item in sublist]
        # get the data from the table
        peak_data = self.chest.root.cell_peaks[:]
        # return an ndarray with only the selected columns
        return np.array(peak_data[cols]).view(float).reshape(len(cols), -1)


class MDAController(ControllerBase):
    # the image data for the factor plot (including any scatter data and
    #    quiver data)
    factor_plotdata = ArrayPlotData
    # the actual plot object
    factor_plot = t.Instance(BasePlotContainer)
    # the image data for the score plot (may be a parent image for scatter overlays)
    score_plotdata = ArrayPlotData
    score_plot = t.Instance(BasePlotContainer)

    def __init__(self, treasure_chest=None, data_path='/mda_results',
                 *args, **kw):
        super(ControllerBase, self).__init__(*args, **kw)
        self.factor_plotdata = ArrayPlotData()
        self.score_plotdata = ArrayPlotData()
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.data_path = data_path
            # TODO: this is not a good way to do things.  MDA is split with
            #   two descriptors - the type of mda, then the date it was done.
            #   perhaps only do by date it was done?
            self.nodes = self.chest.listNodes(data_path)
            self.numfiles = self.chest.root.mda_description.nrows
            if self.numfiles > 0:
                self.init_plots()

    # TODO: need to rethink how to set_data for these things, since we have so
    #    many different places to put data.
    def init_plots(self):
        self.factor_plotdata.set_data('imagedata',
                                      self.get_active_factor_image())
        self.factor_plotdata.set_data('imagedata',
                                      self.get_active_score_image())
        self.factor_plot = self.render_factor_plot(
                img_data=self.factor_plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name()
                )
        self.score_plot = self.render_score_plot(
                img_data=self.score_plotdata, scatter_data=self.score_plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name()
                )

    @t.on_trait_change("selected_index")
    def update_image(self):
        # TODO: customize this to change the factor data and plot data
        self.plotdata.set_data("imagedata", self.get_active_image())
        self.set_plot_title("%s of %s: " % (self.selected_index + 1,
                                          self.numfiles) + self.get_active_name())

    ######
    #  Analysis methods each create their own member under the group of MDA
    #  results in the chest.
    ######
    def PCA(self, n_components=None):
        self._create_new_context("PCA")

        active_data = self.get_active_image_set()
        data = active_data.reshape((active_data.shape[0], -1))
        factors, scores , eigenvalues = mda.PCA(data, n_components=n_components)
        factors, scores = self._reshape_MDA_results(active_data, factors, scores)
        fs = self.chest.createCArray(self.context, 'Factors',
                                     tb.Atom.from_dtype(factors.dtype),
                                     factors.shape,
                                     filters=filters
                                     )
        ss = self.chest.createCArray(self.context, 'Scores',
                                     tb.Atom.from_dtype(scores.dtype),
                                     scores.shape,
                                     filters=filters
                                     )
        ev = self.chest.createCArray(self.context, 'Eigenvalues',
                                     tb.Atom.from_dtype(eigenvalues.dtype),
                                     eigenvalues.shape,
                                     filters=filters
                                     )
        fs[:] = factors
        ss[:] = scores
        ev[:] = eigenvalues
        self.chest.flush()
        return factors, scores, eigenvalues
        # stash the results under the group of MDA results
        #   attribs:
        #   - analysis type
        #   - number of components
        #   - whitening applied
        # store the mean of each column - we use this for reconstruction later

    def ICA(self, n_components, whiten=False, max_iter=10):
        from scipy import integrate
        self._create_new_context("ICA")
        # reshape the data:
        #   The goal is always to have the variables (pixels in an image,
        #     energy channels in a spectrum) always as columns in a 2D array.
        #     The rows are made up of observations.  For example, in
        #     images, the rows are individual cells.  In SIs, the rows
        #     are pixels where spectra were gathered.
        # for images, the cell idx is dim 0
        data = self.data_controller.active_data_cube.reshape(
            (self.active_data.shape[0], -1))
        # for spectra, the energy index is dim 0.
        #data = spectrum_data.reshape((-1, data.shape[0]
        """
        Pre-processes the data to be ready for ICA.  Namely:
          differentiates the data (integrated ICA)
        """
        diffdata = data.copy()
        deriv_kernel = np.array([-1, 0, 0, 0, 0, 0, 1])
        for i in xrange(data.shape[1]):
            diffdata[:, i] = np.convolve(data[:, i], deriv_kernel)[3:-3]
        factors, scores = mda.ICA(diffdata, n_components=n_components)

        # integration undoes the differentiation done in the ICA data prep.
        factors = np.array([integrate.cumtrapz(factors[:, i])
                            for i in xrange(factors.shape[1])]).T
        factors, scores = self._reshape_MDA_results(
                            self.data_controller.active_data_cube,
                            factors, scores)
        fs = self.chest.createCArray(self.context, 'Factors',
                                     tb.Atom.from_dtype(factors.dtype),
                                     factors.shape,
                                     filters=filters
                                     )
        ss = self.chest.createCArray(self.context, 'Scores',
                                     tb.Atom.from_dtype(scores.dtype),
                                     scores.shape,
                                     filters=filters
                                     )
        fs[:] = factors
        ss[:] = scores
        self.chest.flush()
        return factors, scores

    def _reshape_MDA_results(self, data, factors, scores):
        # we need to reshape the factors and scores to make sense.
        # for images, the factors are themselves images, while the scores are
        # line plots with one column per component.
        if self.get_active_data_type() is "image":
            factors = factors.reshape((-1, data.shape[-2], data.shape[-1]))
            factors.squeeze()
            scores.reshape((data.shape[0], -1))
        # for SIs, the factors are spectra, while the scores are images.
        elif ((self.get_active_data_type() is "spectrum") or
                (self.get_active_data_type() is "peaks")):
            factors = factors.reshape((data.shape[0], -1))
            scores = scores.reshape((-1, data.shape[-2], data.shape[-1]))
            scores.squeeze()
        return factors, scores

    def _create_new_context(self, MDA_type):
        import time
        # first add an entry to our table of analyses performed
        datestr = MDA_type + time.strftime("_%Y-%m-%d %H:%M", time.localtime())
        data_record = self.chest.root.mda_description.row
        data_record['date'] = datestr
        data_record['mda_type'] = MDA_type
        data_record['input_data'] = self.data_controller.summarize_data()
        #data_record['treatments'] = self.data_controller.summarize
        data_record.append()
        # If this MDA type hasn't been done yet, add a member of the MDA group
        #   for this type.
        self.chest.createGroup
        # Set this instance's data as members of a group for the time right now
        # this is where the factors and scores result arrays will be stored.
        self.chest.flush()
        # context is a pytables group.  It has attributes for informational
        #   data, as well as being the container for any outputs.
        self.context = "/mda_results/%s/%s" % (MDA_type, datestr)

class CellCropController(BaseImageController):
    zero=t.Int(0)
    template_plot = t.Instance(BasePlotContainer)
    template_data = t.Instance(ArrayPlotData)
    template_size = t.Range(low=2, high=512, value=64, cols=4)
    template_top = t.Range(low='zero',high='max_pos_y', value=20, cols=4)
    template_left = t.Range(low='zero',high='max_pos_x', value=20, cols=4)
    peaks = t.Dict({})
    ShowCC = t.Bool(False)
    max_pos_x = t.Int(256)
    max_pos_y = t.Int(256)
    is_square = t.Bool(True)
    peak_width = t.Range(low=2, high=200, value=10)
    numpeaks_total = t.Int(0,cols=5)
    numpeaks_img = t.Int(0,cols=5)
    
    # todo - we'll probably need to define this
    #csr=t.Instance(BaseCursorTool)

    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', *args, **kw):
        super(CellCropController, self).__init__(parent, treasure_chest, data_path,
                                              *args, **kw)
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
                                      self.numfiles) + self.get_active_name()
                    )
        # pick an initial template with default parameters
        self.template_data = ArrayPlotData()
        self.template_plot = Plot(self.template_data)        
        self.template_data.set_data('imagedata',
                    self.get_active_image()[
                        self.template_top:self.template_top + self.template_size,
                        self.template_left:self.template_left + self.template_size
                    ]
                    )
        self.template_plot.img_plot('imagedata', title = "Template")
        self.template_plot.aspect_ratio=1 #square templates

    @t.on_trait_change("selected_index, ShowCC")
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
        if self.peaks.has_key(self.get_active_name()):
            self.plotdata.set_data("index",self.peaks[self.get_active_name()][:,0])
            self.plotdata.set_data("value",self.peaks[self.get_active_name()][:,1])
            self.plotdata.set_data("color",self.peaks[self.get_active_name()][:,2])
        else:
            if 'index' in self.plotdata.arrays:
                self.plotdata.del_data('index')
                # value will implicitly exist if value exists.
                self.plotdata.del_data('value')
            if 'color' in self.plotdata.arrays:
                self.plotdata.del_data('color')

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
            self.peaks=[np.array([[0,0,-1]])]
        self.update_CC()        

    def add_cursor_tool(self):    
        self.csr = CursorTool(self._base_plot, drag_button='left', color='white',
                                 line_width=2.0)
        self._base_plot.overlays.append(self.csr)
    
    @t.on_trait_change('selected_index, template_size')
    def _get_max_pos_x(self):
        max_pos_x=self.get_active_image().shape[-1]-self.template_size-1
        if max_pos_x>0:
            return max_pos_x
        else:
            return None

    @t.on_trait_change('selected_index, template_size')
    def _get_max_pos_y(self):
        max_pos_y=self.get_active_image().shape[-2]-self.template_size-1
        if max_pos_y>0:
            return max_pos_y
        else:
            return None

    @t.on_trait_change('template_left, template_top')
    def update_csr_position(self):
        #if self.template_left>0:        
            #self.csr.current_position=self.template_left,self.template_top
        pass

    @t.on_trait_change('csr:current_position')
    def update_top_left(self):
        if self.csr.current_position[0]>0 or self.csr.current_position[1]>0:
            if self.csr.current_position[0]>self.max_pos_x:
                if self.csr.current_position[1]<self.max_pos_y:
                    self.template_top=self.csr.current_position[1]
                else:
                    self.csr.current_position=self.max_pos_x, self.max_pos_y
            elif self.csr.current_position[1]>self.max_pos_y:
                self.template_left,self.template_top=self.csr.current_position[0],self.max_pos_y
            else:
                self.template_left,self.template_top=self.csr.current_position

    @t.on_trait_change('_colorbar_selection:selection')
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

    @t.on_trait_change('thresh_upper,thresh_lower')
    def manual_thresh_update(self):
        self.thresh=[self.thresh_lower,self.thresh_upper]
        scatter_renderer=self._scatter_plot.plots['scatter_plot'][0]
        scatter_renderer.color_data.metadata['selections']=self.thresh
        scatter_renderer.color_data.metadata_changed={'selections':self.thresh}
        self.plot.request_redraw()

    @on_trait_change('peaks, _colorbar_selection:selection, selected_index')
    def calc_numpeaks(self):
        try:
            thresh=self.cbar_selection.selection
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

    @on_trait_change('peaks')
    def update_scatter_plot(self):
        self.plotdata.set_data("index",self.peaks[self.get_active_name()][:,0])
        self.plotdata.set_data("value",self.peaks[self.get_active_name()][:,1])
        self.plotdata.set_data("color",self.peaks[self.get_active_name()][:,2])
        self.plot = self.get_scatter_overlay_plot(array_plot_data=self.plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name()
                    )
        scatter_renderer = self._scatter_plot.plots['scatter_plot'][0]
        scatter_renderer.color_data.metadata['selections']=self.thresh
        scatter_renderer.color_data.metadata_changed={'selections':self.thresh}
        self.update_image()
    

    def locate_peaks(self):
        peaks={}
        #progress = ProgressDialog(title="Peak finder progress", 
        #               message="Finding peaks on %s images" % self.numfiles,
        #               max=self.numfiles, show_time=True, can_cancel=False)
        #progress.open()
        for idx in xrange(self.numfiles):
            self.set_active_index(idx)
            CC = cv_funcs.xcorr(self.template_data.get_data("imagedata"),
                                    self.get_active_image())
            # peak finder needs peaks greater than 1.  Multiply by 255 to scale them.
            pks=pc.two_dim_findpeaks(CC*255, peak_width=self.peak_width, medfilt_radius=None)
            pks[:,2]=pks[:,2]/255.
            peaks[self.get_active_name()]=pks
            #progress.update(idx+1)
        #ipdb.set_trace()
        self.peaks=peaks
        
    def mask_peaks(self,image_id):
        #thresh=self.colorbar_selection.selection
        #if thresh==[]:
        #    thresh=(-1,1)
        mpeaks=np.ma.asarray(self.peaks[image_id])
        mpeaks[:,2]=np.ma.masked_outside(mpeaks[:,2],self.thresh[0],self.thresh[1])
        return mpeaks

    def crop_cells(self):
        if self.chest.root.cell_description.nrows > 0:
            # clear the table of peaks
            self.chest.root.cell_description.removeRows(0,-1)
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
        for idx in xrange(self.numfiles):
            # filter the peaks that are outside the selected threshold
            self.set_active_index(idx)
            active_image = self.get_active_image()
            peaks=np.ma.compress_rows(self.mask_peaks(self.get_active_name()))
            tmp_sz=self.template_size
            data=np.zeros((peaks.shape[0],tmp_sz,tmp_sz))
            if data.shape[0] >0:
                for i in xrange(peaks.shape[0]):
                    # store the peak in the table
                    row['idx'] = i
                    row['input_data'] = self.data_path
                    row['original_image'] = self.get_active_name()
                    row['x_coordinate'] = peaks[i, 1]
                    row['y_coordinate'] = peaks[i, 0]
                    row.append()
                    # crop the cells from the given locations
                    data[i,:,:]=active_image[peaks[i, 1]:peaks[i, 1] + tmp_sz,
                                      peaks[i, 0]:peaks[i, 0] + tmp_sz]
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
        self.parent.update_cell_data()
                
# the UI controller
class HighSeasAdventure(t.HasTraits):
    show_image_view = t.Bool(True)
    show_cell_view = t.Bool(False)
    show_score_view = t.Bool(False)
    show_factor_view = t.Bool(False)

    image_controller = t.Instance(BaseImageController)
    cell_controller = t.Instance(CellController)
    crop_controller = t.Instance(CellCropController)

    # TODO: need method for opening files

    def __init__(self, *args, **kw):
        super(HighSeasAdventure, self).__init__(*args, **kw)
        self.image_controller = BaseImageController(parent=self)
        self.cell_controller = CellController(parent=self)
        self.crop_controller = CellCropController(parent=self)
        self.chest = None

    def update_cell_data(self):
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=self.chest)
        
    def update_image_data(self):
        self.image_controller.data_updated()
        self.crop_controller.data_updated()

    def open_treasure_chest(self, filename):
        if self.chest is not None:
            self.chest.close()
        chest = file_import.open_treasure_chest(filename)
        self.image_controller = BaseImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=chest)
        self.crop_controller = CellCropController(parent=self, 
                                                  treasure_chest=chest)
        self.chest = chest

    def import_files(self, file_list):
        chest = file_import.import_files(file_list)
        self.image_controller = BaseImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self,
                                              treasure_chest=chest)
        self.crop_controller = CellCropController(parent=self,
                                                  treasure_chest=chest)
        self.chest = chest

    def import_image(self):
        pass

    def new_project(self):
        #new_file =
        self.image_controller = ImageController()

    def add_cells(self, name, data, locations):
        ds = self.chest.createCArray(self.chest.root.cells,
                                    name,
                                    tb.Atom.from_dtype(data.dtype),
                                    data.shape,
                                    filters=filters
                                    )
        ds[:] = data
        self.chest.flush()

        loc = self.chest.root.cell_description.row

        for idx in xrange(locations.shape[0]):
            loc['idx'] = idx
            # TODO: generalize so that data can come from anywhere
            loc['input_data'] = '/root/rawdata'
            loc['original_image'] = name
            loc['x_coordinate'] = locations[idx, 0]
            loc['y_coordinate'] = locations[idx, 1]
            loc.append()
        self.chest.root.cell_description.flush()
        self.chest.flush()
        #self.active_data_source = 'cells'

if __name__ == '__main__':
    import enaml
    from enaml.stdlib.sessions import simple_session
    from enaml.qt.qt_application import QtApplication
    with enaml.imports():
        from main_view import Main
    qtapp = QtApplication([])
    session = simple_session('bonerfart', 'The main UI window', Main)
    qtapp.add_factories([session])
    qtapp.start_session('bonerfart')
    qtapp.start()
