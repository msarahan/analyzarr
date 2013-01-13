# -*- coding: utf-8 -*-

from traits.api import HasTraits
from chaco.tools.api import PanTool, ZoomTool, RangeSelection, \
     RangeSelectionOverlay
from chaco.api import Plot, ArrayPlotData, jet, gray, \
     ColorBar, ColormappedSelectionOverlay, LinearMapper
from chaco.tools.cursor_tool import CursorTool, BaseCursorTool

from chaco.data_range_1d import DataRange1D

class HasRenderer(HasTraits):
    def render_plot(self, data, data_str):
        """
        data is a numpy array to be plotted as a line plot.
        The first column of the data is used as x, the second is used as y.
        """
        plotdata = ArrayPlotData(x = data[:,0], y = data[:,1])
        plot = Plot(plotdata)
        
        #plot.title="%s of %s: "%(self.img_idx+1,self.numfiles)+self.filename
        #plot.aspect_ratio=float(data.shape[1])/float(data.shape[0])
    
        # attach the rectangle tool
        plot.tools.append(PanTool(plot,drag_button="right"))
        zoom = ZoomTool(plot, tool_mode="box", always_on=False, aspect_ratio=plot.aspect_ratio)
        plot.overlays.append(zoom)
        return plot
        # the thing that gets the Plot object should do something like this:
        #plot.plot(("x", "y"), type = 'line', color = 'blue')[0]

    def render_image(self, img_data, title=None):
        plot = Plot(img_data,default_origin="top left")
        
        # todo: generalize title and aspect ratio
        plot.title = title
        data_array = img_data.arrays['imagedata']
        plot.aspect_ratio=float(data_array.shape[1]) / float(data_array.shape[0])
        # attach the rectangle tool
        plot.tools.append(PanTool(plot,drag_button="right"))
        zoom = ZoomTool(plot, tool_mode="box", always_on=False, aspect_ratio=plot.aspect_ratio)
        plot.overlays.append(zoom)
        return plot
        # the thing that gets the Plot object should do something like this:
        #img = plot.img_plot("imagedata", colormap=gray)[0]

    def render_scatter_overlay(self, base_plot, location_data = None, color_data = None):
        if location_data is None:
            return Plot()
        peakdata=ArrayPlotData()
        peakdata.set_data("index", location_data[:,0])
        peakdata.set_data("value", location_data[:,1])
        if color_data is not None:
            peakdata.set_data("color", color_data)
        scatplot=Plot(peakdata,aspect_ratio = base_plot.aspect_ratio,
                      default_origin="top left")
        if color_data is not None:
            scatplot.plot(("index", "value", "color"),
                      type="cmap_scatter",
                      name="scatter_plot",
                      color_mapper=jet(DataRange1D(low = np.min(color_data),
                                       high = np.max(color_data))),
                      marker = "circle",
                      fill_alpha = 0.5,
                      marker_size = 6,
                      )
        else:
            scatplot.plot(("index","value"), type = "scatter",
                          name = "scatter_plot",
                          marker = "circle",
                          fill_alpha = 0.5,
                          marker_size = 6,
                          )
        scatplot.x_grid.visible = False
        scatplot.y_grid.visible = False
        scatplot.range2d = base_plot.range2d
        return scatplot
        # usage: should create container (overlayplotcontainer); add both 
        #   base_plot and this returned plot to it.

    def render_quiver_overlay(self, location_data=None, vector_data=None, 
                              color = 'white', scale=1):
        if location_data is None:
            return Plot()
        pass
