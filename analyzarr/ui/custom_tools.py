from chaco.tools.api import ScatterInspector
from numpy import zeros

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