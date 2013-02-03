# -*- coding: utf-8 -*-

from traits.api import Float, List, Tuple, Array, Trait, Instance, \
     HasTraits, Range
from chaco.tools.api import PanTool, ZoomTool, RangeSelection, \
     RangeSelectionOverlay
from chaco.api import Plot, ArrayPlotData, jet, gray, \
     ColorBar, ColormappedSelectionOverlay, LinearMapper, \
     HPlotContainer, OverlayPlotContainer, BasePlotContainer
from chaco.tools.cursor_tool import CursorTool, BaseCursorTool

from chaco.data_range_1d import DataRange1D

import numpy as np

def _render_plot(self, array_plot_data):
    """
    data is a numpy array to be plotted as a line plot.
    The first column of the data is used as x, the second is used as y.
    """
    plot = Plot(array_plot_data)
    plot.plot(("x","y"), type="line", name="base_plot")[0]

    # attach the pan and zoom tools
    plot.tools.append(PanTool(plot,drag_button="right"))
    zoom = ZoomTool(plot, tool_mode="box", always_on=False, aspect_ratio=plot.aspect_ratio)
    plot.overlays.append(zoom)
    return plot

def _render_image(array_plot_data, title=None):
    plot = Plot(array_plot_data,default_origin="top left")        
    plot.img_plot("imagedata", colormap=gray, name="base_plot")
    # todo: generalize title and aspect ratio
    plot.title = title
    data_array = array_plot_data.arrays['imagedata']
    plot.aspect_ratio=float(data_array.shape[1]) / float(data_array.shape[0])
    # attach the rectangle tool
    plot.tools.append(PanTool(plot,drag_button="right"))
    zoom = ZoomTool(plot, tool_mode="box", always_on=False, aspect_ratio=plot.aspect_ratio)
    plot.overlays.append(zoom)
    return plot

def _create_colorbar(colormap):
    colorbar = ColorBar(index_mapper=LinearMapper(range=colormap.range),
                            color_mapper=colormap,
                            orientation='v',
                            resizable='v',
                            width=30,
                            padding=20)
    colorbar.tools.append(RangeSelection(component=colorbar))
    colorbar.overlays.append(RangeSelectionOverlay(component=colorbar,
                                                   border_color="white",
                                                   alpha=0.8,
                                                   fill_color="lightgray"))
    return colorbar    

