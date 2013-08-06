# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys

import numpy as np
from scipy.signal import medfilt
from gaussfitter import gaussfit
#from fit_gaussian import fitgaussian

from pyface.api import ProgressDialog

def get_characteristics(moments):
    try:
        import cv
    except:
        try:
            import cv2.cv as cv
        except:
            print 'Module %s:' % sys.modules[__name__]
            print 'OpenCV is not available, the peak characterization functions will not work.'
            return None
    mu00 = cv.GetCentralMoment(moments,0,0)
    mu01 = cv.GetCentralMoment(moments,0,1)
    mu10 = cv.GetCentralMoment(moments,1,0)
    mu11 = cv.GetCentralMoment(moments,1,1)
    mu02 = cv.GetCentralMoment(moments,0,2)
    mu20 = cv.GetCentralMoment(moments,2,0)
    mu03 = cv.GetCentralMoment(moments,0,3)
    mu30 = cv.GetCentralMoment(moments,3,0) 
    
    xxVar = mu20/mu00
    yyVar = mu02/mu00
    
    xCenter = mu10/mu00
    yCenter = mu01/mu00
    
    xyCenter=mu11/mu00
    
    axis_first_term = 0.5*(xxVar + yyVar)
    axis_second_term = 0.5*np.sqrt(4*(xyCenter)**2+(xxVar-yyVar)**2)
    # the lengths of the two principle components
    long_axis = axis_first_term + axis_second_term
    short_axis = abs(axis_first_term - axis_second_term)
    # how round the peak is.  0 means perfectly round; 1 means it's a line, not a circle.
    eccentricity = np.sqrt(abs(1.0-short_axis/long_axis))
    # how much the peak is rotated.  0 means the long axis points upward. 
    #    45 degrees looks like a backslash.
    orientation = 0.5*np.arctan2((2.0*mu11),(mu20-mu02))*180/np.pi
    xSkew = mu30 / (mu00 * (xxVar**(3.0/2)))
    ySkew = mu03 / (mu00 * (yyVar**(3.0/2)))
    # 0 is a placeholder for the height.
    return np.array([xCenter, yCenter, 0, long_axis, short_axis, orientation, eccentricity, xSkew, ySkew])

def estimate_peak_width(image, window_size=64, window_center=None, medfilt=5):
    # put the window in the image center
    if window_center is None:
        # center the window around the tallest peak in the image
        # find the highest point in the image.
        k = np.argmax(image)
        cx,cy = np.unravel_index(k, image.shape)
        #cx = (image.shape[1])/2
        #cy = (image.shape[0])/2
        
    else:
        # let the user define the window center
        cx,cy = window_center
    
    # cut out a smaller sub-region    
    x = np.arange(cx-window_size/2, cx+window_size/2)
    y = np.arange(cy-window_size/2, cy+window_size/2)
    xv,yv = np.meshgrid(x,y)
    image_tmp = image[yv,xv]
    
    # Pick out the row around that highest point.  Make sure datatype
    #    is signed so we can have negative numbers
    tmp_row = np.array(image_tmp[int(window_size/2)],dtype=np.integer)
    # convert it to float
    # make lowest point zero
    tmp_row -= np.min(tmp_row)
    # subtract the half of the maximum height 
    #     (This makes our measurement Full Width eigth Max).
    #     It is better to get a slightly too large neighborhood!
    tmp_row -= (np.max(tmp_row))/8
    # Detect where we cross 0
    zero_crossings = np.where(np.diff(np.sign(tmp_row)))[0]
    # reuse the cx variable to represent the middle of our sub-window.
    cx=window_size/2
    # find the zero crossing closest to the left of the peak.
    # First, chuck any values to the right of our peak.
    peak_left_crossings = zero_crossings[zero_crossings<cx]
    # the left value is the greatest of those.
    left = peak_left_crossings[-1]
    peak_right_crossings = zero_crossings[zero_crossings>cx]
    right = peak_right_crossings[0]
    return int(right-left)
    

