# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from traits.api import HasTraits, Bool, Instance, String

from MappableImage import MappableImageController
from Cell import CellController
from CellCrop import CellCropController
from MDA_view import MDAViewController
from MDA_execute import MDAExecutionController

from analyzarr.lib.cv import peak_char as pc
from analyzarr.lib.io import file_import
from analyzarr.testing.test_pattern import get_test_pattern
from analyzarr.Release import version

from scipy.misc import imsave
import numpy as np

from time import time

import enaml
with enaml.imports():
    from analyzarr.ui.ucc import CellCropperInterface
    from analyzarr.ui.MDA_popup import MDAInterface
from enaml.application import Application
from enaml.stdlib.sessions import simple_session

import os
 
# the UI controller
class HighSeasAdventure(HasTraits):
    has_chest = Bool(False)
    show_image_view = Bool(False)
    show_cell_view = Bool(False)
    show_score_view = Bool(False)
    show_factor_view = Bool(False)
    title = String("")

    image_controller = Instance(MappableImageController)
    cell_controller = Instance(CellController)
    mda_controller = Instance(MDAViewController)
    
    def __init__(self, *args, **kw):
        super(HighSeasAdventure, self).__init__(*args, **kw)
        self.image_controller = MappableImageController(parent=self)
        self.cell_controller = CellController(parent=self)
        self.mda_controller = MDAViewController(parent=self)
        self.chest = None

    def update_cell_data(self):
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=self.chest)
        
    def add_cell_data(self, data, name):
        self.cell_controller.add_cell_data(data,name)

    def update_mda_data(self):
        self.mda_controller = MDAViewController(parent=self, 
                                              treasure_chest=self.chest)
        self.show_factor_view = True
        self.show_score_view = True
        
    def update_image_data(self):
        self.image_controller.data_updated()
        self.crop_controller.data_updated()

    def new_treasure_chest(self, filename):
        if self.chest is not None:
            self.chest.close()
        # first, clear any existing controllers
        self.image_controller = MappableImageController(parent=self)
        self.cell_controller = CellController(parent=self)
        self.mda_controller = MDAViewController(parent=self)
        # open a new chest
        prefix, ext = os.path.splitext(filename)
        if "chest" in ext:
            filename = prefix
        chest = file_import.new_treasure_chest(filename)
        self.chest = chest
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=chest)
        self.title = " - %s" % os.path.split(filename)[1]
        self.has_chest=True

    def open_treasure_chest(self, filename):
        if self.chest is not None:
            self.chest.close()
        chest = file_import.open_treasure_chest(filename)
        self.chest = chest
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=chest)
        self.mda_controller = MDAViewController(parent=self, treasure_chest=chest)
        self.title = " - %s" % os.path.split(filename)[1]
        self.has_chest=True

    def import_files(self, file_list):
        file_import.import_files(self.chest, file_list)
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=self.chest)
        self.cell_controller = CellController(parent=self,
                                              treasure_chest=self.chest)
        self.log_action(action="import", files=file_list)

    def load_test_data(self):
        # create the test pattern
        tp = get_test_pattern((256,256))
        # save it as a file, for user's reference, and because we have
        #    to load files into chests (TODO: fix this to be more generic?)
        imsave('tp.png', tp)
        # create a new project
        self.new_treasure_chest('test_pattern')
        # import the newly saved test pattern file
        self.import_files(['tp.png'])
        # delete the file for cleanliness?

    def characterize_peaks(self):
        has_cells = self.cell_controller._can_change_idx
        # TODO: need to make peak width a user-specified value, or some
        #   auto-detect algorithm...
        self.image_controller.characterize_peaks()
        if has_cells:
            # TODO: cell_controller accesses the database for 
            #  the image controller here.  Need to clean up.
            self.map_global_peaks_to_cells()

    def open_crop_UI(self):
        crop_controller = CellCropController(parent=self,
                                                  treasure_chest=self.chest)
        cell_cropper = simple_session('cropper', 'Cell cropper', CellCropperInterface, 
                                      controller=crop_controller)
        Application.instance().add_factories([cell_cropper])
        session_id = Application.instance().start_session('cropper')
        crop_controller._session_id = session_id
        
    def open_MDA_UI(self):
        mda_controller = MDAExecutionController(parent=self, 
                                             treasure_chest=self.chest)
        mda_dialog = simple_session('mda', 'MDA dialog', MDAInterface, 
                                      controller=mda_controller)
        Application.instance().add_factories([mda_dialog])
        session_id = Application.instance().start_session('mda')
        mda_controller._session_id = session_id
        
    def log_action(self, action, **parameters):
        """
        action - a short string describing the action itself (e.g. crop cells)
        parameters - pass any number of named parameters.  These will be recorded as
            a string that can then be recovered as a dictionary at some later date.
        version - the version of analyzarr used to perform that action
        """
        row = self.chest.root.log.row
        row['date']=time()
        row['action']=action
        # record parameter dictionary as string.  Can be brought back with:
        #   dict2 = eval(string_from_table)
        # http://stackoverflow.com/questions/4547274/convert-a-python-dict-to-a-string-and-back
        row['parameters'] = parameters
        row['version'] = version
        row.append()
        self.chest.root.log.flush()

    def get_peak_data(self, node_name):
        indices = self.chest.get_node('/image_peaks').get_where_list(
                    '(filename=="%s")'%node_name)
        return self.chest.root.image_peaks[indices]

    def find_best_matching_global_peaks(self, target_locations_x_y, node_name):
        coords_x=self.image_controller.get_expression_data("x", "/image_peaks", node_name)
        coords_y=self.image_controller.get_expression_data("y", "/image_peaks", node_name)
        coords = np.vstack((coords_x, coords_y)).T
        indices=[pc.best_match(coords, target) for target in target_locations_x_y]
        return self.get_peak_data(node_name=node_name)[indices]

    def map_global_peaks_to_cells(self):        
        try:
            # wipe out old results
            self.chest.remove_node('/cell_peaks')        
        except:
            # any errors will be because the table doesn't exist. That's OK.
            pass                
        # get the average cell image and find peaks on it
        peaks=pc.two_dim_findpeaks(self.cell_controller.get_average_cell())
        # generate a list of column names
        names = [('x%i, y%i, dx%i, dy%i, h%i, o%i, e%i, sx%i, sy%i' % ((x,)*9)).split(', ') 
                 for x in xrange(peaks.shape[0])]
        # flatten that from a list of lists to a simple list
        names = [item for sublist in names for item in sublist]
        # make tuples of each column name and 'f8' for the data type
        dtypes = zip(names, ['f8', ] * peaks.shape[0]*9)
        # prepend the filename and index columns
        dtypes = [('filename', '|S250'), ('file_idx', 'i4'), ('omit', 'bool')] + dtypes
        # create an empty recarray with our data type
        desc = np.recarray((0,), dtype=dtypes)
        # create the table using the empty description recarray
        self.chest.create_table(self.chest.root,
                               'cell_peaks', description=desc)
        
        self.chest.set_node_attr('/cell_peaks','number_of_peaks', peaks.shape[0])
        self.chest.flush()
        
        global_peak_chars = np.zeros((self.cell_controller.get_num_files()),dtype=dtypes)
        
        # loop over each peak, finding the peak that best matches this cell's position
        #     plus the offset for the peak.
        for node in self.image_controller.get_node_iterator():
            cell_data = self.cell_controller.get_cell_set(node.name)
            data = np.zeros((cell_data.shape[0]),dtype=dtypes)
            data["filename"] = node.name
            data['file_idx'] = np.arange(cell_data.shape[0])
            for idx, peak in enumerate(peaks):            
                #TODO: need to rework this whole get_expression_data concept.  It is
                #    a column accessor.
                target_x = self.image_controller.get_expression_data("x_coordinate", 
                                                    table_loc="/cell_description",
                                                    filename=node.name)+peak[0]
                target_y = self.image_controller.get_expression_data("y_coordinate", 
                                                    table_loc="/cell_description",
                                                    filename=node.name)+peak[1]
                if target_x.shape[0]>0:
                    chars = self.find_best_matching_global_peaks(np.array([target_x,target_y]).T, 
                                                                 node.name)
                    # add the peak ids (or data) to table representing cell peak characteristics
                    
                    
                    data["x%i"%idx] = chars["x"]-target_x+peak[0]
                    data["y%i"%idx] = chars["y"]-target_y+peak[1]
                    data["dx%i"%idx] = chars["x"]-target_x
                    data["dy%i"%idx] = chars["y"]-target_y
                    data["h%i"%idx] = chars["h"]
                    data["o%i"%idx] = chars["o"]
                    data["e%i"%idx] = chars["e"]
                    data["sx%i"%idx] = chars["sx"]
                    data["sy%i"%idx] = chars["sy"]
                
            
            # commit the data to the table
            self.chest.root.cell_peaks.append(data)
            self.chest.root.cell_peaks.flush()
        self.chest.flush()
            
        