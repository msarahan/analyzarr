from chaco.api import ArrayPlotData, BasePlotContainer, Plot
from traits.api import Instance, Bool, Int, List, String, on_trait_change, HasTraits
import tables as tb
# how much to compress the data
from analyzarr.lib.io.data_structure import filters

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

class MDAExecutionController(HasTraits):
    on_peaks = Bool(False)
    has_peaks = Bool(False)
    number_to_derive = Int(69)
    dimensionality = Int(100000000)
    component_index = Int(0)
    _selected_peak = Int(0)
    selected_method_idx = Int(0)
    methods = List(['PCA', 'ICA'])
    _session_id = String('')
    context = String('')

    def __init__(self, treasure_chest=None, data_path='/rawdata',
                 *args, **kw):
        super(MDAExecutionController, self).__init__(*args, **kw)
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.data_path = data_path
            # do we have any peaks?
            try:
                self.chest.getNode('/','cell_peaks')
                self.has_peaks = bool((self.chest.root.cell_peaks.nrows > 0))
            except:
                pass

    # TODO: this is for defining MDA's kind of data it's handling.  It might
    #   eventually be used for spectroscopy data.
    def get_active_data_type(self):
        return "image"

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
        self.chest.setNodeAttr('/mda_results/'+self.context, 
                               'dimensionality', self.number_to_derive)
        # close the dialog window
        Application.instance().end_session(self._session_id)
        # show the results windows
        self.parent.update_mda_data()

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
            chars = ['dx', 'dy', 'h', 'o', 'e']
            if len(indices) is 0:
                indices = range(self.chest.getNodeAttr('/cell_peaks','number_of_peaks'))
            # the columns we get are the combination of the chars with the
            #   indices we want.
            cols = [['%s%i' % (c, i) for c in chars] for i in indices]
        # make the cols a simple list, rather than a list of lists
        cols = [item for sublist in cols for item in sublist]
        # get the data from the table
        peak_data = self.chest.root.cell_peaks[:]
        # return an ndarray with only the selected columns
        return np.array(peak_data[cols]).view(float).reshape(len(cols), -1)

    def get_input_data(self):
        if self.on_peaks:
            # query the peak table for all fields EXCEPT the filename and file index
            # TODO: should we also exclude peak coordinates (keep only the shift?)
            data = self.get_peak_data().T
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
            fs = self.chest.createTable('/mda_results/'+self.context, 'peak_factors',
                         description=table_description)
            self.chest.setNodeAttr('/mda_results/'+self.context, 'on_peaks', True)
            data = np.zeros((self.number_to_derive), dtype=factor_dtype)
            row = fs.row
            # record the factors
            indices = range(self.chest.getNodeAttr('/cell_peaks','number_of_peaks'))
            chars = ['dx', 'dy', 'h', 'o', 'e']
            # the columns we get are the combination of the chars with the
            #   indices we want.
            cols = [['%s%i' % (c, i) for c in chars] for i in indices]            
            # flatten that from a list of lists to a simple list
            cols = [item for sublist in cols for item in sublist]            
            for col in xrange(len(cols)):
                data[cols[col]] = factors[:, col]
            # record the x and y coordinates
            coordinate_data_indices = [['%s%i' % (c, i) for c in ['x', 'y']] 
                                        for i in indices]
            # flatten that from a list of lists to a simple list
            coordinate_data_indices = [item for sublist in coordinate_data_indices for item in sublist]
            # get the row for the average cell from the cell_peaks table.
            #   we use this for recording the X and Y coordinates of peaks,
            #   which we do not feed into MDA itself.
            peak_record = self.chest.root.cell_peaks.readWhere(
                'filename == "average"')[0]        
            for idx in coordinate_data_indices:
                data[idx] = peak_record[idx]
            fs.append(data)
            fs.flush()
        else:
            score_table_title='image_scores'
            fs = self.chest.createCArray('/mda_results/'+self.context, 'image_factors',
                                     tb.Atom.from_dtype(factors.dtype),
                                     factors.shape,
                                     filters=filters
                                     )
            fs[:] = factors
            self.chest.setNodeAttr('/mda_results/'+self.context, 'on_peaks', False)
        # scores go into a table, with one row per input image (or cell), and 
        # one column per component
        names = ['c%i' %x for x in xrange(self.number_to_derive)]
        # make tuples of each column name and 'f8' for the data type
        dtypes = zip(names, ['f8', ] * self.number_to_derive)
        # prepend the index column
        dtypes = [('filename', '|S30'), ('file_idx', 'i4')] + dtypes
        desc = np.recarray((0,), dtype=dtypes)        
        ss = self.chest.createTable('/mda_results/'+self.context, score_table_title, 
                                    description=desc)
        # arrange data to populate the table
        data = np.zeros((self.chest.root.cell_peaks.nrows), dtype=dtypes)
        data['filename']=self.chest.root.cell_peaks.col('filename')
        data['file_idx']=self.chest.root.cell_peaks.col('file_idx')
        for col in xrange(self.number_to_derive):
            data[names[col]] = scores[:, col]
        # get the table and append the data to it
        ss.append(data)
        ss.flush()
        if eigenvalues is not None:
            ev = self.chest.createCArray('/mda_results/'+self.context, 'Eigenvalues',
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
        if self.get_active_data_type() is "image" and not self.on_peaks:
            factors = factors.reshape((-1, datashape[-2], datashape[-1]))
        # for SIs, the factors are spectra, while the scores are images.
        elif ((self.get_active_data_type() is "spectrum") or
                (self.get_active_data_type() is "peaks")):
            scores = scores.reshape((-1, datashape[-2], datashape[-1]))
        return factors.squeeze(), scores.squeeze()

    def _create_new_context(self, MDA_type):
        import time
        # first add an entry to our table of analyses performed
        datestr = MDA_type + time.strftime("_%Y-%m-%d %H:%M", time.localtime())
        data_record = self.chest.root.mda_description.row
        data_record['context'] = datestr
        data_record['mda_type'] = MDA_type
        #data_record['input_data'] = self.data_controller.summarize_data()
        #data_record['treatments'] = self.data_controller.summarize
        data_record.append()
        self.chest.root.mda_description.flush()
        # context is a pytables group.  It has attributes for informational
        #   data, as well as being the container for any outputs.
        self.chest.createGroup('/mda_results', datestr)
        self.context = datestr
        self.chest.flush()
        #self.chest.getNode('/mda_results/'+datestr).setAttr('method', MDA_type)