# Code tweaked from the example by Alejandro at:
# http://stackoverflow.com/questions/16842823/peak-detection-in-a-noisy-2d-array
# main tweak is the pre-allocation of the results, which should speed 
#    things up quite a lot for large numbers of peaks.
def two_dim_findpeaks(image, peak_width=None, sigma=None, alpha=1, medfilt_radius=3, max_peak_number=10000):
    """
    
    """
    from copy import deepcopy
    import numpy.ma as ma
    # do a 2D median filter
    if medfilt_radius > 0:
        image = medfilt(image,medfilt_radius)    
    if peak_width is None:
        peak_width = estimate_peak_width(image)
    coords = np.zeros((max_peak_number,2))
    image_temp = deepcopy(image)
    peak_ct=0
    size=peak_width/2
    if sigma is None:
        # peaks are some number of standard deviations from mean
        #sigma=np.std(image)
        # peaks are some set fraction of the max peak height
        sigma = np.min(image)+0.2*(np.max(image)-np.min(image))
    while True:
        k = np.argmax(image_temp)
        j,i = np.unravel_index(k, image_temp.shape)
        if(image_temp[j,i] >= alpha*sigma):
            # store the coordinate
            coords[peak_ct]=[j,i]
            # set the neighborhood of the peak to zero so we go look elsewhere
            #  for other peaks
            x = np.arange(i-size, i+size)
            y = np.arange(j-size, j+size)
            xv,yv = np.meshgrid(x,y)
            image_temp[yv.clip(0,image_temp.shape[0]-1),
                                   xv.clip(0,image_temp.shape[1]-1) ] = 0
            peak_ct+=1
        else:
            break
    
    coords = coords[:peak_ct]
    # add in the heights
    heights=np.array([image[coords[i,0],coords[i,1]] for i in xrange(coords.shape[0])]).reshape((-1,1))
    sigma = np.std(heights)
    mean = np.mean(heights)
    # filter out junk peaks - anything beyond 5 sigma.
    heights = ma.masked_outside(heights, mean-(5*sigma), mean+(5*sigma))
    coords=np.hstack((coords,heights))
    return ma.compress_rows(coords)
    

def peak_attribs_image(image, peak_width=None, target_locations=None, medfilt_radius=5):
    """
    Characterizes the peaks in an image.

        Parameters:
        ----------

        peak_width : int (optional)
                expected peak width.  Affects characteristic fitting window.
                Too big, and you'll include other peaks in the measurement.  
                Too small, and you'll get spurious peaks around your peaks.
                Default is None (attempts to auto-detect)

        target_locations : numpy array (n x 2)
                array of n target locations.  If left as None, will create 
                target locations by locating peaks on the average image of the stack.
                default is None (peaks detected from average image)

        medfilt_radius : int (optional)
                median filter window to apply to smooth the data
                (see scipy.signal.medfilt)
                if 0, no filter will be applied.
                default is set to 5

        Returns:
        -------

        2D numpy array:
        - One row per peak
        - 7 columns:
          0,1 - location
          2 - height
          3,4 - long and short axis length
          5 - orientation
          6 - eccentricity
          7,8 - skew

    """
    try:
        import cv
    except:
        try:
            import cv2.cv as cv
        except:
            print 'Module %s:' % sys.modules[__name__]
            print 'OpenCV is not available, the peak characterization functions will not work.'
            return None
    if medfilt_radius:
        image=medfilt(image,medfilt_radius)
    if peak_width is None:
        peak_width = estimate_peak_width(image)
        print "Estimated peak width as %d pixels"%peak_width
    if target_locations is None:
        target_locations=two_dim_findpeaks(image, peak_width=peak_width, medfilt_radius=5)
    rlt=np.zeros((target_locations.shape[0],9))
    r=np.ceil(peak_width/2)
    imsize=image.shape[0]
    roi=np.zeros((r*2,r*2))
    
    # TODO: this should be abstracted to use whatever graphical 
    #       or command-line environment we're in.
    progress = ProgressDialog(title="Peak characterization progress", 
                              message="Characterizing %d peaks on current image"%target_locations.shape[0], 
                              max=int(target_locations.shape[0]), show_time=True, can_cancel=False)
    progress.open()

    for loc in xrange(target_locations.shape[0]):
        progress.update(int(loc+1))
        c=target_locations[loc]
        bxmin=c[1]-r
        bymin=c[0]-r
        bxmax=c[1]+r
        bymax=c[0]+r
        if bxmin<0: bxmin=0; bxmax=peak_width
        if bymin<0: bymin=0; bymax=peak_width
        if bxmax>imsize: bxmax=imsize; bxmin=imsize-peak_width
        if bymax>imsize: bymax=imsize; bymin=imsize-peak_width
        roi[:,:]=image[bymin:bymax,bxmin:bxmax]
        # skip frames with significant dead pixels (corners of
        #    rotated images, perhaps
        if np.average(roi)< 0.5*np.average(image):
            rlt[loc,:2] = (c[1], c[0])
            continue
        ms=cv.Moments(cv.fromarray(roi))
        # output from get_characteristics is:
        # x, y, height, long_axis, short_axis, orientation, eccentricity, skew_x, skew_y
        rlt[loc] = get_characteristics(ms)
        
        dummy, amp, x, y, width_x, width_y, rot = gaussfit(roi)
        # we are looking at global peak locations - why are we adjusting for bymin/bymax?
        rlt[loc,:2] = (np.array([bymin,bxmin]) + np.array([y,x]))
        #rlt[loc,:2] = np.array([y,x])
        # insert the height
        rlt[loc,2]=amp
        # TODO: compare this with OpenCV moment calculation above:
        #  (this is using the gaussfitter value)
        rlt[loc,5]=rot
    return rlt

