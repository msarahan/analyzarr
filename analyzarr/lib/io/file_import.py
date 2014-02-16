# -*- coding: utf-8 -*-

import tables as tb
import os
import time

from data_structure import get_image_h5file, get_spectrum_h5file, filters

img_extensions = ['.png', '.bmp', '.dib', '.gif', '.jpeg', '.jpe', '.jpg', '.msp', '.pcx', '.ppm', ".pbm", ".pgm", '.xbm', '.spi',]

tiff_extensions = ['.tiff', '.tif',]

dm_extensions = ['.dm3',]


# I don't give a rat's ass about FEI's MRC files or other spectral formats.  
# Sorry.

def new_treasure_chest(filename):
    h5file = get_image_h5file(filename)
    return h5file

def open_treasure_chest(filename):
    h5file = tb.open_file(filename, 'a')
    return h5file

def import_files(h5file, file_string):
    # match supported file input types - check extension
    if '*' in file_string:
        from glob import glob
        flist = glob(file_string)
        flist.sort()
    elif isinstance(file_string, list):
        flist = file_string
    else:
        flist = [file_string]

    if os.path.splitext(flist[0])[1] in img_extensions:
        import_image(h5file, flist)
    elif os.path.splitext(flist[0])[1] in tiff_extensions:
        import_tiff(h5file, flist)
    elif os.path.splitext(flist[0])[1] in dm_extensions:
        import_dm(h5file, flist)
    h5file.flush()

#TODO: add ways to add/remove member data

def import_image(h5file, flist, output_filename=None):
    from scipy.misc import imread
    data_record = h5file.root.image_description.row
    # any kind of jpg, png can be lumped together
    for f in flist:
        filename = os.path.splitext(os.path.split(f)[1])[0]
        if len(h5file.root.image_description.get_where_list('filename=="%s"'%filename)) == 0:
            # get data as numpy array
            d = imread(f)
            # add a CArray for this data in the h5file
            ds = h5file.create_carray(h5file.root.rawdata, 
                            filename,
                            tb.Atom.from_dtype(d.dtype),
                            d.shape,
                            filters=filters
                            )
            # assigns the data to the array
            ds[:] = d
            # add the record for this image to the table in the h5file
            data_record['filename'] = filename
            data_record['idx'] = flist.index(f)
            data_record.append()
    h5file.root.image_description.flush()
    h5file.flush()

def import_tiff(h5file, flist):
    # for tiff, we use Christoph Gohlke's reader
    from analyzarr.lib.io.libs.tifffile import imread
    data_record = h5file.root.image_description.row
    # any kind of jpg, png can be lumped together
    for f in flist:
        filename = os.path.splitext(os.path.split(f)[1])[0]
        if len(h5file.root.image_description.get_where_list('filename=="%s"'%filename)) == 0:
            # get data as numpy array
            d = imread(f)
            # add a CArray for this data in the h5file
            ds = h5file.create_carray(h5file.root.rawdata, 
                            filename,
                            tb.Atom.from_dtype(d.dtype),
                            d.shape,
                            filters=filters
                            )
            # assigns the data to the array
            ds[:] = d

            # add the record for this image to the table in the h5file
            data_record['filename'] = filename
            data_record['idx'] = flist.index(f)
            data_record.append()
    h5file.root.image_description.flush()
    h5file.flush()

# DM3 files
def import_dm(h5file, flist):
    from analyzarr.lib.io.digital_micrograph import file_reader
    tmp_dm3, tmp_tags = file_reader(flist[0])
    
    data_record = h5file.root.image_description.row
    for f in flist:
        filename = os.path.splitext(os.path.split(f)[1])[0]
        if len(h5file.root.image_description.get_where_list('filename=="%s"'%filename)) == 0:
            print "loading file: %s" %f
            # this is a little wasteful (re-reading the first file), 
            # but I'm vain and want to save a line or two of code.
            tmp_dm3, tmp_tags = file_reader(f)
            # add a CArray for this data in the h5file
            ds = h5file.create_carray(h5file.root.rawdata, 
                            filename, 
                            tb.Atom.from_dtype(tmp_dm3.data.dtype),
                            tmp_dm3.data.shape,
                            filters=filters
                            )
            # assigns the data to the array
            ds[:] = tmp_dm3.data

            # TODO: add the tags as metadata for the CArray
            
            # add the record for this image to the table in the h5file
            data_record['filename'] = filename
            data_record['idx'] = flist.index(f)
            data_record.append()
    # flush the data to commit our changes to the file.
    h5file.root.image_description.flush()
    h5file.flush()
