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

# try to use the faster Cython version.  If it's not available, fall back to the python definition below (~5x slower)
try:
    from one_dim_findpeaks import one_dim_findpeaks
except:
    def one_dim_findpeaks(y, x=None, slope_thresh=0.5, amp_thresh=None,
                                medfilt_radius=5, maxpeakn=30000, peakgroup=10, subchannel=True,
                                peak_array=None):
        """
        Find peaks along a 1D line.
        
        Function to locate the positive peaks in a noisy x-y data set.

        Detects peaks by looking for downward zero-crossings in the first
        derivative that exceed 'slope_thresh'.
    
        Returns an array containing position, height, and width of each peak.
    
        'slope_thresh' and 'amp_thresh', control sensitivity: higher values will
        neglect smaller features.
    
        Parameters
        ---------
        y : array
            1D input array, e.g. a spectrum
    
        x : array (optional)
            1D array describing the calibration of y (must have same shape as y)
    
        slope_thresh : float (optional)
            1st derivative threshold to count the peak
            default is set to 0.5
            higher values will neglect smaller features.
    
        amp_thresh : float (optional)
            intensity threshold above which   
            default is set to 10% of max(y)
            higher values will neglect smaller features.
    
        medfilt_radius : int (optional)
            median filter window to apply to smooth the data
            (see scipy.signal.medfilt)
            if 0, no filter will be applied.
            default is set to 5
    
        peakgroup : int (optional)
            number of points around the "top part" of the peak
            default is set to 10
    
        maxpeakn : int (optional)
            number of maximum detectable peaks
            default is set to 30000
    
        subchannel : bool (optional)
            default is set to True
    
        peak_array : array of shape (n, 3) (optional)
            A pre-allocated numpy array to fill with peaks.  Saves memory,
            especially when using the 2D peakfinder.
    
        Returns
        -------
        P : array of shape (npeaks, 3)
            contains position, height, and width of each peak
    
        """
        # Changelog
        # T. C. O'Haver, 1995.  Version 2  Last revised Oct 27, 2006
        # Converted to Python by Michael Sarahan, Feb 2011.
        # Revised to handle edges better.  MCS, Mar 2011
        if x is None:
            x = np.arange(len(y),dtype=np.int64)
        if not amp_thresh:
            amp_thresh = 0.1 * y.max()
        d = np.gradient(y)
        if peak_array is None:
            # allocate a result array for 'maxpeakn' peaks
            P = np.zeros(y.shape[0])
            H = np.zeros(y.shape[0])
        else:
            maxpeakn=peak_array.shape[0]
            P=peak_array
        peak = 0
        for j in xrange(len(y) - 4):
            if np.sign(d[j]) > np.sign(d[j+1]): # Detects zero-crossing
                if np.sign(d[j+1]) == 0: continue
                # if slope of derivative is larger than slope_thresh
                if d[j] - d[j+1] > slope_thresh:
                    # if height of peak is larger than amp_thresh
                    if y[j] > amp_thresh:  
                        location = x[j]	
                        height = y[j]
                        # no way to know peak width without
                        # the above measurements.
                        if (location > 0 and not np.isnan(location)
                            and location < x[-1]):
                            P[peak] = location
                            H[peak] = height
                            peak = peak + 1
        # return only the part of the array that contains peaks
        # (not the whole maxpeakn x 3 array)
        return P[:peak], H[:peak]

def two_dim_findpeaks(arr,peak_width=10, medfilt_radius=5,
                      maxpeakn=10000):
    """
    Locate peaks on a 2-D image.  Basic idea is to locate peaks in X direction,
    then in Y direction, and see where they overlay.

    Code based on Dan Masiel's matlab functions

    Parameters
    ---------
    arr : array
    2D input array, e.g. an image

    medfilt_radius : int (optional)
                     median filter window to apply to smooth the data
                     (see scipy.signal.medfilt)
                     if 0, no filter will be applied.
                     default is set to 5

    peak_width : int (optional)
                expected peak width.  Too big, and you'll include other peaks.
                default is set to 10

    Returns
    -------
    P : array of shape (npeaks, 3)
        contains position and height of each peak
    """
    #
    mapX=np.zeros_like(arr)
    mapY=np.zeros_like(arr)

    # do a 2D median filter, not a 1D.
    if medfilt_radius > 0:
        arr = medfilt(arr,medfilt_radius)
    xc = [(one_dim_findpeaks(arr[i].astype(np.float64)))[0] for i in xrange(arr.shape[0])]
    for row in xrange(len(xc)):
        for col in xrange(xc[row].shape[0]):
            mapX[row,int(xc[row][col])]=1
    yc = [(one_dim_findpeaks(arr[:,i].astype(np.float64)))[0] for i in xrange(arr.shape[1])]
    for col in xrange(len(yc)):
        for row in xrange(yc[col].shape[0]):
            mapY[int(yc[col][row]),col]=1
    # Dan's comment from Matlab code, left in for curiosity:
    #% wow! lame!
    Fmap = mapX*mapY
    nonzeros=np.nonzero(Fmap)
    coords=np.vstack((nonzeros[1],nonzeros[0])).T
    coords=np.ma.fix_invalid(coords,fill_value=-1)
    coords=np.ma.masked_outside(coords,peak_width/2+1,arr.shape[0]-peak_width/2-1)
    coords=np.ma.masked_less(coords,0)
    coords=np.ma.compress_rows(coords)
    # push them down and to the right to account for zero-based indexing
    coords+=1
    # add in the heights
    heights=np.array([arr[coords[i,1],coords[i,0]] for i in xrange(coords.shape[0])]).reshape((-1,1))
    coords=np.hstack((coords,heights))
    return coords 

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
    orientation = 0.5*np.arctan2((2.0*mu11),(mu20-mu02))*180/np.pi;
    eccentricity = ((mu20-mu02)**2+4*mu11**2)/mu00
    xSkew = mu30 / (mu00 * (xxVar**(3.0/2)))
    ySkew = mu03 / (mu00 * (yyVar**(3.0/2)))
    # 0 is a placeholder for the height.
    return np.array([xCenter, yCenter, 0, orientation, eccentricity, xSkew, ySkew])

def peak_attribs_image(image, peak_width, target_locations=None, medfilt_radius=5):
    """
    Characterizes the peaks in an image.

        Parameters:
        ----------

        peak_width : int (required)
                expected peak width.  Affects characteristic fitting window.
                Too big, and you'll include other peaks in the measurement

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
        - 5 columns:
          0,1 - location
          2 - height
          3 - orientation
          4 - eccentricity

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
    if target_locations is None:
        target_locations=two_dim_findpeaks(image, peak_width=peak_width)
    rlt=np.zeros((target_locations.shape[0],7))
    r=peak_width/2
    imsize=image.shape[0]
    roi=np.zeros((peak_width,peak_width))
    for loc in xrange(target_locations.shape[0]):
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
        ms=cv.Moments(cv.fromarray(roi))
        height=image[c[1],c[0]]
        rlt[loc] = get_characteristics(ms)
        rlt[loc,:2] += target_locations[loc]
        rlt[loc,2]=height
    return rlt

def stack_coords(stack,peak_width,maxpeakn=5000):
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


