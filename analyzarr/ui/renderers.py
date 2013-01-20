# -*- coding: utf-8 -*-

from traits.api import Float, List, Tuple, Array, Trait, Instance
from traits.api import HasTraits
from chaco.tools.api import PanTool, ZoomTool, RangeSelection, \
     RangeSelectionOverlay
from chaco.api import Plot, ArrayPlotData, jet, gray, \
     ColorBar, ColormappedSelectionOverlay, LinearMapper
from chaco.tools.cursor_tool import CursorTool, BaseCursorTool

from chaco.data_range_1d import DataRange1D

class HasRenderer(HasTraits):
    quiver_scale = Float(1.0)
    scatter_threshold = Trait(None,None,List,Tuple,Array)
    colorbar_selection = Instance(RangeSelection)
    # TODO: do we need the scatter plot renderer for the transparency manipulation?
    
    def get_line_plot(self, array_plot_data, title=None):
        return self._render_line_plot(array_plot_data)

    def get_simple_image_plot(self, array_plot_data, title=None):
        plot = self._render_image(array_plot_data, title)
        return plot

    # TODO - add optional appearance tweaks
    def get_scatter_overlay_plot(self, array_plot_data, title=None):
        colorbar = None
        image_plot = _render_image(array_plot_data, title)
        scatter_plot, colorbar = _render_scatter_overlay(array_plot_data)
        image_container = OverlayPlotContainer(image_plot, scatter_plot)
        if colorbar is not None:
            image_container = HPlotContainer(image_container, colorbar)
        return image_container
            
    # TODO - add optional appearance tweaks
    def get_scatter_quiver_plot(self, array_plot_data, title=None):
        colorbar = None
        image_plot = _render_image(array_plot_data, title)
        scatter_plot, colorbar = _render_scatter_overlay(array_plot_data)
        quiver_plot = _render_quiver_overlay(array_plot_data)
        image_container = OverlayPlotContainer(image_plot, quiver_plot, 
                                               scatter_plot)
        if colorbar is not None:
            image_container = HPlotContainer(image_container, colorbar)
        return image_container
    
    def _render_plot(self, data):
        """
        data is a numpy array to be plotted as a line plot.
        The first column of the data is used as x, the second is used as y.
        """
        plotdata = ArrayPlotData(x = data[:,0], y = data[:,1])
        plot = Plot(plotdata)
        colorbar = None
    
        # attach the pan and zoom tools
        plot.tools.append(PanTool(plot,drag_button="right"))
        zoom = ZoomTool(plot, tool_mode="box", always_on=False, aspect_ratio=plot.aspect_ratio)
        plot.overlays.append(zoom)
        return plot, colorbar

    def _render_image(self, image_data, title=None):
        plot = Plot(image_data,default_origin="top left")        
        plot.img_plot("imagedata", colormap=gray, name="image_plot")
        # todo: generalize title and aspect ratio
        plot.title = title
        data_array = image_data.arrays['imagedata']
        plot.aspect_ratio=float(data_array.shape[1]) / float(data_array.shape[0])
        # attach the rectangle tool
        plot.tools.append(PanTool(plot,drag_button="right"))
        zoom = ZoomTool(plot, tool_mode="box", always_on=False, aspect_ratio=plot.aspect_ratio)
        plot.overlays.append(zoom)
        return plot
        # the thing that gets the Plot object should do something like this:
        #img = plot.img_plot("imagedata", colormap=gray)[0]

    def _render_scatter_overlay(self, base_plot, array_plot_data,
                                marker="circle", fill_alpha="0.5",
                                marker_size=6):
        plot = Plot(image_data, aspect_ratio = base_plot.aspect_ratio, 
                    default_origin="top left")
        # the simple case - no color data
        if "color" not in array_plot_data.keys():
            scatter_plot = plot.plot(("index", "value"),
                          type="scatter",
                          name="scatter_plot",
                          marker = marker,
                          fill_alpha = fill_alpha,
                          marker_size = marker_size,
                          )
            colorbar = None
        # slightly more involved: colors mapped to some value
        # with a threshold control that links to transparency
        else:
            color_data = array_plot_data.get_data('color')
            scatter_plot = plot.plot(("index", "value", "color"),
                          type="cmap_scatter",
                          name="scatter_plot",
                          marker = marker,
                          fill_alpha = fill_alpha,
                          marker_size = marker_size,
                          )
            colorbar = ColorBar(index_mapper = LinearMapper(
                range = DataRange1D(
                    low = np.min(color_data),
                    high = np.max(color_data),
                    )
                ),
                orientation = 'v',
                resizable = 'v',
                width = 30,
                )
            # this part is for making the colormapped points fade when they
            #  are not selected by the threshold.
            # The renderer is the actual class that does the rendering - 
            # the Plot class calls this other class.  When we say 
            #   plots['scatter_plot']
            # we are getting the named plot that we created above.
            # The extra [0] on the end is because we get a list - in case
            # there is more than one plot named "scatter_plot"
            scatter_renderer = scatter_plot.plots["scatter_plot"][0]
            selection = ColormappedSelectionOverlay(scatter_renderer, 
                                                    fade_alpha=0.35, 
                                                    selection_type="range")
            scatter_renderer.overlays.append(selection)
            if self.threshold is not None:
                scatter_renderer.color_data.metadata['selections']=self.threshold
                scatter_renderer.color_data.metadata_changed={'selections':self.threshold}
            colorbar_selection=RangeSelection(component=colorbar)
            colorbar.tools.append(colorbar_selection)
            colorbar.overlays.append(RangeSelectionOverlay(component=colorbar,
                                              border_color="white",
                                              alpha=0.8,
                                              fill_color="lightgray",
                                              metadata_name='selections',
                                              )
                                     ) 
            colorbar.padding_top = scatter_renderer.padding_top
            colorbar.padding_bottom = scatter_renderer.padding_bottom
        scatter_plot.x_grid.visible = False
        scatter_plot.y_grid.visible = False
        scatter_plot.range2d = base_plot.range2d
        return scatter_plot, colorbar

    def _render_quiver_overlay(self, base_plot, array_plot_data, line_color="white", 
                               line_width=1.0, arrow_size=5):
        plot = Plot(image_data, aspect_ratio = base_plot.aspect_ratio, 
                    default_origin="top left")
        plot.quiverplot(("index", "value", "vectors"), line_color=line_color,
                        line_width=line_width, arrow_size=arrow_size)
        quiverplot.x_grid.visible = False
        quiverplot.y_grid.visible = False
        quiverplot.range2d = base_plot.range2d
        return quiverplot