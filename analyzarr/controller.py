# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import traits.api as t
from plotting.image import ImagePlot
from plotting.ucc import CellCropper
from file_import import filters
import tables as tb

# essential tasks:

class HighSeasAdventure(t.HasTraits):
    # traits of importance:
    # current image index
    selected_image = t.Int(0)
    # current cell index
    selected_cell = t.Int(0)
    selected_image_cell = t.Int(0)
    # where plot data should come from
    active_data_source = t.Str("rawdata")
    # definition of any attribute or combination of attributes to be mapped
    
    
    def __init__(self, treasure_chest, *args, **kw):
        self.chest = treasure_chest

    def set_active_index(self, img_idx):
        nodes = self.chest.listNodes('/rawdata')
        if self.active_data_source is "rawdata":
            self.selected_image = img_idx
            self.selected_cell = 0
        elif self.active_data_source is 'cells':
            diff = img_idx - self.selected_image_cell
            # select a different parent image if we go out of range of this one
            if (self.selected_cell+diff) > len( [x['idx'] for x in self.chest.root.cell_description.where(
                'original_image == "%s"' % nodes[self.selected_image])]):
                if self.selected_image < len(nodes):
                    self.selected_image += 1
                    self.selected_image_cell = 0
                else:
                    self.selected_image = 0
                    self.selected_image_cell = 0
            else:
                self.selected_cell = img_idx
                if img_idx == 0:
                    self.selected_image_cell = 0
                else:
                    self.selected_image_cell = self.selected_cell + diff

    def set_active_data(self, active_data = 'rawdata'):
        self.active_data_source = active_data
            
    def get_active_data(self):
        nodes = self.chest.listNodes('/%s'%self.active_data_source)
        if self.active_data_source is 'rawdata':
            return nodes[self.selected_image][:]
        elif self.active_data_source is 'cells':
            # find the parent that this cell comes from
            parent = self.chest.root.cell_description.read(start = self.selected_cell, 
                                                           stop = self.selected_cell + 1,
                                                           field = "original_image")
            # select that parent as the selected image
            self.selected_image = int([x['idx'] for x in 
                                   self.chest.root.image_description.iterrows()
                                   if x['filename'] == parent][0])
            
            # return the cell data
            return nodes[self.selected_image][self.selected_image_cell,:,:]

    def get_active_name(self):
        nodes = self.chest.listNodes('/rawdata')
        if self.active_data_source is 'rawdata':
            return nodes[self.selected_image].name
        elif self.active_data_source is 'cells':  
            return '(from %s)' %nodes[self.selected_image].name

    def get_num_files(self):
        if self.active_data_source is 'rawdata':
            return len(self.chest.listNodes('/rawdata'))
        elif self.active_data_source is 'cells':          
            return self.chest.root.cell_description.nrows
    # get plots
    def spyglass(self):
        chaco_plot = ImagePlot(self)
        chaco_plot.configure_traits()
    # run analyses
        
    ## fire up cell cropper
    def cell_cropper(self):
        self.set_active_data('rawdata')
        ui = CellCropper(self)
        ui.configure_traits()

    def add_cells(self, name, data, locations):
        ds = self.chest.createCArray(self.chest.root.cells, 
                                    name, 
                                    tb.Atom.from_dtype(data.dtype),
                                    data.shape,
                                    filters=filters
                                    )
        ds[:] = data
        self.chest.flush()
        
        loc = self.chest.root.cell_description.row
        
        for idx in xrange(locations.shape[0]):
            loc['idx'] = idx
            # TODO: generalize so that data can come from anywhere
            loc['input_data'] = '/root/rawdata'
            loc['original_image'] = name
            loc['x_coordinate'] = locations[idx, 0]
            loc['y_coordinate'] = locations[idx, 1]
            loc.append()
        self.chest.root.cell_description.flush()
        self.chest.flush()
        #self.active_data_source = 'cells'
        

    def _get_image_data(self, datatype, slab=[]):
        """
        Gets some slab of data from the HDF5 file
        @param rawdata: string; one of 
            'rawdata' - the collection of raw images
            'cells' - the cells cropped from the raw images
            'mda_image_results' - mda results (eigenimages and scores) from the raw images
            'mda_cells_results' - mda results (eigenimages and scores) from the cell stacks
        @param slab: list of tuples; the first is the origin to start slicing from; the second 
            is the coordinate to slice to.
            for example, given a 3D stack, dimensions (10, 512, 512), which would be a stack of 512x512 images, 10 deep:
            slab = [(0,0,0), (5,512,512)]  # will give you the first five images
            slab = [(0,128,128), (10, 384, 384)] #will give you the central 256x256 area of the whole stack
        """
        pass
    
    def plot_images(self):
        main_window = None
        self.set_active_data('rawdata')
        self.spyglass()


    def plot_cells(self):
        main_window = None
        self.set_active_data('cells')
        #
        self.spyglass()


        
