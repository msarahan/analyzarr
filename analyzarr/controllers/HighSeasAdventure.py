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

from analyzarr.lib.io import file_import
from analyzarr.testing.test_pattern import get_test_pattern
from analyzarr.Release import version

from scipy.misc import imsave

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
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=chest)
        self.chest = chest
        self.title = " - %s" % os.path.split(filename)[1]

    def open_treasure_chest(self, filename):
        if self.chest is not None:
            self.chest.close()
        chest = file_import.open_treasure_chest(filename)
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=chest)
        self.mda_controller = MDAViewController(parent=self, treasure_chest=chest)
        self.chest = chest
        self.title = " - %s" % os.path.split(filename)[1]

    def import_files(self, file_list):
        file_import.import_files(self.chest, file_list)
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=self.chest)
        self.cell_controller = CellController(parent=self,
                                              treasure_chest=self.chest)
        self.log_action(action="import", files=file_list)

    def load_test_data(self):
        # create the test pattern
        tp = get_test_pattern()
        # save it as a file, for user's reference, and because we have
        #    to load files into chests (TODO: fix this to be more generic?)
        imsave('tp.png', tp)
        # create a new project
        self.new_treasure_chest('test_pattern')
        # import the newly saved test pattern file
        self.import_files(['tp.png'])
        # delete the file for cleanliness?

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
