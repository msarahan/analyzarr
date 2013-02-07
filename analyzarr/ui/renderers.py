# -*- coding: utf-8 -*-

from traits.api import Float, List, Tuple, Array, Trait, Instance, \
     HasTraits, Range, Dict
from chaco.tools.api import PanTool, ZoomTool, RangeSelection, \
     RangeSelectionOverlay, DataLabelTool
from chaco.api import Plot, ArrayPlotData, jet, gray, \
     ColorBar, ColormappedSelectionOverlay, LinearMapper, \
     HPlotContainer, OverlayPlotContainer, BasePlotContainer, \
     DataLabel, ScatterInspectorOverlay, PlotGraphicsContext
from chaco.tools.cursor_tool import CursorTool, BaseCursorTool

from chaco.data_range_1d import DataRange1D

#from custom_tools import PeakSelectionTool

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

def _create_colorbar(colormap, tool=None):
    colorbar = ColorBar(index_mapper=LinearMapper(range=colormap.range),
                            color_mapper=colormap,
                            orientation='v',
                            resizable='v',
                            width=30,
                            padding=20)
    if tool=='colorbar':
        colorbar.tools.append(RangeSelection(component=colorbar))
        colorbar.overlays.append(RangeSelectionOverlay(component=colorbar,
                                                   border_color="white",
                                                   alpha=0.8,
                                                   fill_color="lightgray"))
    return colorbar    

def _render_scatter_overlay(base_plot, array_plot_data,
                            marker="circle", fill_alpha=0.5,
                            marker_size=6, tool=None):
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
        scatter_renderer = scatter_plot.plots['scatter_plot'][0]
        colorbar = _create_colorbar(scatter_plot.color_mapper, tool=tool)
        colorbar.plot = scatter_renderer
        colorbar.padding_top = scatter_renderer.padding_top
        colorbar.padding_bottom = scatter_renderer.padding_bottom
        if tool=='colorbar':
            # this part is for making the colormapped points fade when they
            #  are not selected by the threshold.
            # The renderer is the actual class that does the rendering - 
            # the Plot class calls this other class.  When we say 
            #   plots['scatter_plot']
            # we are getting the named plot that we created above.
            # The extra [0] on the end is because we get a list - in case
            # there is more than one plot named "scatter_plot"
            selection = ColormappedSelectionOverlay(scatter_renderer, 
                                                    fade_alpha=0.35, 
                                                    selection_type="range")
            scatter_renderer.overlays.append(selection)
    if tool=='inspector':
        # Attach the inspector and its overlay
        scatter_renderer = scatter_plot.plots['scatter_plot'][0]
        #scatter_plot.tools.append(PeakSelectionTool(scatter_renderer))
        selection = ColormappedSelectionOverlay(scatter_renderer, 
                                                fade_alpha=0.35, 
                                                selection_type="mask")
        scatter_plot.overlays.append(selection)
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

def _create_label(base_plot, point, label_text, show_label_coords=False,
                  movable=True):
    # Another 'bubble' label.  This one sets arrow_min_length=20, so
    # the arrow is not drawn when the label is close to the data point.
    label = DataLabel(component=base_plot, data_point=point,
                       border_padding=10,
                       marker_color="green",
                       marker_size=2,
                       show_label_coords=show_label_coords,
                       label_style='bubble',
                       label_position=(25, 5),
                       label_text=label_text,
                       border_visible=False,
                       arrow_min_length=20,
                       font='modern 14',
                       bgcolor=(0.75, 0.75, 0.75, 1),
                       )
    if movable:
        tool = DataLabelTool(label, drag_button="left",
                          auto_arrow_root=True)
        label.tools.append(tool)
    return label

