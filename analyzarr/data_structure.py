

import tables

class MdaResults(tables.IsDescription):
    idx = tables.Int64Col(pos=0)
    # type of MDA
    mda_type = tables.StringCol(10)
    # description of where data came from
    input_data = tables.StringCol(250)
    # was data filtered or reconstructed?
    treatments = tables.StringCol(250)

class PeakData(tables.IsDescription):
    idx = tables.Int64Col(pos=0)
    x = tables.Float32Col(pos=1)
    y = tables.Float32Col(pos=2)
    height = tables.Float32Col(pos=3)
    orientation = tables.Float32Col(pos=4)
    eccentricity = tables.Float32Col(pos=5)
    # which file did it come from?  This might be a cell or a parent image.
    input_data = tables.StringCol(250)
    # treatments - any prior processing (for example, reconstruction)    
    treatments = tables.StringCol(250)

    # Higher order moments - third: shift from center?
    # how to introduce Chebyshev polynomials?

class OriginalImageData(tables.IsDescription):
    idx = tables.Int64Col(pos=0)
    # metadata = tables.
    # attributes - tags
    # name of a file
    filename = tables.StringCol(250)    
    # treatments - any prior processing (for example, reconstruction)
    treatments = tables.StringCol(250)
    peaks = PeakData()
    mda_image_results = MdaResults()
    mda_peak_results = PeakData()
    class Cells(tables.IsDescription):
        idx = tables.Int64Col()
        # the image from which this cell was cropped
        parent = tables.StringCol(150)
        # the upper left coordinate of the parent image where this
        # cell was cropped from.
        x_coordinate = tables.Float32Col()
        y_coordinate = tables.Float32Col()
        # peaks here can be mapped back to the original image by 
        # some offset from the x and y coordinate.
        peaks = PeakData()
        peaks_avg = PeakData()
        # MDA results tables specifc to cell stacks
        mda_image_results = MdaResults()
        mda_peak_results = PeakData()

class OriginalSpectrumData(tables.IsDescription):
    idx = tables.Int64Col(pos=0)
    # name of a file
    filename = tables.StringCol(250)  

    # metadata = tables.
  
    # treatments - any prior processing (for example, reconstruction)
    treatments = tables.StringCol(250)

    # holds results from any number of MDA treatments
    mda_results = MdaResults()

def get_image_h5file(filename):
    # split off any extension in the filename - we add our own.
    h5file = tables.openFile('%s.h5'%filename,'w')
    # data outline keeps records of what data are available - the linkage 
    # between which cells came from which images, locations, etc.
    data_outline = h5file.createTable('/', 'data_outline', 
                                     OriginalImageData)
    # image group has data files as CArrays, peaks as Tables, image MDA 
    # results as CArrays, peak MDA results as Tables.  Can be multiple of each.
    imgGroup = h5file.createGroup('/', 'rawdata')

    # image MDA results group
    imgMdaGroup = h5file.createGroup(imgGroup, 'mda_image_results')

    # cell group has data files as CArrays, peaks as Tables, image MDA results 
    # as CArrays, peak MDA results as Tables.  Can be multiple of each.
    cellsGroup = h5file.createGroup(imgGroup, 'cells')

    cellsImgMdaGroup = h5file.createGroup(cellsGroup, 'mda_cells_results')
    
    h5file.flush()

    return h5file

def get_spectrum_h5file(filename):
    # split off any extension in the filename - we add our own.
    h5file = tables.openFile('%s.h5'%filename,'w')
    data_outline = h5file.createTable('/', 'data_outline', 
                                     OriginalSpectrumData)
    imgGroup = h5file.createGroup('/', 'rawdata')
    # image MDA results group
    mdaGroup = h5file.createGroup(imgGroup, 'mda_results')

    h5file.flush()

    
