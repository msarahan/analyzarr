from BaseImage import BaseImageController

from traits.api import Bool, Int, on_trait_change
import numpy as np
import tables as tb

import analyzarr.lib.cv.peak_char as pc
from analyzarr.lib.io.data_structure import filters

from pyface.api import ProgressDialog
from enaml.application import Application

class CellController(BaseImageController):
    _can_characterize = Bool(False)
    _show_peak_ids = Bool(False)
    _can_show_peak_ids = Bool(False)
    _progress_value = Int(0)
    _progress_max = Int(1)
    numpeaks = Int(0)
    peak_width = Int(10)
    _do_char=Bool(False)
    omitted=Bool(False)
    
    def __init__(self, parent, treasure_chest=None, data_path='/cells', *args, **kw):
        super(CellController, self).__init__(parent, treasure_chest, data_path,
                *args, **kw)
        if self.chest is not None:
            try:
                self.chest.get_node('/','cell_description')
            except:
                return            
            self.numfiles = int(self.chest.root.cell_description.nrows)
            if self.numfiles > 0:
                self.init_plot()
                self._toggle_UI(True)
                self._can_change_idx = True
                self.parent.show_cell_view=True
                try:
                    self.chest.get_node('/', 'cell_peaks')
                    self.numpeaks = int(self.chest.get_node_attr('/cell_peaks','number_of_peaks'))
                    self._can_show_peak_ids = True
                except:
                    # we haven't got any peaks to identify
                    return

    def _toggle_UI(self, enable):
        self._can_save = enable
        self._can_characterize = enable

    @on_trait_change("selected_index, _show_peak_ids")
    def update_data_labels(self):
        try:
            self.chest.get_node('/','cell_peaks')
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
        peak_record = self.chest.root.cell_peaks.read_where(
            '(filename == "%s") & (file_idx == %i)'%(self.get_cell_parent(), file_idx)
            )[0]        
        for peak in range(self.numpeaks):
            x = peak_record['x%i'%peak]
            y = peak_record['y%i'%peak]
            label = '%i' %peak
            labels[label]=(y,x)
        self.plot_labels(labels)
        self.show_labels(self._show_peak_ids)

    @on_trait_change("selected_index")
    def update_omitted_status(self):
        omitted = self.chest.root.cell_description.read(
                            start=self.selected_index, field="omit")[0]
        self.omitted=bool(omitted)
        
    def get_average_cell(self):
        return self._get_average_image()
    
    def map_peaks_to_cells(self):
        """
        This function takes the global collection of peaks from each parent
        image and figures out where they fit in the context of a local cell.
        """
        
        # we have to first identify the locations on the average image of the
        # peaks that we should look at. 
        avg=self.get_average_cell()
        
        #Now for each cell we've cropped, and for each peak ID, locate the
        #best matching global peak. The best match is defined as the
        #coordinate closest to the top-left corner of the cell, plus the
        #cell-local offset (from the average image) to get to the peak.
        
    def get_active_image(self):
        # Find this cell in the cell description table.  We use this to look
        # up the parent image and subsequently the local cell index (the
        # index among only the cells from that image)
        try:
            self.chest.get_node('/','cell_description')
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
        if len(self.nodes[selected_image].shape)==2:
            return self.nodes[selected_image][:]
        else:
            return self.nodes[selected_image][cell_record['file_idx'], :, :]

    def get_cell_parent(self):
        # Find this cell in the cell description table.  We use this to look
        # up the parent image and subsequently the local cell index (the
        # index among only the cells from that image)
        try:
            self.chest.get_node('/','cell_description')
        except:
            return        
        cell_record = self.chest.root.cell_description.read(
                            start=self.selected_index,
                            stop=self.selected_index + 1)[0]
        # find the parent that this cell comes from
        return cell_record['filename']

    def get_omitted_indices(self, node_name):
        return self.chest.root.cell_description.read_where(
            '(omit==True) & (filename == "%s")' % node_name, 
            field='file_idx').tolist()
        
    # TODO: is there any compelling reason that we need the whole stack at once?
    def get_cell_set(self, node_name = None):
        """ 
        If node_name is specified (it would be the name of a parent image),
            then this method will return cell images for only that node.
        The default behavior is to return data from all nodes.
        """
        node_names = [node.name for node in self.nodes]
        if node_name is not None:
            data = self.nodes[node_names.index(node_name)][:]
            data = data.reshape((-1, data.shape[-2], 
                                 data.shape[-1]))
            # cut out any exclusions
            #exclusions = self.get_omitted_indices(node_name)
            #data = np.delete(data, exclusions, 0)
        else:
            data = np.zeros((self.chest.root.cell_description.nrows,
                             self.chest.root.cells.template.shape[1],
                             self.chest.root.cells.template.shape[0]
                             ),
                            dtype = self.chest.root.cells.template.dtype,
                            )
            nodes = self.chest.list_nodes('/cells')
            start_idx = 0
            end_idx=0
            tmp_size = self.chest.root.cells.template.shape[0]
            empty_slices=0
            for node in nodes:
                node_data = node[:]
                #exclusions = self.get_omitted_indices(node.name)
                #data = np.delete(node_data, exclusions, 0)                
                #empty_slices+=len(exclusions)
                
                node_data = node_data.reshape((-1, node_data.shape[-2], 
                                               node_data.shape[-1]))
                # cut out any exclusions
                #exclusions = self.get_omitted_indices(node.name)
                #node_data = np.delete(node_data, exclusions, 0)
                if node.name not in ['template', 'average']:
                    end_idx = start_idx + node_data.shape[0]
                    data[start_idx:end_idx,:,:] = node_data
                    start_idx = end_idx
            # delete the empty space used for the excluded cells
        return data
        
    def _get_average_image(self):
        return np.average(self.get_cell_set(), axis=0)
        
    def get_active_name(self):
        parent = self.get_cell_parent()
        return '(from %s)' % parent

    def get_num_files(self):
        return self.chest.root.cell_description.nrows
    
    def toggle_char(self):
        self._do_char = not self._do_char
        
    @on_trait_change('_do_char')
    def execute_characterize(self):
        self.characterize()
    
    def omit_selected_index(self):
        cell_record=self.chest.root.cell_description[self.selected_index]
        # this is not the nicest - would be better to do a table join, 
        #    but this is more a feature of relational databases, not pytables.
        self.chest.root.cell_description.cols.omit[self.selected_index]=not cell_record["omit"]
        # locate the cell in the cell peaks table by its image id and cell id 
        #         (here is where the join would be nice...)
        
        peak_selected_idx = self.chest.root.cell_peaks.get_where_list(
            '(filename == "%s") & (file_idx == %i)'%(cell_record["filename"], 
                                               cell_record["file_idx"]))[0]
        
        self.chest.root.cell_peaks.cols.omit[peak_selected_idx]=not cell_record["omit"]
        #cell_record["omit"] = np.bool(not cell_record["omit"])
        #self.chest.root.cell_description.modifyRows(self.selected_index,
        #    rows=[self.selected_index,cell_record])
        self.chest.root.cell_description.flush()
        self.omitted = not self.omitted
        self.log_action(action="omit cell", 
                        idx=cell_record["file_idx"], 
                        image=cell_record["filename"],
                        state=cell_record["omit"])
    
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
            sx - the skew in the x-direction.  Skew is a measure of asymmetry.
            sy - the skew in the y-direction.  Skew is a measure of asymmetry.
            
        indices - peak indices (integers) to select from.  Use this if you want to compare
            only a few peaks in the cell structure to compare.
            None selects all peaks from all non-omitted cells.
        """
        if len(chars) > 0:
            if len(indices) is 0:
                # we want data for all the peaks in each cell
                indices = range(self.chest.get_node_attr('/cell_peaks','number_of_peaks'))
            # the columns we get are the combination of the chars with the
            #   indices we want.
            cols = [['%s%i' % (c, i) for i in indices] for c in chars]
        else:
            chars = ['x', 'y', 'dx', 'dy', 'h', 'o', 'e', 'sx', 'sy']
            if len(indices) is 0:
                indices = range(self.chest.root.cell_peaks.number_of_peaks)
            # the columns we get are the combination of the chars with the
            #   indices we want.
            cols = [['%s%i' % (c, i) for c in chars] for i in indices]
        # make the cols a simple list, rather than a list of lists
        cols = [item for sublist in cols for item in sublist]
        # get the data from the table, omitting any excluded data
        indices = self.chest.get_node('/cell_peaks').get_where_list(
            '(omit==False)')
        peak_data = self.chest.root.cell_peaks[indices]
        # return an ndarray with only the selected columns
        return np.array(peak_data[cols]).view(float).reshape(len(cols), -1)

    def merge_processed_peak_data(self, data):
        """
        We passed data to PCA/ICA that did not include omitted cells.  When 
        we add data back into the results table, we need to indicate in that
        table that we don't have data on those cells.
        """
        indices = self.chest.get_node('/cell_peaks').get_where_list(
                    '(omit==False)')        
        if len(indices)==0:
            return data
        desc = np.recarray((0,), dtype=dtypes)
        data=np.insert(data,1,desc,0)
        return data
        
        