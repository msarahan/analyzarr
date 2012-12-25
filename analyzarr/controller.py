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
import numpy as np
from mda import mda_sklearn as mda

import peak_char as pc
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
            self.selected_cell = img_idx

    def set_active_data(self, active_data = 'rawdata'):
        self.active_data_source = active_data

    # TODO: must generalize this more to deal with 3D info being passed around.
    def get_active_data(self):
        nodes = self.chest.listNodes('/%s'%self.active_data_source)
        if self.active_data_source is 'rawdata':
            return nodes[self.selected_image][:]
        elif self.active_data_source is 'cells':
            # find the parent that this cell comes from
            cell_record = self.chest.root.cell_description.read(start = self.selected_cell, 
                                                           stop = self.selected_cell + 1)[0]
            parent = cell_record['original_image']
            # select that parent as the selected image
            self.selected_image = int([x['idx'] for x in 
                                   self.chest.root.image_description.where(
                                       'filename == "%s"' % parent)][0])
            
            # return the cell data
            return nodes[self.selected_image][cell_record['idx'],:,:]

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
        
    def get_cell_set(self, names = None):
        if names is None:
            # query the raw data table for filenames
            nodes = self.chest.listNodes('/cells')
            celldata = nodes[0][:]
            # collect all the cells
            for node in nodes[1:]:
                celldata = np.append(celldata, node[:], axis=0)
        else:
            celldata = None                
        return celldata
    
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

    def characterize_cells(self, peak_width, subpixel = False, target_locations = None,
                           peak_locations = None, target_neighborhood = 20, 
                           medfilt_radius = 5):
        # get the peak attributes
        attribs = pc.peak_attribs_stack(self.get_cell_set(), peak_width=peak_width, subpixel=subpixel, 
                           target_locations=target_locations, peak_locations=peak_locations, 
                           target_neighborhood=target_neighborhood, medfilt_radius=medfilt_radius)
        # transpose the results - they come in the form of one column per image.  Should be one row per image.
        attribs = attribs.T
        # generate a list of column names
        names = [('x%i, y%i, dx%i, dy%i, h%i, o%i, e%i'%((x,)*7)).split(', ') for x in xrange(attribs.shape[1]//7)]
        # flatten that from a list of lists to a simple list
        names = [item for sublist in names for item in sublist]
        # make tuples of each column name and 'f8' for the data type
        dtypes = zip(names, ['f8',]*attribs.shape[1])
        # prepend the index column
        dtypes = [('idx', "i4"),]+dtypes
        # make a blank recarray with our column names and dtypes
        data = np.zeros((attribs.shape[0]), dtype = dtypes)
        # fill in the index column
        data['idx'] = np.arange(attribs.shape[0])
        # for each column name, copy in the data
        for name_idx in xrange(len(names)):
            data[names[name_idx]] = attribs[:,name_idx]
        # populate a table with the results
        self.chest.createTable(self.chest.root, 'cell_peaks', description = data)
        # add an attribute for the total number of peaks recorded
        self.chest.root.cell_peaks.number_of_peaks = attribs.shape[1]//7
        #self.chest.root.cell_peaks.append([data[idx] for idx in xrange(1,attribs.shape[0])])
        self.chest.root.cell_peaks.flush()

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
    
    def _get_ICA_data(self):
        """
        Pre-processes the data to be ready for ICA.  Namely:
        - flattens data to 2D
        - differentiates the data (integrated ICA)
        """
        # TODO: this is only a test - grabs all cell data.
        # reshape the data: 
        #   The goal is always to have the variables (pixels in an image,
        #     energy channels in a spectrum) always as columns in a 2D array.
        #     The rows are made up of observations.  For example, in 
        #     images, the rows are individual cells.  In SIs, the rows
        #     are pixels where spectra were gathered.
        # for images, the cell idx is dim 0
        data = self.get_cell_set().reshape((data.shape[0], -1))
        # for spectra, the energy index is dim 0.
        #data = spectrum_data.reshape((-1, data.shape[0]
        diffdata=data.copy()
        deriv_kernel=np.array([-1,0,0,0,0,0,1])
        for i in xrange(data.shape[1]):
            diffdata[:,i]=np.convolve(data[:,i],deriv_kernel)[3:-3]
        return diffdata

    #TODO: modify this to take advantage of PyTables queries
    def get_peak_data(self, chars=[], indices = []):
        """
        Get peak data from the table of peak data.
        
        Input:
        chars - a list of characteristic names (as string letters).
            For example, ['dx', 'dy', 'h'] selects x and y deviation from 
            average peak position and the peak height.
            
            Possible options include:
            x - the x position of a peak in a cell
            y - the y position of a peak in a cell
            dx - the difference between the x position of the peak in this cell
                 and the x position of the same peak in the average cell
            dy - the difference between the y position of the peak in this cell
                 and the y position of the same peak in the average cell
            h - the height of the peak
            o - if a peak is not perfectly symmetric, the orientation of the peak.
            e - the eccentricity of a peak.  i.e. how egg-shaped is it?
            
        indices - peak indices (integers) to select from.  Use this if you want to compare
            only a few peaks in the cell structure to compare.
            None selects all peaks.
        """
        if len(chars) > 0:
            if len(indices) is 0:
                indices = range( self.chest.root.cell_peaks.number_of_peaks)
            # the columns we get are the combination of the chars with the 
            #   indices we want.
            cols = [['%s%i' % (c, i) for i in indices] for c in chars]
        else:
            chars = ['x', 'y', 'dx', 'dy', 'h', 'o', 'e']
            if len(indices) is 0:
                indices = range( self.chest.root.cell_peaks.number_of_peaks)
            # the columns we get are the combination of the chars with the 
            #   indices we want.            
            cols = [['%s%i' % (c, i) for c in chars] for i in indices]
        # make the cols a simple list, rather than a list of lists
        cols = [item for sublist in cols for item in sublist]
        # get the data from the table
        peak_data = self.chest.root.cell_peaks[:]
        # return an ndarray with only the selected columns
        return np.array(peak_data[cols]).view(float).reshape(len(cols),-1)

    def PCA(self, n_components, whiten = False):
        factors, scores = mda.PCA(self.get_MDA_data())
        # stash the results under the group of MDA results
        #   attribs:
        #   - analysis type
        #   - number of components
        #   - whitening applied
        # store the mean of each column - we use this for reconstruction later
        
        
    def ICA(self, n_components, whiten = True, max_iter = 10):
        factors, scores = mda.ICA(self.get_MDA_data())
        # integration undoes the differentiation done in the ICA data prep.
        factors = np.array([integrate.cumtrapz(factors[:,i]) for i in xrange(factors.shape[1])]).T
        # we need to reshape the factors and scores to make sense.
        # for images, the factors are themselves images, while the scores are line plots.
        
        # for SIs, the factors are spectra, while the scores are images.
        
        return factors, scores
    
    def plot_images(self):
        main_window = None
        self.set_active_data('rawdata')
        self.spyglass()


    def plot_cells(self):
        main_window = None
        self.set_active_data('cells')
        #
        self.spyglass()


        
