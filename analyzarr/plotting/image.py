# -*- coding: utf-8 -*-

from traits.api \
     import HasTraits, Array, Int, Float, Range, Instance, on_trait_change, \
     Bool, Button, Property, Event, Tuple, Any, List, Trait, CInt
from traitsui.api import View, Item, Group, HFlow, VGroup, Tabbed, \
     BooleanEditor, ButtonEditor, CancelButton, Handler, Action, Spring, \
     HGroup, TextEditor
from chaco.tools.api import PanTool, ZoomTool, RangeSelection, \
     RangeSelectionOverlay
from chaco.api import Plot, ArrayPlotData, jet, gray, \
     ColorBar, ColormappedSelectionOverlay, HPlotContainer, LinearMapper, \
     OverlayPlotContainer
from enable.api import ComponentEditor, KeySpec, Component
from chaco.tools.cursor_tool import CursorTool, BaseCursorTool
from traitsui.key_bindings import KeyBinding, KeyBindings

from chaco.data_range_1d import DataRange1D

import numpy as np
from collections import OrderedDict
import os

key_bindings = KeyBindings(
    KeyBinding( binding1    = 'Left',
                description = 'Step left through images',
                method_name = 'decrease_img_idx' ),
    KeyBinding( binding1    = 'Right',
                description = 'Step right through images',
                method_name = 'increase_img_idx' ),
)

class ImagePlot(HasTraits):

    zero=Int(0)
    img_plot = Instance(Plot)
    next_img = Button
    prev_img = Button
    tab_selected = Event
    img_container = Instance(Component)
    container = Instance(Component)
    colorbar= Instance(Component)
    cbar_selection = Instance(RangeSelection)
    cbar_selected = Event
    numfiles=Int(1)
    img_idx=Int(0)

    traits_view = View(
        Group(
            Group(
                Item("img_container",editor=ComponentEditor(), show_label=False),
                HGroup(
                    Spring(),
                    Item("prev_img",editor=ButtonEditor(label="<"),show_label=False, enabled_when='numfiles > 1'),
                    Item("next_img",editor=ButtonEditor(label=">"),show_label=False, enabled_when='numfiles > 1'),
                    ),
                label="Image", show_border=True, trait_modified="tab_selected",
                orientation='vertical',
                ),
            orientation='horizontal'
            ),
        title="Image Viewer",
        key_bindings = key_bindings,
        width=700, height=500,resizable=True
    ) 

    def __init__(self, controller, *args, **kw):
        super(ImagePlot, self).__init__(*args,**kw)
        self.controller = controller
        self.numfiles = controller.get_num_files()
        self.data = controller.get_active_data()
        self.filename = controller.get_active_name()
        self.img_plotdata=ArrayPlotData(imagedata = self.data)
        self.img_container=self._image_plot_container()

    def _image_plot_container(self):
        plot = self.render_image()

        # Create a container to position the plot and the colorbar side-by-side
        self.container=OverlayPlotContainer()
        self.container.add(plot)
        self.img_container = HPlotContainer(use_backbuffer = False)
        self.img_container.add(self.container)
        self.img_container.bgcolor = "white"
        return self.img_container

    def render_image(self):
        plot = Plot(self.img_plotdata,default_origin="top left")
        img=plot.img_plot("imagedata", colormap=gray)[0]
        plot.title="%s of %s: "%(self.img_idx+1,self.numfiles)+self.filename
        plot.aspect_ratio=float(self.data.shape[1])/float(self.data.shape[0])

        # attach the rectangle tool
        plot.tools.append(PanTool(plot,drag_button="right"))
        zoom = ZoomTool(plot, tool_mode="box", always_on=False, aspect_ratio=plot.aspect_ratio)
        plot.overlays.append(zoom)
        self.img_plot=plot
        return plot

    @on_trait_change("img_idx")
    def update_img_depth(self):
        self.controller.set_active_index(self.img_idx)
        self.data = self.controller.get_active_data()
        self.filename = self.controller.get_active_name()
        self.img_plotdata.set_data("imagedata",self.data)
        self.img_plot.title="%s of %s: "%(self.img_idx+1,self.numfiles)+self.filename

    @on_trait_change('next_img')
    def increase_img_idx(self,info):
        if self.img_idx==(self.numfiles-1):
            self.img_idx=0
        else:
            self.img_idx+=1

    @on_trait_change('prev_img')
    def decrease_img_idx(self,info):
        if self.img_idx==0:
            self.img_idx=self.numfiles-1
        else:
            self.img_idx-=1

# depth profile tools

# line profile tools
#   integration width
#   for 2D SI's, limit line to full width of spectrum

# area selector tools - lasso and square
