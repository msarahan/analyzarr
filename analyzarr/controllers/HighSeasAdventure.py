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
from traits.api import on_trait_change
from data_structure import filters
import tables as tb
import numpy as np
from lib.mda import mda_sklearn as mda

import cv_funcs
import peak_char as pc

from controllers.MappableImage import MappableImageController
from controllers.Cell import CellController
from controllers.CellCrop import CellCropController

from ui.renderers import HasRenderer
import file_import
import data_structure

from enaml.application import Application
 
# the UI controller
class HighSeasAdventure(t.HasTraits):
    show_image_view = t.Bool(False)
    show_cell_view = t.Bool(False)
    show_score_view = t.Bool(False)
    show_factor_view = t.Bool(False)

    image_controller = t.Instance(MappableImageController)
    cell_controller = t.Instance(CellController)
    crop_controller = t.Instance(CellCropController)

    # TODO: need method for opening files

    def __init__(self, *args, **kw):
        super(HighSeasAdventure, self).__init__(*args, **kw)
        self.image_controller = MappableImageController(parent=self)
        self.cell_controller = CellController(parent=self)
        self.crop_controller = CellCropController(parent=self)
        self.chest = None

    def update_cell_data(self):
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=self.chest)
        
    def update_image_data(self):
        self.image_controller.data_updated()
        self.crop_controller.data_updated()

    def new_treasure_chest(self, filename):
        chest = file_import.new_treasure_chest(filename)
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=chest)
        self.crop_controller = CellCropController(parent=self, 
                                                  treasure_chest=chest)
        self.chest = chest        

    def open_treasure_chest(self, filename):
        if self.chest is not None:
            self.chest.close()
        chest = file_import.open_treasure_chest(filename)
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=chest)
        self.cell_controller = CellController(parent=self, 
                                              treasure_chest=chest)
        self.crop_controller = CellCropController(parent=self, 
                                                  treasure_chest=chest)
        self.chest = chest

    def import_files(self, file_list):
        file_import.import_files(self.chest, file_list)
        self.image_controller = MappableImageController(parent=self, 
                                                    treasure_chest=self.chest)
        self.cell_controller = CellController(parent=self,
                                              treasure_chest=self.chest)
        self.crop_controller = CellCropController(parent=self,
                                                  treasure_chest=self.chest)

