from traits.api import Int, Bool
from analyzarr.ui.renderers import HasRenderer

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
            
    def log_action(self, action, **parameters):
        self.parent.log_action(action, **parameters)