# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import tables

filters = tables.Filters(complib='blosc', complevel=8)

class MdaResultsTable(tables.IsDescription):
    idx = tables.Int64Col(pos=0)
    # the MDA type and the date it was run - an identifier for each run.
    # XXX_YYYY-MM-DD HH:MM
    context = tables.StringCol(24)
    # type of MDA
    mda_type = tables.StringCol(10)
    # description of where data came from (as a path in the file, for example:
    # '/root/rawdata'
    input_data = tables.StringCol(250)
    # was data filtered or reconstructed?
    treatments = tables.StringCol(250)

class ImageDataTable(tables.IsDescription):
    idx = tables.Int64Col(pos=0)
    # metadata = tables.
    # attributes - tags
    # name of a file
    filename = tables.StringCol(250)
    # treatments - any prior processing (for example, reconstruction)
    treatments = tables.StringCol(250)


class CellsTable(tables.IsDescription):
    file_idx = tables.Int64Col(pos=0)
    # description of where data came from (as a path in the file, for example:
    # '/root/rawdata'
    input_data = tables.StringCol(250)
    # filename that the data is from
    filename = tables.StringCol(250, pos=1)
    # the upper left coordinate of the parent image where this
    # cell was cropped from.
    x_coordinate = tables.Float32Col(pos=3)
    y_coordinate = tables.Float32Col(pos=4)
    omit = tables.BoolCol()


class SpectrumDataTable(tables.IsDescription):
    idx = tables.Int64Col(pos=0)
    # name of a file
    filename = tables.StringCol(250)
    # treatments - any prior processing (for example, reconstruction)
    treatments = tables.StringCol(250)


def get_image_h5file(filename):
    # split off any extension in the filename - we add our own.
    h5file = tables.openFile('%s.chest' % filename, 'w')

    # data outline keeps records of what data are available - the linkage
    # between which cells came from which images, locations, etc.
    h5file.createTable('/', 'image_description', ImageDataTable)

    h5file.createTable('/', 'cell_description', CellsTable)

    h5file.createTable('/', 'mda_description', MdaResultsTable)
    #cell_peak_table = h5file.createTable('/', 'cell_peaks',
    #                                     CellsTable)
    # image group has data files as CArrays.  There is one array for each file,
    # accessed by the filename.
    h5file.createGroup('/', 'rawdata')

    # cell group has cell stacks as CArrays - one for each file from which
    #    cells came
    # cell group also has template used for cropping
    h5file.createGroup('/', 'cells')

    # mda cell results has factors/score images for cell data.  These are
    #  nested:
    #   - MDA type
    #     - which image they (the cells) originated from
    #       - Factors
    #       - Scores
    #       - anything else of interest
    
    # note that image MDA really only makes sense to do on a single image.  This is
    # related to Masashi Watanabe's MSA plugin, marketed by HREM Research, which
    # provides a facility for doing SVD on an image.
    
    # If you want to do it on more than one image, do either one at a time, or do
    # cell cropping.
    
    # image MDA results group.  Nested:
    #   - MDA type
    #     - which image they (the cells) originated from
    #       - Factors
    #       - Scores
    h5file.createGroup('/', 'mda_results')

    h5file.flush()

    return h5file


def get_spectrum_h5file(filename):
    # split off any extension in the filename - we add our own.
    h5file = tables.openFile('%s.chest'%filename,'w')
    data_outline = h5file.createTable('/', 'image_description', 
                                     SpectrumDataTable)
    imgGroup = h5file.createGroup('/', 'rawdata')
    # image MDA results group
    mdaGroup = h5file.createGroup('/', 'mda_results')

    h5file.flush()

    
