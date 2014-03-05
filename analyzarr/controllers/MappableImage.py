from BaseImage import BaseImageController
from traits.api import Bool, List, Int, Float, Range, String, on_trait_change
import numpy as np
import tables as t

from analyzarr.ui.progress import PyFaceProgress

class MappableImageController(BaseImageController):
    _can_map_peaks = Bool(False)
    _can_map_vectors = Bool(False)
    _is_mapping_peaks = Bool(False)
    _characteristics = List(["None","Height", "Orientation", "Eccentricity", "Expression"])
    _characteristic = Int(0)
    _selected_peak = Int()
    _peak_ids = List([])
    _peak_expression = String("")
    _vectors = List(['None','Shifts', 'Skew'])
    _vector = Int(0)
    vector_scale = Float(1.0)

    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', *args, **kw):
        super(MappableImageController, self).__init__(parent, treasure_chest, data_path,
                                              *args, **kw)
        
        if self.chest is not None:
            self.numfiles = len(self.nodes)
            if self.numfiles >0:
                self.init_plot()
                self._can_crop_cells = True
                self.parent.show_image_view=True
                self.update_peak_map_choices()
    
    def add_data(self, data, name):
        super(MappableImageController, self).add_data(data, name)
        row = self.chest.root.image_description.row
        row["idx"]=self.chest.root.image_description.nrows
        row["filename"]="average"
        row.append()
        self.chest.root.image_description.flush()
    
    def get_characteristic_name(self):
        return self._characteristics[self._characteristic]

    def get_vector_name(self):
        return self._vectors[self._vector]
    
    @on_trait_change('selected_index')
    def update_peak_map_choices(self):
        # do we have any entries in the peak characteristic table for this image?
        if (self.get_numpeaks() > 0):
            # TODO: figure out if we've mapped peak IDs to the global peak registry.
            self._peak_ids = self.get_peak_id_list()
            self._can_map_peaks=True
            if len(self.get_peak_id_list())>1:
                self._can_map_vectors=True
        else:
            # clear the image and disable the comboboxes
            pass
    
    def get_peak_id_list(self):
        try:
            numpeaks = self.chest.get_node_attr('/cell_peaks','number_of_peaks')
            peak_ids = ['all']+[str(idx) for idx in range(numpeaks)]
            return peak_ids
        except (ValueError, t.NoSuchNodeError):
            return ['all']
    
    def get_numpeaks(self):
        return self.chest.root.image_peaks.nrows
    
    def characterize_peaks(self, peak_width=None, progress_object=PyFaceProgress()):
        from analyzarr.lib.io.data_structure import ImagePeakTable
        import analyzarr.lib.cv.peak_char as pc
        # clear out the existing peak data table
        # TODO: there's probably a better way to intelligently only recalculate
        #    peaks as necessary for new images, or if peak_width changes.
        try:
            # wipe out old results
            self.chest.remove_node('/image_peaks')
        except:
            # any errors will be because the table doesn't exist. That's OK.
            pass
        self.chest.create_table('/', 'image_peaks', ImagePeakTable)
        table = self.chest.root.image_peaks
        nodes = self.chest.list_nodes('/rawdata')
        progress_object.initialize("Characterizing peaks on images", int(len(
                                                                    nodes)))
        for node in nodes:
            # uses default median filter radius of 5 pixels
            if node.name=="average":
                peak_data = pc.peak_attribs_image(node[:],xc_filter=False,
                                                  kill_edges=False)
            else:
                peak_data = pc.peak_attribs_image(node[:],peak_width=peak_width)
            # prepend the filename and index columns
            dtypes = ['i8','|S250']+['f8']*9
            dtypes = zip(table.colnames, dtypes)
            rows = peak_data.shape[0]
            cols = peak_data.shape[1]
            # prepend the filename and index columns
            data = np.zeros(rows,dtype=dtypes)
            data['filename'] = node.name
            data['file_idx'] = np.arange(rows)
            for name_idx in xrange(cols):
                data[table.colnames[name_idx+2]] = peak_data[:, name_idx]
            # populate the peak_data table
            self.chest.root.image_peaks.append(data)
            self.chest.root.image_peaks.flush()
            self.chest.flush()
            progress_object.increment()
            
        # update the menu since we now (probably) have peaks to map.
        self.update_peak_map_choices()
            
    
    def get_characteristic_plot_title(self):
        name = ""
        if self.get_characteristic_name() != "None":
            name = ", "+self.get_characteristic_name()
            if self.get_vector_name() !="None":
                name += " and %s"%self.get_vector_name()
            name += " from peak %s" %self._peak_ids[self._selected_peak]
        elif self.get_vector_name() != "None":
            name = ", "+ self.get_vector_name()
            name += " from peak %s" %self._peak_ids[self._selected_peak]
        return self.get_active_name() + name
    
    @on_trait_change('_peak_ids, _characteristic, _selected_peak, _vector, \
                        selected_index, vector_scale, _peak_expression')
    def update_image(self):
        has_cell_peaks=False
        if self.chest is None or self.numfiles<1:
            return
        super(MappableImageController, self).update_image()
        if self.get_numpeaks()<1:
            return
        self.update_peak_map_choices()
        try:
            # if the cell_peaks table exists, then we have mapped the global 
            #    peak descriptors to local cells and can use peak IDs.
            self.chest.get_node('/','cell_peaks')
            has_cell_peaks=True
        except (ValueError, t.NoSuchNodeError):
            pass
        if self.get_peak_id_list()[self._selected_peak] == "all":
            # peaks in base table are in absolute coordinates.
            values = self.get_expression_data("x", table_loc="/image_peaks")
            indices = self.get_expression_data("y", table_loc="/image_peaks")            
        else:
            if has_cell_peaks is True:
                values = self.get_expression_data("x_coordinate", 
                                                  table_loc="/cell_description") + \
                    self.get_expression_data("x%s"%self._peak_ids[self._selected_peak],
                                             table_loc="/cell_peaks")
                indices = self.get_expression_data("y_coordinate", 
                                                   table_loc="/cell_description") + \
                    self.get_expression_data("y%s"%self._peak_ids[self._selected_peak],
                                             table_loc="/cell_peaks")
            else:
                raise StandardError("Error: you somehow managed to specify a selected peak, \
                when there are no peak ids available.  If you're a beta tester,\
                you've earned a beer.")
                return
                
        
        self.plotdata.set_data('value', values)
        self.plotdata.set_data('index', indices)
        
        if self.get_vector_name() != "None":
            field = ''
            if self.get_vector_name() == 'Shifts':
                field = 'd'
            elif self.get_vector_name() == 'Skew':
                field = 's'
            if field != '':
                if self.get_peak_id_list()[self._selected_peak] == "all":
                    if field=="s":
                        x_comp = self.get_expression_data("%sx"%(field),
                                                          table_loc="/image_peaks")
                        y_comp = self.get_expression_data("%sy"%(field),
                                                          table_loc="/image_peaks")
                    else:
                        x_comp=None
                        # clear vector data
                        if 'vectors' in self.plotdata.arrays:
                            try:
                                self.plotdata.del_data('vectors')
                            except:
                                pass                        
                else:
                    x_comp = self.get_expression_data("%sx%s"%(field,self._peak_ids[self._selected_peak]),
                                                      table_loc="/cell_peaks")
                    y_comp = self.get_expression_data("%sy%s"%(field,self._peak_ids[self._selected_peak]),
                                                      table_loc="/cell_peaks")
                    if field=='d':
                        y_comp*=-1

                if x_comp is not None:
                    vectors = np.vstack((x_comp, y_comp)).T
                    vectors *= self.vector_scale
                    self.plotdata.set_data('vectors',vectors)
            else:
                print "%s field not recognized for vector plots."%field
                if 'vectors' in self.plotdata.arrays:
                    self.plotdata.del_data('vectors')
                
        else:
            # clear vector data
            if 'vectors' in self.plotdata.arrays:
                try:
                    self.plotdata.del_data('vectors')
                except:
                    pass
                
        if self.get_expression_name() not in ["None",'']:
            if self.get_peak_id_list()[self._selected_peak] == "all":
                data = self.get_expression_data(self.get_expression_name(),'/image_peaks')
            else:
                data = self.get_expression_data(self.get_expression_name(),'/cell_peaks')
            self.plotdata.set_data('color', data)
        else:
            if 'color' in self.plotdata.arrays:
                try:
                    self.plot.datasources.clear()
                    self.plotdata.del_data('color')
                    self.plot.request_redraw()
                except:
                    pass

        #TODO: might want to implement the selection tool here.
        self.plot = self.get_scatter_quiver_plot(self.plotdata,
                                                      tools=["zoom","pan"])
        self.set_plot_title(self.get_characteristic_plot_title())
        self.log_action(action="plot peak map", 
                        vector_plot=self.get_vector_name(),
                        expression=self.get_expression_name())
        self._is_mapping_peaks=True

    def get_expression_name(self):
        if self.get_characteristic_name() =="None":
            return "None"
        if self.get_characteristic_name() == "Expression":
            expression = self._peak_expression
        elif self.get_characteristic_name != "None":
            expression = self._characteristics[self._characteristic][0].lower()
            if self.get_peak_id_list()[self._selected_peak] != "all":
                # -1 because "all" is first position
                expression = expression + str(self._selected_peak-1)
        return expression

    
    
    