from traits.api import Instance, Int, Float, Str, HasTraits, on_trait_change
from chaco.api import BasePlotContainer, PlotGraphicsContext
from enaml.application import Application

class SaveFileController(HasTraits):
    plot = Instance(BasePlotContainer)
    # width and height are defined in inches.  These are translated
    #   internally into pixels
    plot_width = Int(800)
    plot_height = Int(600)
    physical_plot_width = Float(4)
    physical_plot_height = Float(3)
    dpi = Int(72)
    plot_title = Str('')
    _session_id = Str('')
    
    def __init__(self, plot, parent):
        self.plot = plot
        self.plot_title = self.get_plot_title(plot)
        self.parent=parent
    
    def save_plot(self, filename):
        self._save_plot(self.plot, filename, self.plot_width, self.plot_height,
                        self.dpi)
        self.parent.log_action("save plot", 
                               controller=self.parent.__class__.__name__,
                               dpi=self.dpi,
                               width=self.plot_width,
                               height=self.plot_height,
                               filename=filename)
        Application.instance().end_session(self._session_id)
    
    def _save_plot(self, plot, filename, width=800, height=600, dpi=72):
        self.set_plot_title(plot, self.plot_title)
        original_outer_bounds = plot.outer_bounds
        plot.outer_bounds = [width, height]
        plot.do_layout(force=True)
        gc = PlotGraphicsContext((width, height), dpi=dpi)
        gc.render_component(plot)
        gc.save(filename)
        plot.outer_bounds = original_outer_bounds

    def set_plot_title(self, plot, title):
        self.get_base_plot(plot).title = title
        
    def get_plot_title(self, plot_or_container):
        return self.get_base_plot(self.plot).title        
        
    def get_base_plot(self, plot_or_container):
        # only Plot object have title attributes
        if hasattr(plot_or_container,'title'):
            # only the base plot has the title set
            if 'base_plot' in plot_or_container.plots:
                return plot_or_container
            else:
                return None
        else:
            # recurse, looking always for the base plot
            if hasattr(plot_or_container, '_components'):
                for component in plot_or_container._components:
                    plot = self.get_base_plot(component)
                    if plot is not None:
                        return plot