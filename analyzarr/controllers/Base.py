from traits.api import Int, Bool
from analyzarr.ui.renderers import HasRenderer
import tables as tb

from analyzarr.lib.io.data_structure import filters

class ControllerBase(HasRenderer):
    # current image index
    selected_index = Int(0)
    numfiles = Int(0)
    _can_save = Bool(False)
    _can_change_idx = Bool(False)

    def __init__(self, parent, treasure_chest=None, data_path='/rawdata', *args, **kw):
        super(ControllerBase, self).__init__(*args, **kw)
        self.chest = None
        self.numfiles = 0
        self.data_path = data_path
        self.parent = parent
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.nodes = self.chest.list_nodes(data_path)

    def get_plot(self, plot_id):
        if hasattr(self, plot_id):
            return getattr(self, plot_id)
        else:
            raise NameError('No such plot: %s' % plot_id)

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
            
    # this is a potentially 3D image stack for feeding into analyses
    def get_active_image_set(self, names=None):
        # TODO: this isn't rational for non-3D data yet.
        if names is None:
            # query the raw data table for filenames
            nodes = self.chest.list_nodes(self.data_path)
            data = nodes[0][:]
            # collect all the cells
            for node in nodes[1:]:
                data = np.append(data, node[:], axis=0)
        else:
            # TODO: need to implement image selection
            data = None
        return data

    def get_node_iterator(self):
        nodes = self.chest.list_nodes(self.data_path)
        for node in nodes:
            yield node            
            
    def log_action(self, action, **parameters):
        self.parent.log_action(action, **parameters)
        
    def add_data(self, data, name):
        import tables as tb
        array = self.chest.create_carray(self.data_path,
                                         name,
                                         tb.Atom.from_dtype(data.dtype),
                                         data.shape,
                                         filters = filters,
                                         )
        array[:] = data
        self.chest.flush()        
        
    def get_expression_data(self, expression, table_loc=None, filename=None):
        import tables
        if table_loc is None:
            table_loc=self.data_path
        target_table = self.chest.get_node(table_loc)
        uv = target_table.colinstances
        # apply any shortcuts/macros
        expression = self.remap_distance_expressions(expression)
        # evaluate the math expression
        data = tables.Expr(expression, uv).eval()
        if filename is None:
            filename=self.get_active_name()
        elif filename == "all":
            return data
        # pick out the indices for only the active image
        indices = target_table.get_where_list(
            #'(omit==False) & (filename == "%s")' % self.get_active_name())
            '(filename == "%s")' % filename)
        # access the array data for those indices
        data=data[indices]
        return data
            
    def remap_distance_expressions(self, expression):
        import re
        pattern = re.compile("dist\((\s*\d+\s*),(\s*\d+\s*)\)")
        expression = pattern.sub(r"((x\1-x\2)**2+(y\1-y\2)**2)**0.5", expression)
        return expression    