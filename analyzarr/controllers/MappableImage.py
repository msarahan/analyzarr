from BaseImage import BaseImageController
from traits.api import Bool, List, Int, Float, Range, String, on_trait_change
import numpy as np
import tables as t

class MappableImageController(BaseImageController):
    _can_map_peaks = Bool(False)
    _is_mapping_peaks = Bool(False)
    _characteristics = List(["None","Height", "Orientation", "Eccentricity", "Expression"])
    _characteristic = Int(0)
    _selected_peak = Int(0)
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
                print "initialized plot for data in %s" % data_path
                self._can_crop_cells = True
                self.parent.show_image_view=True
                self.update_peak_map_choices()
    
    def get_characteristic_name(self):
        return self._characteristics[self._characteristic]

    def get_vector_name(self):
        return self._vectors[self._vector]
    
    @on_trait_change('selected_index')
    def update_peak_map_choices(self):
        # do we have any entries in the peak characteristic table for this image?
        # knowing about the arrays in the cell data group is enough - if
        #  there aren't any cells from an image, there won't be any entries.
        try:
            cell_desc = self.chest.root.cell_description
        except:
            return
        if (len(self.chest.root.cell_description.get_where_list(
               'filename == "%s"' % self.get_active_name())) > 0):
            try:
                # if this table doesn't exist, we raise an exception
                peak_table = self.chest.root.cell_peaks
            except:
                return
            try:
                #TODO: need to figure out pytables attributes
                numpeaks = self.get_numpeaks()
                self._peak_ids = [str(idx) for idx in range(numpeaks)]
            except:
                return
            self._can_map_peaks=True
            self.update_image()
        else:
            # clear the image and disable the comboboxes
            pass
    
    def get_numpeaks(self):
        return self.chest.getNodeAttr('/cell_peaks','number_of_peaks')
    
    def characterize_peaks(self, peak_width):
        from lib.io.data_structure import ImagePeakTable
        import lib.cv.peak_char as pc
        # clear out the existing peak data table
        # TODO: there's probably a better way to intelligently only recalculate
        #    peaks as necessary for new images, or if peak_width changes.
        try:
            # wipe out old results
            self.chest.removeNode('/image_peaks')
        except:
            # any errors will be because the table doesn't exist. That's OK.
            pass
        self.chest.createTable('/', 'image_peaks', ImagePeakTable)
        table = self.chest.root.image_peaks
        for node in self.chest.listNodes('/rawdata'):
            # TODO: progress bar here for image progress
            # TODO: progress bar for characterizing each peak (within this function call...)
            # uses default median filter radius of 5 pixels
            peak_data = pc.peak_attribs_image(node[:],peak_width=peak_width)
            # prepend the filename and index columns
            dtypes = ['i8','|S250']+['f8']*7
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
            
    
    def get_characteristic_plot_title(self):
        name = ""
        if self.get_characteristic_name() != "None":
            name = ", "+self.get_characteristic_name()
            if self.get_vector_name() !="None":
                name += " and %s"%self.get_vector_name()
            name += " from peak %i" %self._selected_peak
        elif self.get_vector_name() != "None":
            name = ", "+ self.get_vector_name()
            name += " from peak %i" %self._selected_peak
        return self.get_active_name() + name
    
    @on_trait_change('_peak_ids, _characteristic, _selected_peak, _vector, \
                        selected_index, vector_scale, _peak_expression')
    def update_image(self):
        if self.chest is None or self.numfiles<1:
            return
        super(MappableImageController, self).update_image()
        try:
            self.chest.getNode('/','cell_peaks')
        except:
            return
        
        values = self.get_expression_data("x_coordinate", 
                                          table_loc="/cell_description") + \
            self.get_expression_data("y%i"%self._selected_peak)
        indices = self.get_expression_data("y_coordinate", 
                                           table_loc="/cell_description") + \
            self.get_expression_data("x%i"%self._selected_peak)
        
        self.plotdata.set_data('value', values)
        self.plotdata.set_data('index', indices)
        
        if self.get_vector_name() != "None":
            field = ''
            if self.get_vector_name() == 'Shifts':
                field = 'd'
            elif self.get_vector_name() == 'Skew':
                field = 's'
            if field != '':
                x_comp = self.get_expression_data("%sx%i"%(field,self._selected_peak))
                y_comp = self.get_expression_data("%sy%i"%(field,self._selected_peak))

                vectors = np.vstack((x_comp, y_comp)).T
                vectors *= self.vector_scale
                self.plotdata.set_data('vectors',vectors)
            else:
                print "%s field not recognized for vector plots."%field
                if 'vectors' in self.plotdata.arrays:
                    self.plotdata.del_data('vectors')
                
        else:
            if 'vectors' in self.plotdata.arrays:
                self.plotdata.del_data('vectors')
                # clear vector data
        if self.get_expression_name() not in ["None",'']:
            data = self.get_expression_data(self.get_expression_name())
            self.plotdata.set_data('color', data)
        else:
            if 'color' in self.plotdata.arrays:
                self.plotdata.del_data('color')

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
            prefix = self._characteristics[self._characteristic][0].lower()
            expression = prefix + str(self._selected_peak)
            if expression != "":
                data = self.get_expression_data(expression)
                self.plotdata.set_data('color', data)
        return expression

    def get_expression_data(self, expression, table_loc="/cell_peaks"):
        target_table = self.chest.getNode(table_loc)
        uv = target_table.colinstances
        # apply any shortcuts/macros
        expression = self.remap_distance_expressions(expression)
        # evaluate the math expression
        data = t.Expr(expression, uv).eval()
        # pick out the indices for only the active image
        indices = target_table.get_where_list(
            '(omit==False) & (filename == "%s")' % self.get_active_name())
        # access the array data for those indices
        data=data[indices]
        return data
    
    def remap_distance_expressions(self, expression):
        import re
        pattern = re.compile("dist\((\s*\d+\s*),(\s*\d+\s*)\)")
        expression = pattern.sub(r"((x\1-x\2)**2+(y\1-y\2)**2)**0.5", expression)
        return expression