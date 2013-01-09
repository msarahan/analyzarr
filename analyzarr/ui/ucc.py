# -*- coding: utf-8 -*-
# Copyright 2007-2011 The analyzarr developers
#
# This file is part of  analyzarr.
#
# analyzarr is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# analyzarr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with  analyzarr.  If not, see <http://www.gnu.org/licenses/>.

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

from pyface.api import ProgressDialog

from types import ListType, TupleType

import numpy as np
from collections import OrderedDict
import os

import peak_char as pc
import cv_funcs


#import ipdb

from viewers import StackViewer
from single_plot import key_bindings

"""
try:
    __IPYTHON__
except NameError:
    nested = 0
    args = ['']
else:
    print "Running nested copies of IPython."
    print "The prompts for the nested copy have been modified"
    nested = 1
    # what the embedded instance will see as sys.argv:
    args = ['-pi1','In <\\#>: ','-pi2','   .\\D.: ',
            '-po','Out<\\#>: ','-nosep']

# First import the embeddable shell class
from IPython.Shell import IPShellEmbed

# Now create an instance of the embeddable shell. The first argument is a
# string with options exactly as you would type them if you were starting
# IPython at the system command line. Any parameters you want to define for
# configuration can thus be specified here.
ipshell = IPShellEmbed(args,
                       banner = 'Dropping into IPython',
                       exit_msg = 'Leaving Interpreter, back to program.')
"""
class OK_custom_handler(Handler):
    def close(self, info, is_ok):
        if is_ok:
            info.object.crop_cells()
        return True      