def stack_coords(stack, peak_width, maxpeakn=5000):
    """
    A rough location of all peaks in the image stack.  This can be fed into the
    best_match function with a list of specific peak locations to find the best
    matching peak location in each image.
    """
    depth=stack.shape[0]
    coords=np.ones((maxpeakn,2,depth))*10000
    for i in xrange(depth):
        ctmp=two_dim_findpeaks(stack[i,:,:], peak_width=peak_width)
        for row in xrange(ctmp.shape[0]):
            coords[row,:,i]=ctmp[row,:2]
    return coords
    
def best_match(arr, target, neighborhood=None):
    """
    Attempts to find the best match (least distance) for target coordinates 
    in array of coordinates arr.
    
    target is a 1D array of 2 coordinates.
    arr is a 2D array of (npeaks)x2 coordinates.
    
    Usage:
    best_match(arr, target)
    """
    arr_sub = arr[:]
    arr_sub = arr - target
    if neighborhood:
        # mask any peaks outside the neighborhood
        arr_sub = np.ma.masked_outside(arr_sub, -neighborhood, neighborhood)
        # set the masked pixel values to 10000, so that they won't be the nearest peak.
        arr_sub = np.ma.filled(arr_sub, 10000)
    # locate the peak with the smallest euclidean distance to the target
    match=np.argmin(np.sqrt(np.sum(
        np.power(arr_sub,2),
        axis=1)))
    rlt=arr[match]
    # TODO: this neighborhood warning doesn't work well.
    #if neighborhood and np.sum(rlt)>2*neighborhood:
    #    print "Warning! Didn't find a peak within your neighborhood! Watch for fishy peaks."
    return rlt

def normalize(arr,lower=0.0,upper=1.0):
    if lower>upper: lower,upper=upper,lower
    arr -= arr.min()
    arr *= (upper-lower)/arr.max()
    arr += lower
    return arr

# code from
# http://stackoverflow.com/questions/8647024/how-to-apply-a-disc-shaped-mask-to-a-numpy-array
def draw_mask(array_size, radius, target_locations):
    array = np.zeros(array_size)
    for loc in target_locations:
        ay, ax = array_size[0], array_size[1]
        ty, tx = loc[0], loc[1]
        y,x = np.mgrid[-ty:ay-ty, -tx:ax-tx]
        mask = x*x + y*y <= radius*radius
        array[mask] = 1
    return array

def min_peak_distance(target_locations):
    """
    This function is meant to estimate the smallest distance between peaks.
    It is used in turn (in Cell.py) to estimate the peak size for cell 
    characterization.
    """
    minimum = 3000
    xx, yy = np.meshgrid(range(len(target_locations)), 
                range(len(target_locations)))
    for i in range(len(target_locations)):
        for j in range(len(target_locations)):
            ix = target_locations[i][1]
            jx = target_locations[j][1]
            iy = target_locations[i][0]
            jy = target_locations[j][0]
            distance = np.sqrt((ix-jx)**2 + (iy-jy)**2)
            if distance == 0: continue
            if distance < minimum: minimum = distance
    return minimum
    
"""
# OpenCV does not derive 4th order moments.  
# Stuck at skew until rewrite of moment derivation?
def kurtosis(moments):
    mu00 = cv.GetCentralMoment(moments,0,0)

    xxVar = 
    yyVar = 
    xKurt = m40 / (m00 * Math.pow(xxVar,2.0)) - 3.0;
    yKurt = m04 / (m00 * Math.pow(yyVar,2.0)) - 3.0;
"""


