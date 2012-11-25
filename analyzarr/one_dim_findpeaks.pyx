# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import numpy as np
cimport numpy as np
import cython

# the data type used for our indices
ctypedef np.int_t INT_t
ctypedef np.float_t FLOAT_t


# for our sign computations:
cdef inline int sign(double a): return 1 if a >= 0 else -1

@cython.boundscheck(False)
def one_dim_findpeaks(np.ndarray[FLOAT_t, ndim=1] y, float slope_thresh=0.5, float amp_thresh=None):
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

    slope_thresh : float (optional)
        1st derivative threshold to count the peak
        default is set to 0.5
        higher values will neglect smaller features.

    amp_thresh : float (optional)
        intensity threshold above which   
        default is set to 10% of max(y)
        higher values will neglect smaller features.

    Returns
    -------
    P : array of shape (npeaks)
        contains position (index) of each peak
    H : array of shape (npeaks)
        contains height (pixel value at index) of each peak

    """
    # Changelog
    # T. C. O'Haver, 1995.  Version 2  Last revised Oct 27, 2006
    # Converted to Python by Michael Sarahan, Feb 2011.
    # Revised to handle edges better.  MCS, Mar 2011
    # cythonized.  MCS, Nov 2012

    cdef int y_shape = y.shape[0]
    cdef int d_shape = y_shape-4
    cdef int peak_ct = 0

    cdef np.ndarray[INT_t, ndim = 1] P = np.zeros((y_shape), dtype = np.int64)
    cdef np.ndarray[FLOAT_t, ndim = 1] H = np.zeros((y.shape[0]), dtype = np.float64) # double-precision heights
    cdef np.ndarray[FLOAT_t, ndim = 1] d = np.gradient(y)

    if amp_thresh is None:
        amp_thresh = 0.1 * y.max()

    # cython function:
    # input data:
    #   - input array (y)
    #   - input derivative of array (d)
    #   - slope threshold
    #   - amplitude threshold

    # the index of the loop
    cdef int j, jplusone

    for j in range(d_shape):
        jplusone = j + 1
        if sign(d[j]) > sign(d[jplusone]): # Detects zero-crossing
            if sign(d[jplusone]) == 0: continue
            # if slope of derivative is larger than slope_thresh
            if d[j] - d[jplusone] > slope_thresh:
                # if height of peak is above threshold
                if y[j] > amp_thresh:  
                    # Fill results array P and H. One row for each peak 
                    # detected, containing the
                    # peak position (x-value) and peak height (y-value).
                    if (j > 0 and j < y_shape):
                        P[peak_ct] = j
                        H[peak_ct] = y[j]
                        peak_ct = peak_ct + 1
    # return only the part of the array that contains peaks
    return P[:peak_ct], H[:peak_ct]

def one_dim_findpeaks_naive(y, x=None, slope_thresh=0.5, amp_thresh=None,
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