def _render_scatter_overlay(base_plot, array_plot_data,
                            marker="circle", fill_alpha=0.5,
                            marker_size=6):
    if 'index' not in array_plot_data.arrays:
        return base_plot, None
    
    scatter_plot = Plot(array_plot_data, aspect_ratio = base_plot.aspect_ratio, 
                default_origin="top left")
    
    # the simple case - no color data
    if "color" not in array_plot_data.arrays:
        scatter_plot.plot(("index", "value"),
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
        scatter_plot.plot(("index", "value", "color"),
                      type="cmap_scatter",
                      name="scatter_plot",
                      color_mapper=jet,
                      marker = marker,
                      fill_alpha = fill_alpha,
                      marker_size = marker_size,
                      )
        # this part is for making the colormapped points fade when they
        #  are not selected by the threshold.
        # The renderer is the actual class that does the rendering - 
        # the Plot class calls this other class.  When we say 
        #   plots['scatter_plot']
        # we are getting the named plot that we created above.
        # The extra [0] on the end is because we get a list - in case
        # there is more than one plot named "scatter_plot"
        scatter_renderer = scatter_plot.plots['scatter_plot'][0]
        selection = ColormappedSelectionOverlay(scatter_renderer, 
                                                fade_alpha=0.35, 
                                                selection_type="range")
        scatter_renderer.overlays.append(selection)

        colorbar = _create_colorbar(scatter_plot.color_mapper)
        colorbar.plot = scatter_renderer
        colorbar.padding_top = scatter_renderer.padding_top
        colorbar.padding_bottom = scatter_renderer.padding_bottom
    scatter_plot.x_grid.visible = False
    scatter_plot.y_grid.visible = False
    scatter_plot.range2d = base_plot.range2d
    return scatter_plot, colorbar

def _render_quiver_overlay(base_plot, array_plot_data, 
                           line_color="white", line_width=1.0, 
                           arrow_size=5):
    if 'index' not in array_plot_data.arrays:
        return base_plot
    plot = Plot(array_plot_data, aspect_ratio = base_plot.aspect_ratio, 
                default_origin="top left")
    plot.quiverplot(("index", "value", "vectors"), name="quiver_plot",
                    line_color=line_color, line_width=line_width, 
                    arrow_size=arrow_size)
    quiverplot.x_grid.visible = False
    quiverplot.y_grid.visible = False
    quiverplot.range2d = base_plot.range2d
    return quiverplot

class HasRenderer(HasTraits):
    _quiver_scale = Float(1.0)
    _colorbar = Instance(ColorBar)
    _colorbar_selection = Instance(RangeSelection)
    _base_plot = Instance(Plot)
    _scatter_plot = Instance(Plot)
    _quiver_plot = Instance(Plot)
    _csr=Instance(BaseCursorTool)    
    
    thresh = Trait([0,1],None,List,Tuple,Array)
    thresh_upper = Range(-1.0, 1.0, 1.0)
    thresh_lower = Range(-1.0, 1.0, -1.0)    
    
    def get_line_plot(self, array_plot_data, title=None):
        plot = self._render_line_plot(array_plot_data)
        # container isn't necessary here, but we do it to keep it consistent
        #   with how the other plot types return data.        
        plot_container = OverlayPlotContainer(plot)
        self._base_plot = plot
        self.plot_container = plot_container
        return plot_container

    def get_simple_image_plot(self, array_plot_data, title=None):
        image_plot = _render_image(array_plot_data=array_plot_data, 
                                        title=title)
        # container isn't necessary here, but we do it to keep it consistent
        #   with how the other plot types return data.
        image_container = OverlayPlotContainer(image_plot)
        self._base_plot = image_plot
        self.image_container = image_container
        return image_container

    # TODO - add optional appearance tweaks
    def get_scatter_overlay_plot(self, array_plot_data, title=None):
        image_plot = _render_image(array_plot_data, title)
        scatter_plot, colorbar = _render_scatter_overlay(image_plot, 
                                                         array_plot_data)
        image_container = OverlayPlotContainer(image_plot, scatter_plot)
        if colorbar is not None:
            image_container = HPlotContainer(image_container, colorbar)
            if self.thresh is not None:
                scatter_renderer = scatter_plot.plots['scatter_plot'][0]
                scatter_renderer.color_data.metadata['selections'] = self.thresh
                scatter_renderer.color_data.metadata_changed={
                    'selections':self.thresh}
            self._colorbar = colorbar
            self._colorbar_selection = colorbar.tools[0]
        self._base_plot = image_plot
        self._scatter_plot = scatter_plot
        self.image_container = image_container
        return image_container
            
    # TODO - add optional appearance tweaks
    def get_scatter_quiver_plot(self, array_plot_data, title=None):
        colorbar = None
        image_plot = _render_image(array_plot_data, title)
        scatter_plot, colorbar = _render_scatter_overlay(image_plot,
                                                         array_plot_data)
        quiver_plot = _render_quiver_overlay(image_plot, array_plot_data)
        image_container = OverlayPlotContainer(image_plot, quiver_plot, 
                                               scatter_plot)
        if colorbar is not None:
            image_container = HPlotContainer(image_container, colorbar)
        self._base_plot = image_plot
        self._scatter_plot = scatter_plot
        self._quiver_plot = quiver_plot
        self.image_container = image_container
        return image_container
    
    def set_plot_title(self, title):
        self._base_plot.title=title