#(value=[Array(dtype=np.float32,value=np.zeros((64,64)))])
# (value=[Array(shape=(None,3), value=np.array(([[0,0,0]])))])
# TODO: this should be either a single plot or a dual plot?
class CellCropper(StackViewer):
    template = Array
    CC = Array
    peaks = List
    zero=Int(0)
    tmp_size = Range(low=2, high=512, value=64, cols=4)
    max_pos_x=Property(depends_on=['tmp_size'])
    max_pos_y=Property(depends_on=['tmp_size'])
    top = Range(low='zero',high='max_pos_y', value=20, cols=4)
    left = Range(low='zero',high='max_pos_x', value=20, cols=4)
    is_square = Bool
    tmp_plot = Instance(Plot)
    findpeaks = Button
    peak_width = Range(low=2, high=200, value=10)
    ShowCC = Bool
    numpeaks_total = Int(0,cols=5)
    numpeaks_img = Int(0,cols=5)
    OK_custom=OK_custom_handler
    thresh=Trait(None,None,List,Tuple,Array)
    thresh_upper=Float(1.0)
    thresh_lower=Float(-1.0)
    tmp_img_idx=Int(0)

    csr=Instance(BaseCursorTool)

    traits_view = View(
        Group(
            Group(
                Item("img_container",editor=ComponentEditor(), show_label=False),
                HGroup(
                    Item("ShowCC", editor=BooleanEditor(), label="Show cross correlation image"),
                    Spring(),
                    Item("prev_img",editor=ButtonEditor(label="<"),show_label=False, enabled_when='numfiles > 1'),
                    Item("next_img",editor=ButtonEditor(label=">"),show_label=False, enabled_when='numfiles > 1'),
                    ),
                label="Original image", show_border=True, trait_modified="tab_selected",
                orientation='vertical',),
            VGroup(
                Group(
                    HGroup(
                        Item("left", label="Left coordinate", style="custom"),
                        Spring(),
                        Item("top", label="Top coordinate", style="custom"),
                        ),
                    Item("tmp_size", label="Template size", style="custom"),
                    Item("tmp_plot",editor=ComponentEditor(height=256, width=256), show_label=False, resizable=True),
                    label="Template", show_border=True),
                Group(
                    HGroup(
                        Item("peak_width", label="Peak width", style="custom"),
                        Spring(),
                        Item("findpeaks",editor=ButtonEditor(label="Find Peaks"),show_label=False),
                        ),
                    HGroup(
                        Item("thresh_lower",label="Threshold Lower Value", editor=TextEditor(evaluate=float,
                                                                                             format_str='%1.4f')),
                        Spring(),
                        Item("thresh_upper",label="Threshold Upper Value", editor=TextEditor(evaluate=float,
                                                                                             format_str='%1.4f')),
                    ),
                    HGroup(
                        Item("numpeaks_img",label="Number of Cells selected (this image)",style='readonly'),
                        Spring(),
                        Item("numpeaks_total",label="Total",style='readonly'),                          
                        ),
                    label="Peak parameters", show_border=True),
                ),
            orientation='horizontal'),
        buttons = [ Action(name='OK', enabled_when = 'numpeaks_total > 0' ),
            CancelButton ],
        title="Template Picker",
        handler=OK_custom, kind='livemodal',
        key_bindings = key_bindings,
        width=940, height=530,resizable=True)        

    def __init__(self, controller, *args, **kw):
        super(CellCropper, self).__init__(controller, *args, **kw)
        try:
            import cv
        except:
            try:
                import cv2.cv as cv
            except:
                print "OpenCV unavailable.  Can't do cross correlation without it.  Aborting."
                return None
        self.OK_custom=OK_custom_handler()
        self.template = self.data[self.top:self.top+self.tmp_size,self.left:self.left+self.tmp_size]
        tmp_plot_data=ArrayPlotData(imagedata=self.template)
        tmp_plot=Plot(tmp_plot_data,default_origin="top left")
        tmp_plot.img_plot("imagedata", colormap=jet)
        tmp_plot.aspect_ratio=1.0
        self.tmp_plot=tmp_plot
        self.tmp_plotdata=tmp_plot_data
        self.crop_sig=None

    def render_image(self):
        plot = super(CellCropper,self).render_image()
        img=plot.img_plot("imagedata", colormap=gray)[0]
        csr = CursorTool(img, drag_button='left', color='white',
                         line_width=2.0)
        self.csr=csr
        csr.current_position=self.left, self.top
        img.overlays.append(csr)
        self.img_plot=plot
        return plot

    # TODO: use base class render_scatter_overlay method
    def render_scatplot(self):
        peakdata=ArrayPlotData()
        peakdata.set_data("index",self.peaks[self.img_idx][:,0])
        peakdata.set_data("value",self.peaks[self.img_idx][:,1])
        peakdata.set_data("color",self.peaks[self.img_idx][:,2])
        scatplot=Plot(peakdata,aspect_ratio=self.img_plot.aspect_ratio,default_origin="top left")
        scatplot.plot(("index", "value", "color"),
                      type="cmap_scatter",
                      name="my_plot",
                      color_mapper=jet(DataRange1D(low = 0.0,
                                       high = 1.0)),
                      marker = "circle",
                      fill_alpha = 0.5,
                      marker_size = 6,
                      )
        scatplot.x_grid.visible = False
        scatplot.y_grid.visible = False
        scatplot.range2d=self.img_plot.range2d
        self.scatplot=scatplot
        self.peakdata=peakdata
        return scatplot

    def _image_plot_container(self):
        plot = self.render_image()

        # Create a container to position the plot and the colorbar side-by-side
        self.container=OverlayPlotContainer()
        self.container.add(plot)
        self.img_container = HPlotContainer(use_backbuffer = False)
        self.img_container.add(self.container)
        self.img_container.bgcolor = "white"
        #ipdb.set_trace()

        if self.numpeaks_img>0:
            scatplot = self.render_scatplot()
            self.container.add(scatplot)
            colorbar = self.draw_colorbar()
            self.img_container.add(colorbar)
        return self.img_container

    def draw_colorbar(self):
        scatplot=self.scatplot
        cmap_renderer = scatplot.plots["my_plot"][0]
        selection = ColormappedSelectionOverlay(cmap_renderer, fade_alpha=0.35, 
                                                selection_type="range")
        cmap_renderer.overlays.append(selection)
        if self.thresh is not None:
            cmap_renderer.color_data.metadata['selections']=self.thresh
            cmap_renderer.color_data.metadata_changed={'selections':self.thresh}
        # Create the colorbar, handing in the appropriate range and colormap
        colormap=scatplot.color_mapper
        colorbar = ColorBar(
            index_mapper=LinearMapper(
                range=DataRange1D(
                    low = -1.0,
                    high = 1.0)
                ),
            orientation='v',
            resizable='v',
            width=30,
            padding=20)
        colorbar_selection=RangeSelection(component=colorbar)
        colorbar.tools.append(colorbar_selection)
        ovr=colorbar.overlays.append(
            RangeSelectionOverlay(component=colorbar,
                                  border_color="white",
                                  alpha=0.8,
                                  fill_color="lightgray",
                                  metadata_name='selections'))
        #ipshell('colorbar, colorbar_selection and ovr available:')
        self.cbar_selection=colorbar_selection
        self.cmap_renderer=cmap_renderer
        colorbar.plot = cmap_renderer
        colorbar.padding_top = scatplot.padding_top
        colorbar.padding_bottom = scatplot.padding_bottom
        self.colorbar=colorbar
        return colorbar

    @on_trait_change('ShowCC')
    def toggle_cc_view(self):
        if self.ShowCC:
            self.update_CC()
            grid_data_source = self.img_plot.range2d.sources[0]
            grid_data_source.set_data(np.arange(self.CC.shape[1]), 
                                      np.arange(self.CC.shape[0]))
        else:
            self.img_plotdata.set_data("imagedata",self.data)
        self.redraw_plots()

    @on_trait_change("img_idx")
    def update_img_depth(self):
        """
        TODO: We look up the index in the model - first get a list of files, then get the name
        of the file at the given index.
        """
        super(CellCropper, self).update_img_depth()
        if self.ShowCC:
            self.update_CC()
        self.redraw_plots()        

    def _get_max_pos_x(self):
        max_pos_x=self.data.shape[-1]-self.tmp_size-1
        if max_pos_x>0:
            return max_pos_x
        else:
            return None

    def _get_max_pos_y(self):
        max_pos_y=self.data.shape[-2]-self.tmp_size-1
        if max_pos_y>0:
            return max_pos_y
        else:
            return None

    @on_trait_change('left, top')
    def update_csr_position(self):
        if self.left>0:        
            self.csr.current_position=self.left,self.top

    @on_trait_change('csr:current_position')
    def update_top_left(self):
        if self.csr.current_position[0]>0 or self.csr.current_position[1]>0:
            if self.csr.current_position[0]>self.max_pos_x:
                if self.csr.current_position[1]<self.max_pos_y:
                    self.top=self.csr.current_position[1]
                else:
                    self.csr.current_position=self.max_pos_x, self.max_pos_y
            elif self.csr.current_position[1]>self.max_pos_y:
                self.left,self.top=self.csr.current_position[0],self.max_pos_y
            else:
                self.left,self.top=self.csr.current_position
        
    @on_trait_change('left, top, tmp_size')
    def update_tmp_plot(self):
        self.template = self.data[self.top:self.top+self.tmp_size,self.left:self.left+self.tmp_size]
        self.tmp_plotdata.set_data("imagedata", self.template)
        grid_data_source = self.tmp_plot.range2d.sources[0]
        grid_data_source.set_data(np.arange(self.tmp_size), np.arange(self.tmp_size))
        self.tmp_img_idx=self.img_idx
        if self.numpeaks_total>0:
            print "clearing peaks"
            self.peaks=[np.array([[0,0,-1]])]
        self.update_CC()
        return

    def update_CC(self):
        if self.ShowCC:
            self.CC = cv_funcs.xcorr(self.template, self.data)
            self.img_plotdata.set_data("imagedata",self.CC)

    @on_trait_change('cbar_selection:selection')
    def update_thresh(self):
        try:
            thresh=self.cbar_selection.selection
            self.thresh=thresh
            self.cmap_renderer.color_data.metadata['selections']=thresh
            self.thresh_lower=thresh[0]
            self.thresh_upper=thresh[1]
            #cmap_renderer.color_data.metadata['selection_masks']=self.thresh
            self.cmap_renderer.color_data.metadata_changed={'selections':thresh}
            self.container.request_redraw()
            self.img_container.request_redraw()
        except:
            pass

    @on_trait_change('thresh_upper,thresh_lower')
    def manual_thresh_update(self):
        self.thresh=[self.thresh_lower,self.thresh_upper]
        self.cmap_renderer.color_data.metadata['selections']=self.thresh
        self.cmap_renderer.color_data.metadata_changed={'selections':self.thresh}
        self.container.request_redraw()
        self.img_container.request_redraw()

    @on_trait_change('peaks,cbar_selection:selection,img_idx')
    def calc_numpeaks(self):
        try:
            thresh=self.cbar_selection.selection
            self.thresh=thresh
        except:
            thresh=[]
        if thresh==[] or thresh==() or thresh==None:
            thresh=(-1,1)
        self.numpeaks_total=int(np.sum([np.sum(np.ma.masked_inside(self.peaks[i][:,2],thresh[0],thresh[1]).mask) for i in xrange(len(self.peaks))]))
        try:
            self.numpeaks_img=int(np.sum(np.ma.masked_inside(self.peaks[self.img_idx][:,2],thresh[0],thresh[1]).mask))
        except:
            self.numpeaks_img=0

    @on_trait_change('findpeaks')
    def locate_peaks(self):
        peaks=[]
        progress = ProgressDialog(title="Peak finder progress", message="Finding peaks on %s images"%self.numfiles, max=self.numfiles, show_time=True, can_cancel=False)
        progress.open()
        for idx in xrange(self.numfiles):
            self.controller.set_active_index(idx)
            self.data = self.controller.get_active_image()[:]
            self.CC = cv_funcs.xcorr(self.template, self.data)
            # peak finder needs peaks greater than 1.  Multiply by 255 to scale them.
            pks=pc.two_dim_findpeaks(self.CC*255, peak_width=self.peak_width, medfilt_radius=None)
            pks[:,2]=pks[:,2]/255.
            peaks.append(pks)
            progress.update(idx+1)
        #ipdb.set_trace()
        self.peaks=peaks
        self.redraw_plots()
        
    def mask_peaks(self,idx):
        thresh=self.cbar_selection.selection
        if thresh==[]:
            thresh=(-1,1)
        mpeaks=np.ma.asarray(self.peaks[idx])
        mpeaks[:,2]=np.ma.masked_outside(mpeaks[:,2],thresh[0],thresh[1])
        return mpeaks

    @on_trait_change("peaks")
    def redraw_plots(self):
        oldplot=self.img_plot
        self.container.remove(oldplot)
        newplot=self.render_image()
        self.container.add(newplot)
        self.img_plot=newplot

        try:
            # if these haven't been created before, this will fail.  wrap in try to prevent that.
            oldscat=self.scatplot
            self.container.remove(oldscat)
            oldcolorbar = self.colorbar
            self.img_container.remove(oldcolorbar)
        except:
            pass

        if self.numpeaks_img>0:
            newscat=self.render_scatplot()
            self.container.add(newscat)
            self.scatplot=newscat
            colorbar = self.draw_colorbar()
            self.img_container.add(colorbar)
            self.colorbar=colorbar

        self.container.request_redraw()
        self.img_container.request_redraw()

    def crop_cells(self):
        print "cropping cells..."
        for idx in xrange(self.numfiles):
            # filter the peaks that are outside the selected threshold
            self.controller.set_active_index(idx)
            self.data = self.controller.get_active_image()
            self.name = self.controller.get_active_name()
            peaks=np.ma.compress_rows(self.mask_peaks(idx))
            tmp_sz=self.tmp_size
            data=np.zeros((peaks.shape[0],tmp_sz,tmp_sz))
            if data.shape[0] >0:
                for i in xrange(peaks.shape[0]):
                    # crop the cells from the given locations
                    data[i,:,:]=self.data[peaks[i,1]:peaks[i,1]+tmp_sz, 
                                      peaks[i,0]:peaks[i,0]+tmp_sz]
                # send the data to the controller for storage in the chest
                self.controller.add_cells(name = self.name, data = data,
                                      locations = peaks)
        

