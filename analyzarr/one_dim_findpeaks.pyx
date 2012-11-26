# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import cython

import numpy as np
cimport numpy as np

# the data type used for our indices
ctypedef long long INT_t
ctypedef double FLOAT_t

# for our sign computations:
cdef inline int sign(double a): return 1 if a >= 0 else -1

def say_hello_to(name):
    print("Hello %s!" % name)

@cython.boundscheck(False)
def one_dim_findpeaks(np.ndarray[FLOAT_t, ndim=1] y, float slope_thresh=0.5, float amp_thresh=-1):
#def one_dim_findpeaks(np.ndarray y, float slope_thresh=0.5, float amp_thresh=None):
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

    if amp_thresh < 0:
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