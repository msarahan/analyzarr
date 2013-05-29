from chaco.tools.api import ScatterInspector, DragTool
from numpy import zeros

class DataspaceMoveTool(DragTool):
    """
    Modifies the data values of a plot.  Only works on instances
    of BaseXYPlot or its subclasses
    """
    event_state = Enum("normal", "dragging")
    _prev_pt = CArray
    def is_draggable(self, x, y):
        return self.component.hittest((x,y))
    def drag_start(self, event):
        data_pt = self.component.map_data((event.x, event.y), all_values=True)
        self._prev_pt = data_pt
        event.handled = True
    def dragging(self, event):
        plot = self.component
        cur_pt = plot.map_data((event.x, event.y), all_values=True)
        dx = cur_pt[0] - self._prev_pt[0]
        dy = cur_pt[1] - self._prev_pt[1]
        index = plot.index.get_data() + dx
        value = plot.value.get_data() + dy
        plot.index.set_data(index, sort_order=plot.index.sort_order)
        plot.value.set_data(value, sort_order=plot.value.sort_order)
        self._prev_pt = cur_pt
        event.handled = True
        plot.request_redraw()

class PeakSelectionTool(ScatterInspector):
    def _deselect(self, index=None):
        super(PeakSelectionTool, self)._deselect(index)
        self._update_mask()
    
    # override this method so that we only select one peak at a time
    def _select(self, index, append=False):
        super(PeakSelectionTool, self)._select(index, append)
        self._update_mask()
        
    def _update_mask(self):
        plot = self.component
        for name in ('index', 'value'):
            if not hasattr(plot, name):
                continue
            md = getattr(plot, name).metadata
            mask = zeros(getattr(plot, name).get_data().shape[0],
                         dtype=bool)
            mask[list(md[self.selection_metadata_name])]=True
            md['selection_masks'] = mask