class HasRenderer(HasTraits):
    _quiver_scale = Float(1.0)
    _colorbar = Instance(ColorBar)
    _colorbar_selection = Instance(RangeSelection)
    _base_plot = Instance(Plot)
    _scatter_plot = Instance(Plot)
    _quiver_plot = Instance(Plot)
    _csr=Instance(BaseCursorTool)
    _labels = Dict({})
    
    thresh = Trait([0,1],None,List,Tuple,Array)
    thresh_upper = Range(-1.0, 1.0, 1.0)
    thresh_lower = Range(-1.0, 1.0, -1.0)
    
    def get_line_plot(self, array_plot_data, title=''):
        plot = self._render_line_plot(array_plot_data)
        # container isn't necessary here, but we do it to keep it consistent
        #   with how the other plot types return data.        
        plot_container = OverlayPlotContainer(plot)
        self._base_plot = plot
        self.plot_container = plot_container
        return plot_container

    def get_simple_image_plot(self, array_plot_data, title=''):
        image_plot = _render_image(array_plot_data=array_plot_data, 
                                        title=title)
        # container isn't necessary here, but we do it to keep it consistent
        #   with how the other plot types return data.
        image_container = OverlayPlotContainer(image_plot)
        self._base_plot = image_plot
        self.image_container = image_container
        return image_container

    # TODO - add optional appearance tweaks
    def get_scatter_overlay_plot(self, array_plot_data, title='', 
                                 tool=None):
        """
        tool can be either:
        'colorbar' - the range selection colobar (for thresholding cells)
        or
        'inspector' - the peak-picking tool that uses clicks to select cells
            from the parent image
        """
        image_plot = _render_image(array_plot_data, title)
        scatter_plot, colorbar = _render_scatter_overlay(image_plot, 
                                    array_plot_data,
                                    tool=tool,)
        image_container = OverlayPlotContainer(image_plot, scatter_plot)
        if colorbar is not None:
            image_container = HPlotContainer(image_container, colorbar)
            if self.thresh is not None:
                scatter_renderer = scatter_plot.plots['scatter_plot'][0]
                scatter_renderer.color_data.metadata['selections'] = self.thresh
                scatter_renderer.color_data.metadata_changed={
                    'selections':self.thresh}
            self._colorbar = colorbar
            if tool == 'colorbar':
                self._colorbar_selection = colorbar.tools[0]
        if tool == 'inspector':
            scatter_renderer = scatter_plot.plots['scatter_plot'][0]
            
        self._base_plot = image_plot
        self._scatter_plot = scatter_plot
        self.image_container = image_container
        return image_container
            
    # TODO - add optional appearance tweaks
    def get_scatter_quiver_plot(self, array_plot_data, title='',
                                add_tool=False):
        colorbar = None
        image_plot = _render_image(array_plot_data, title)
        scatter_plot, colorbar = _render_scatter_overlay(image_plot,
                                                         array_plot_data,
                                                         add_tool=add_tool)
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
        
    # TODO: are we going to need to delete labels somehow?
    def plot_labels(self, labels):
        for label in labels.keys():
            if label in self._labels:
                data_point = labels[label]
                self._labels[label].data_point = data_point
                label_text = '%s: %.2f,%.2f' %(label, data_point[0], data_point[1])
                self._labels[label].label_text = label_text
            else:
                data_point = labels[label]
                label_text = '%s: %.2f,%.2f' %(label, data_point[0], data_point[1])                
                self._labels[label]=_create_label(self._base_plot, 
                                         point=data_point,
                                         label_text=label_text)
    def show_labels(self, show=True):
        for label in self._labels.keys():
            if show:
                self._base_plot.overlays.append(self._labels[label])
            else:
                pass
            
    def _save_plot(self, plot, filename, width=800, height=600, dpi=72):
        original_outer_bounds = plot.outer_bounds
        plot.outer_bounds = [width, height]
        plot.do_layout(force=True)
        gc = PlotGraphicsContext((width, height), dpi=dpi)
        gc.render_component(plot)
        gc.save(filename)
        plot.outer_bounds = original_outer_bounds    