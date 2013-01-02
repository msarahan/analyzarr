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

from renderers import HasRenderer

key_bindings = KeyBindings(
    KeyBinding( binding1    = 'Left',
                description = 'Step left through images',
                method_name = 'decrease_img_idx' ),
    KeyBinding( binding1    = 'Right',
                description = 'Step right through images',
                method_name = 'increase_img_idx' ),
)

class DoubleImagePlot(HasRenderer):
    left_plot = Instance(Plot)
    right_plot = Instance(Plot)
    total_container = Instance(Component)
    left_container = Instance(Component)
    right_container = Instance(Component)    
    colorbar= Instance(Component)
    cbar_selection = Instance(RangeSelection)
    cbar_selected = Event
    left_numfiles = Int(1)
    right_numfiles = Int(1)
    left_img_idx = Int(0)
    right_img_idx = Int(0)

    traits_view = View(
        Group(
            Group(
                HGroup(
                    Item("total_container",editor=ComponentEditor(), show_label=False),
                    ),
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
        width=900, height=500,resizable=True
    )
    
    def __init__(self, controller, *args, **kw):
        super(ImagePlot, self).__init__(*args,**kw)
        self.controller = controller
        self.numfiles = controller.get_num_files()
        # todo: must define two data sources
        self.data_left = controller.get_active_data()
        self.data_right = controller.get_active_data()
        # todo: must base name on active data sources
        self.filename = controller.get_active_name()
        # todo: we'll have two data sources
        self.img_plotdata=ArrayPlotData(imagedata = self.data)
        self._create_image_plot_containers()

    def _create_image_plot_container(self):
        self.left_container=OverlayPlotContainer()
        self.right_container=OverlayPlotContainer()
        self.total_container = HPlotContainer(use_backbuffer = False)
        self.total_container.add(self.left_container)
        self.total_container.add(self.right_container)
        self.total_container.bgcolor = "white"   
    
