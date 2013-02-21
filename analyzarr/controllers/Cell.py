from BaseImage import BaseImageController

from traits.api import Bool, Int, on_trait_change
import numpy as np

from analyzarr import peak_char as pc

#from chaco.default_colormaps import gray
#from chaco.api import ArrayPlotData, BasePlotContainer, Plot

class CellController(BaseImageController):
    _can_characterize = Bool(False)
    numpeaks = Int(0)
    
    def __init__(self, parent, treasure_chest=None, data_path='/cells', *args, **kw):
        super(CellController, self).__init__(parent, treasure_chest, data_path,
                *args, **kw)
        if self.chest is not None:
            try:
                self.chest.getNode('/','cell_description')
            except:
                return            
            self.numfiles = int(self.chest.root.cell_description.nrows)
            if self.numfiles > 0:
                self.init_plot()
                print "initialized plot for data in %s" % data_path
                self._toggle_UI(True)
                self._can_change_idx = True
                self.parent.show_cell_view=True

    def _toggle_UI(self, enable):
        self._can_save = enable
        self._can_characterize = enable

    @on_trait_change("selected_index")
    def update_data_labels(self):
        try:
            self.chest.getNode('/','cell_peaks')
        except:
            return
        # labels is a dict consisting of data points as tuples
        labels = {}
        # this is the record in the cell_description table
        cell_record = self.chest.root.cell_description.read(
                            start=self.selected_index,
                            stop=self.selected_index + 1)[0]
        file_idx = cell_record['file_idx']
        # this is the corresponding record in the cell_peaks table:
        peak_record = self.chest.root.cell_peaks.readWhere(
            'filename == "%s" and file_idx == %i'%(self.get_cell_parent(), file_idx)
            )[0]        
        for peak in range(self.numpeaks):
            x = peak_record['x%i'%peak]
            y = peak_record['y%i'%peak]
            label = '%i' %peak
            labels[label]=(x,y)
        self.plot_labels(labels)
        self.show_labels()
        
    def get_active_image(self):
        # Find this cell in the cell description table.  We use this to look
        # up the parent image and subsequently the local cell index (the
        # index among only the cells from that image)
        try:
            self.chest.getNode('/','cell_description')
        except:
            return       
        cell_record = self.chest.root.cell_description.read(
                            start=self.selected_index,
                            stop=self.selected_index + 1)[0]        
        parent = self.get_cell_parent()
        # select that parent as the selected image (int because it is an index)
        selected_image = int([x['idx'] for x in
                                       self.chest.root.image_description.where(
                                       'filename == "%s"' % parent)][0])

        # return the cell data - the index is the index of this cell
        #    among only its indexed cells - not the universal index!
        return self.nodes[selected_image][cell_record['file_idx'], :, :]

    def get_cell_parent(self):
        # Find this cell in the cell description table.  We use this to look
        # up the parent image and subsequently the local cell index (the
        # index among only the cells from that image)
        try:
            self.chest.getNode('/','cell_description')
        except:
            return        
        cell_record = self.chest.root.cell_description.read(
                            start=self.selected_index,
                            stop=self.selected_index + 1)[0]
        # find the parent that this cell comes from
        return cell_record['filename']
        
    # TODO: is there any compelling reason that we need the whole stack at once?
    def get_cell_set(self):
        data = np.zeros((self.chest.root.cell_description.nrows,
                         self.chest.root.cells.template.shape[1],
                         self.chest.root.cells.template.shape[0]
                         ),
                        dtype = self.chest.root.cells.template.dtype,
                        )
        nodes = self.chest.listNodes('/cells')
        start_idx = 0
        end_idx=0
        tmp_size = self.chest.root.cells.template.shape[0]
        for node in nodes:
            if node.name is not 'template':
                end_idx = start_idx + node.shape[0]
                data[start_idx:end_idx,:,:] = node[:]
                start_idx = end_idx
        return data
        
    def _get_average_image(self):
        return np.average(self.get_cell_set(), axis=0)
        
    def get_active_name(self):
        parent = self.get_cell_parent()
        return '(from %s)' % parent

    def get_num_files(self):
        return self.chest.root.cell_description.nrows
        
    # TODO: automatically determine the peak width from an average image
    def characterize(self, peak_width, subpixel=True,
                     target_locations=None, target_neighborhood=20, 
                     medfilt_radius=5):
        # disable the UI while we're running
        self._toggle_UI(False)
        try:
            # wipe out old results
            self.chest.removeNode('/cell_peaks')        
        except:
            # any errors will be because the table doesn't exist. That's OK.
            pass        
        # locate peaks on the average image to use as target locations.
        #   also determines the number of peaks, which in turn determines
        #   the table columns.
        target_locations = pc.two_dim_findpeaks(self._get_average_image(),
                                                subpixel=True)[:,:2]
        self.numpeaks = int(target_locations.shape[0])
        # generate a list of column names
        names = [('x%i, y%i, dx%i, dy%i, h%i, o%i, e%i' % ((x,)*7)).split(', ') 
                 for x in xrange(self.numpeaks)]
        # flatten that from a list of lists to a simple list
        names = [item for sublist in names for item in sublist]
        # make tuples of each column name and 'f8' for the data type
        dtypes = zip(names, ['f8', ] * self.numpeaks*7)
        # prepend the index column
        dtypes = [('filename', '|S30'), ('file_idx', 'i4')] + dtypes
        desc = np.recarray((0,), dtype=dtypes)
        self.chest.createTable(self.chest.root,
                               'cell_peaks', description=desc)        
        # for each file in the cell_data group, run analysis.
        nodes = self.chest.listNodes('/cells')
        node_names = [node.name for node in nodes if node.name not in ['template', 'average']]
        for node in node_names:
            numcells = nodes[node_names.index(node)].shape[0]
            data = np.zeros((numcells),dtype=dtypes)
            data['filename'] = node
            data['file_idx'] = np.arange(numcells)
            attribs = pc.peak_attribs_stack(nodes[node_names.index(node)][:],
                            peak_width=peak_width, subpixel=subpixel,
                            target_locations=target_locations,
                            target_neighborhood=target_neighborhood,
                            medfilt_radius=medfilt_radius)
            attribs = attribs.T
            # for each column name, copy in the data
            for name_idx in xrange(len(names)):
                data[names[name_idx]] = attribs[:, name_idx]
            # add the data to the table
            self.chest.root.cell_peaks.append(data)
        # add an attribute for the total number of peaks recorded
        self.chest.root.cell_peaks.setAttr('number_of_peaks', self.numpeaks)
        self.chest.root.cell_peaks.flush()
        self.update_data_labels()
        self.parent.image_controller.update_peak_map_choices()
        
        self._toggle_UI(True)

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
