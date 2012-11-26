# -*- coding: utf-8 -*-

import tables as tb
import os

from data_structure import get_image_h5file, get_spectrum_h5file

img_extensions = ['.png', '.bmp', '.dib', '.gif', '.jpeg', '.jpe', '.jpg', '.msp', '.pcx', '.ppm', ".pbm", ".pgm", '.xbm', '.spi',]

tiff_extensions = ['.tiff', '.tif',]

dm_extensions = ['.dm3',]

# I don't give a rat's ass about FEI's MRC files or other spectral formats.  
# Sorry.

def open_treasure_chest(filename):
    h5file = tb.openFile(filename, 'a')
    return h5file

def import_files(file_string, output_filename = None):

    # match supported file input types - check extension
    if '*' in file_string:
        from glob import glob
        flist=glob(file_string)
        flist.sort()
    else:
        flist = [file_string]

    if os.path.splitext(flist[0])[1] in img_extensions:
        h5file = import_images(flist, output_filename)
    elif os.path.splitext(flist[0])[1] in tiff_extensions:
        h5file = import_tiff(flist, output_filename)
    elif os.path.splitext(flist[0])[1] in dm_extensions:
        h5file = import_dm(flist, output_filename)
    else:
        h5file = None
    h5file.flush()
    return h5file

#TODO: add ways to add/remove member data

def import_image(flist, output_filename=None):
    from scipy.misc import imread
    filters = tb.Filters(complib='blosc', complevel=8)
    if output_filename is None:
        output_filename = "image_treasure_%s" % ""    
    h5file = get_image_h5file(output_filename)
    data_record = h5file.root.data_outline.row
    # any kind of jpg, png can be lumped together
    for f in flist:
        # get data as numpy array
        d = imread(f)
        # add a CArray for this data in the h5file
        ds = h5file.createCArray(h5file.root.rawdata, 
                            os.path.splitext(f)[0], 
                            tb.Atom.from_dtype(d.dtype),
                            d.shape,
                            filters=filters
                            )
        # assigns the data to the array
        ds[:] = d
        # add the record for this image to the table in the h5file
        data_record['filename'] = os.path.splitext(f)[0]
        data_record['idx'] = flist.index(f)
        data_record.append()
    return h5file
        

def import_tiff(flist, output_filename=None):
    # for tiff, we use Christoph Gohlke's reader
    from lib.io.tifffile import imread
    if output_filename is None:
        output_filename = "image_treasure_%s" % ""    
    h5file = get_image_h5file(output_filename)
    filters = tb.Filters(complib='blosc', complevel=8)
    data_record = h5file.root.data_outline.row
    # any kind of jpg, png can be lumped together
    for f in flist:
        # get data as numpy array
        d = imread(f)
        # add a CArray for this data in the h5file
        ds = h5file.createCArray(h5file.root.rawdata, 
                            os.path.splitext(f)[0], 
                            tb.Atom.from_dtype(d.dtype),
                            d.shape,
                            filters=filters
                            )
        # assigns the data to the array
        ds[:] = d

        # add the record for this image to the table in the h5file
        data_record['filename'] = os.path.splitext(f)[0]
        data_record['idx'] = flist.index(f)
        data_record.append()
    return h5file
        

# DM3 files
def import_dm(flist, output_filename=None):
    filters = tb.Filters(complib='blosc', complevel=8)
    from lib.io.digital_micrograph import file_reader
    tmp_dm3, tmp_tags = file_reader(flist[0])
    
    if tmp_dm3.record_by is 'spectrum':
        if output_filename is None:
            output_filename = "spectrum_treasure_%s" % ""
        h5file = get_spectrum_h5file(output_filename)
    elif tmp_dm3.record_by is 'image':
        if output_filename is None:
            output_filename = "image_treasure_%s" % ""
        h5file = get_image_h5file(output_filename)
    
    data_record = h5file.root.data_outline.row
    for f in flist:
        print "loading file: %s" %f
        # this is a little wasteful (re-reading the first file), 
        # but I'm vain and want to save a line or two of code.
        tmp_dm3, tmp_tags = file_reader(f)
        # add a CArray for this data in the h5file
        ds = h5file.createCArray(h5file.root.rawdata, 
                            os.path.splitext(tmp_dm3.name)[0], 
                            tb.Atom.from_dtype(tmp_dm3.data.dtype),
                            tmp_dm3.data.shape,
                            filters=filters
                            )
        # assigns the data to the array
        ds[:] = tmp_dm3.data

        # TODO: add the tags as metadata for the CArray
        
        # add the record for this image to the table in the h5file
        data_record['filename'] = os.path.splitext(tmp_dm3.name)[0]
        data_record['idx'] = flist.index(f)
        data_record.append()

    # flush the data to commit our changes to the file.
    return h5file
