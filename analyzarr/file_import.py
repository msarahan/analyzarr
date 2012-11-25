# -*- coding: utf-8 -*-

import tables as tb
import os

from data_structure import get_image_h5file, get_spectrum_h5file

img_extensions = ['.png', '.bmp', '.dib', '.gif', '.jpeg', '.jpe', '.jpg', '.msp', '.pcx', '.ppm', ".pbm", ".pgm", '.xbm', '.spi',]

tiff_extensions = ['.tiff', '.tif',]

dm_extensions = ['.dm3',]

# I don't give a rat's ass about FEI's MRC files or other spectral formats.  
# Sorry.

def import_files(filename):

    # match supported file input types - check extension
    if '*' in filename:
        from glob import glob
        flist=glob(filename)
        flist.sort()
    else:
        flist = [filename]

    if os.path.splitext(flist[0])[1] in img_extensions:
        h5file = import_images(flist)
    elif os.path.splitext(flist[0])[1] in tiff_extensions:
        h5file = import_tiff(flist)
    elif os.path.splitext(flist[0])[1] in dm_extensions:
        h5file = import_dm(flist)
    else:
        h5file = None
    return h5file


def import_image(flist):
    from scipy.misc import imread
    filters = tb.Filters(complib='blosc', complevel=8)
    h5file = get_image_h5file("img")
    data_record = h5file.root.data_outline.row
    # any kind of jpg, png can be lumped together
    for f in flist:
        # get data as numpy array
        d = imread(f)
        # add a CArray for this data in the h5file
        ds = h5file.createCArray(h5file.root.rawdata, 
                            f, 
                            tb.Atom.from_dtype(d.dtype),
                            d.shape,
                            filters=filters
                            )
        # assigns the data to the array
        ds[:] = d
        # add the record for this image to the table in the h5file
        data_record['filename'] = f
        data_record['idx'] = flist.index(f)
        data_record.append()
    h5file.flush()
    return h5file
        

def import_tiff(flist):
    # for tiff, we use Christoph Gohlke's reader
    from lib.io.tifffile import imread
    h5file = get_image_h5file("image_treasure_chest_%s" % "")
    filters = tb.Filters(complib='blosc', complevel=8)
    data_record = h5file.root.data_outline.row
    # any kind of jpg, png can be lumped together
    for f in flist:
        # get data as numpy array
        d = imread(f)
        # add a CArray for this data in the h5file
        ds = h5file.createCArray(h5file.root.rawdata, 
                            f, 
                            tb.Atom.from_dtype(d.dtype),
                            d.shape,
                            filters=filters
                            )
        # assigns the data to the array
        ds[:] = d

        # add the record for this image to the table in the h5file
        data_record['filename'] = f
        data_record['idx'] = flist.index(f)
        data_record.append()
    h5file.flush()
    return h5file
        

# DM3 files
def import_dm(flist):
    filters = tb.Filters(complib='blosc', complevel=8)
    from lib.io.digital_micrograph import file_reader
    tmp_dm3, tmp_tags = file_reader(flist[0])
    if tmp_dm3.record_by is 'spectrum':
        h5file = get_spectrum_h5file("spectrum_treasure_chest_%s" % "")
    elif tmp_dm3.record_by is 'image':
        h5file = get_image_h5file("image_treasure_chest_%s" % "")
    
    data_record = h5file.root.data_outline.row
    for f in flist:
        print "loading file: %s" %f
        # this is a little wasteful (re-reading the first file), 
        # but I'm vain and want to save a line or two of code.
        tmp_dm3, tmp_tags = file_reader(f)
        # add a CArray for this data in the h5file
        ds = h5file.createCArray(h5file.root.rawdata, 
                            tmp_dm3.name, 
                            tb.Atom.from_dtype(tmp_dm3.data.dtype),
                            tmp_dm3.data.shape,
                            filters=filters
                            )
        # assigns the data to the array
        ds[:] = tmp_dm3.data

        # TODO: add the tags as metadata for the CArray
        
        # add the record for this image to the table in the h5file
        data_record['filename'] = tmp_dm3.name
        data_record['idx'] = flist.index(f)
        data_record.append()

    print
    # flush the data to commit our changes to the file.
    h5file.flush()

    return h5file
