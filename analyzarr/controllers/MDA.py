from chaco.api import ArrayPlotData, BasePlotContainer, Plot
from traits.api import Instance, Bool, Int, List, String, on_trait_change
from Base import ControllerBase
import tables as tb
# how much to compress the data
from analyzarr.data_structure import filters

import numpy as np

try:
    import analyzarr.lib.mda.mda_rpy as mda
except:
    try:
        import analyzarr.lib.mda.mda_sklearn as mda        
        print "rpy not available; falling back to sklearn."
    except:
        raise NotImplementedError("No MDA methods functional")

from enaml.application import Application

class MDAController(ControllerBase):
    # the image data for the factor plot (including any scatter data and
    #    quiver data)
    factor_plotdata = Instance(ArrayPlotData)
    # the actual plot object
    factor_plot = Instance(BasePlotContainer)
    # the image data for the score plot (may be a parent image for scatter overlays)
    score_plotdata = Instance(ArrayPlotData)
    score_plot = Instance(BasePlotContainer)
    on_peaks = Bool(False)
    has_peaks = Bool(False)
    number_to_derive = Int(69)
    dimensionality = Int(100000000)
    component_index = Int(0)
    _selected_peak = Int(0)
    selected_method_idx = Int(0)
    methods = List(['PCA', 'ICA'])
    _session_id = String('')

    def __init__(self, treasure_chest=None, data_path='/mda_results',
                 *args, **kw):
        super(ControllerBase, self).__init__(*args, **kw)
        self.factor_plotdata = ArrayPlotData()
        self.score_plotdata = ArrayPlotData()
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.data_path = data_path
            # do we have any peaks?
            try:
                self.chest.getNode('/','cell_peaks')
                self.has_peaks = (self.chest.root.cell_peaks.nrows > 0)
            except:
                pass
    
        def increase_selected_component(self):
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

    def set_target(self,target='images'):
        if target == 'peaks':
            self.on_peaks = True
            # dimensionality is the number of entries in our peak table
            self.dimensionality = int(self.chest.root.cell_peaks.nrows)
        else:
            self.on_peaks = False
            # dimensionality is the number of cell images
            self.dimensionality = int(self.chest.root.cell_description.nrows)
    
    def execute(self):
        method = self.methods[self.selected_method_idx]
        if self.dimensionality < self.number_to_derive:
            self.number_to_derive = self.dimensionality
        if method == 'PCA':
            self.PCA(n_components=self.number_to_derive)
        elif method == 'ICA':
            self.ICA(n_components=self.number_to_derive)
        # close the control panel
        
        # now update the UI
        
        # close the dialog window
        Application.instance().end_session(self._session_id)
        # show the results windows

    def render_active_factor_image(self):
        if self.on_peaks:
            factors = self.chest.root.mda_results[context]['peak_factors']
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
            factors = self.chest.root.mda_results[context]['image_factors']
            # return current factor image (MDA on images themselves)
            self.factor_plotdata.set_data('imagedata', 
                                          factors[self.component_index,:,:])
            # return current factor image (MDA on images themselves)
            self.factor_plot = self.get_simple_image_plot(self.factor_plotdata)
            
    def render_active_score_image(self):
        if self.on_peaks:
            scores = self.chest.root.mda_results[context]['peak_scores']
        else:
            scores = self.chest.root.mda_results[context]['image_scores']
        values = \
            self.chest.root.cell_description.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='x_coordinate',) \
            + \
            self.chest.root.cell_peaks.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='y%i'%self._selected_peak,)
        
        indices = \
            self.chest.root.cell_description.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='y_coordinate',) \
            + \
            self.chest.root.cell_peaks.readWhere(
                'filename == "%s"' % self.get_active_name(),
                field='x%i'%self._selected_peak,)
        color = scores.readWhere(
            'filename' == "%s" % self.get_active_filename(),
            field='%i' % self.component_index
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
        

    def get_input_data(self):
        if self.on_peaks:
            # query the peak table for all fields EXCEPT the filename and file index
            # TODO: should we also exclude peak coordinates (keep only the shift?)
            cols = self.chest.root.cell_peaks.colnames[2:]
            data = self.chest.root.cell_peaks[:][cols]
            data = data.view((np.float64, len(data.dtype.names)))
            active_data_shape = data.shape
        else:
            active_data = self.parent.cell_controller.get_cell_set()
            active_data_shape = active_data.shape
            data = active_data.reshape((active_data.shape[0], -1))
        return data, active_data_shape

    def store_MDA_results(self, factors, scores, eigenvalues=None):
        if self.on_peaks:
            score_table_title='peak_scores'
            # each row of this table is a component
            # we should copy the column titles from the cell peaks table
            # but we remove the file index and filename fields, they're irrelevant.
            factor_dtype = self.chest.root.cell_peaks.dtype.descr[2:]
            table_description = np.zeros((0,), dtype=factor_dtype)
            fs = self.chest.createTable('/'+self.context, 'peak_factors',
                         description=table_description)
            for name_idx in xrange(len(names)):
                pass
        else:
            score_table_title='image_scores'
            fs = self.chest.createCArray('/'+self.context, 'image_factors',
                                     tb.Atom.from_dtype(factors.dtype),
                                     factors.shape,
                                     filters=filters
                                     )
            fs[:] = factors
        # scores go into a table, with one row per input image (or cell), and 
        # one column per component
        names = ['c%i' %x for x in xrange(self.number_to_derive)]
        # make tuples of each column name and 'f8' for the data type
        dtypes = zip(names, ['f8', ] * self.number_to_derive)
        # prepend the index column
        dtypes = [('filename', '|S30'), ('file_idx', 'i4')] + dtypes
        desc = np.recarray((0,), dtype=dtypes)        
        ss = self.chest.createTable('/'+self.context, score_table_title, 
                                    description=desc)
        # arrange data to populate the table
        data = np.zeros((self.number_to_derive), dtype=dtypes)
        data['filename']=self.chest.root.cell_description.col('filename')
        data['file_idx']=self.chest.root.cell_description.col('file_idx')
        for col in xrange(self.number_to_derive):
            data[names[col]] = scores[:, col]
        # get the table and append the data to it
        self.chest.getNode('/'+self.context+'/'+score_table_title).append(data)
        self.chest.getNode('/'+self.context+'/'+score_table_title).flush()
        if eigenvalues is not None:
            ev = self.chest.createCArray('/'+self.context, 'Eigenvalues',
                                     tb.Atom.from_dtype(eigenvalues.dtype),
                                     eigenvalues.shape,
                                     filters=filters
                                     )
            ev[:] = eigenvalues
        self.chest.flush()

    ######
    #  Analysis methods each create their own member under the group of MDA
    #  results in the chest.
    ######
    def PCA(self, n_components=None):
        self._create_new_context("PCA")
        data, active_data_shape = self.get_input_data()
        factors, scores , eigenvalues = mda.PCA(data, n_components=n_components)
        factors, scores = self._reshape_MDA_results(active_data_shape, factors, scores)
        self.store_MDA_results(factors, scores, eigenvalues)
        # stash the results under the group of MDA results
        #   attribs:
        #   - analysis type
        #   - number of components
        #   - whitening applied
        # store the mean of each column - we use this for reconstruction later

    def ICA(self, n_components, whiten=False, max_iter=10, differentiate=False):
        from scipy import integrate
        self._create_new_context("ICA")
        # reshape the data:
        #   The goal is always to have the variables (pixels in an image,
        #     energy channels in a spectrum) always as columns in a 2D array.
        #     The rows are made up of observations.  For example, in
        #     images, the rows are individual cells.  In SIs, the rows
        #     are pixels where spectra were gathered.
        # for images, the cell idx is dim 0
        data, active_data_shape = self.get_input_data()
        """
        Pre-processes the data to be ready for ICA.  Namely:
          differentiates the data (integrated ICA)
        """
        if differentiate:
            diffdata = data.T.copy()
            deriv_kernel = np.array([-1, 0, 0, 0, 0, 0, 1])
            for i in xrange(data.shape[1]):
                diffdata[:, i] = np.convolve(data[:, i], deriv_kernel)[3:-3]
            factors, scores = mda.ICA(diffdata, n_components=n_components)
            # integration undoes the differentiation done in the ICA data pre
            factors = np.array([integrate.cumtrapz(factors[:, i])
                                for i in xrange(factors.shape[1])]).T
            # TODO: pad by one row for the row than has been discarded by differentiation/integtration            
        else:
            factors, scores = mda.ICA(data, n_components=n_components)
        
        factors, scores = self._reshape_MDA_results(active_data_shape, 
                                                    factors, scores)
        self.store_MDA_results(factors, scores, eigenvalues)

    def _reshape_MDA_results(self, datashape, factors, scores):
        # we need to reshape the factors and scores to make sense.
        # for images, the factors are themselves images, while the scores are
        # line plots with one column per component.
        if self.get_active_data_type() is "image":
            factors = factors.reshape((-1, datashape[-2], datashape[-1]))
            factors.squeeze()
            scores.reshape((datashape[0], -1))
        # for SIs, the factors are spectra, while the scores are images.
        elif ((self.get_active_data_type() is "spectrum") or
                (self.get_active_data_type() is "peaks")):
            factors = factors.reshape((datashape[0], -1))
            scores = scores.reshape((-1, datashape[-2], datashape[-1]))
            scores.squeeze()
        return factors, scores

    def _create_new_context(self, MDA_type):
        import time
        # first add an entry to our table of analyses performed
        datestr = MDA_type + time.strftime("_%Y-%m-%d %H:%M", time.localtime())
        data_record = self.chest.root.mda_description.row
        data_record['date'] = datestr
        data_record['mda_type'] = MDA_type
        #data_record['input_data'] = self.data_controller.summarize_data()
        #data_record['treatments'] = self.data_controller.summarize
        data_record.append()
        # If this MDA type hasn't been done yet, add a member of the MDA group
        #   for this type.
        # Set this instance's data as members of a group for the time right now
        # this is where the factors and scores result arrays will be stored.
        self.chest.flush()
        # context is a pytables group.  It has attributes for informational
        #   data, as well as being the container for any outputs.
        self.context = "mda_results/%s" % (datestr)
        self.chest.createGroup('/mda_results', datestr)
        #self.chest.getNode('/mda_results/'+datestr).setAttr('method', MDA_type)