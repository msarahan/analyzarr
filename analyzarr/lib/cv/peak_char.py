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

import numpy.ma as ma
#from fit_gaussian import fitgaussian

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
    m=moments
    # these are all central moments!
    mu00 = cv.GetCentralMoment(m,0,0)
    mu11 = cv.GetCentralMoment(moments,1,1)
    mu02 = cv.GetCentralMoment(moments,0,2)
    mu20 = cv.GetCentralMoment(moments,2,0)
    mu03 = cv.GetCentralMoment(moments,0,3)
    mu30 = cv.GetCentralMoment(moments,3,0) 
    
    if mu00 == 0:
        return np.array([0, 0, 0, 0, 0, 0, 0, 0, 0])
    
    xxVar = mu20/mu00
    yyVar = mu02/mu00

    # these use raw moments!
    xCenter = m.m10/m.m00
    yCenter = m.m01/m.m00
    
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

def gaussian(height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x,y: height*np.exp(
                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)

def estimate_peak_width(image, window_size=64, window_center=None, medfilt=5, max_peak_width=100):
    from scipy.ndimage import gaussian_filter
    from copy import deepcopy
    if window_center is None:
        tmp_image = deepcopy(image)
        # apply a quick mask so that we don't end up on the edges.
        mask = np.ones((image.shape[0],image.shape[1]))
        mask[0:window_size/2]=0
        mask[-window_size/2:]=0
        mask[:,0:window_size/2]=0
        mask[:,-window_size/2:]=0
        tmp_image *= mask
        # center the window around the tallest peak in the image
        # find the highest point in the image.
        k = np.argmax(tmp_image)
        cx,cy = np.unravel_index(k, image.shape)
        #cx = (image.shape[1])/2
        #cy = (image.shape[0])/2
        
    else:
        # let the user define the window center
        cx,cy = window_center
        tmp_image=image
    
    # cut out a smaller sub-region    
    x = np.arange(cx-window_size/2, cx+window_size/2)
    y = np.arange(cy-window_size/2, cy+window_size/2)
    xv,yv = np.meshgrid(x,y)
    
    tmp_image = image[xv.clip(0,image.shape[0]-1),
                          yv.clip(0,image.shape[1]-1) ]    
        
    
    # Pick out the row around that highest point.  Make sure datatype
    #    is signed so we can have negative numbers
    tmp_row = np.array(tmp_image[int(window_size/2)],dtype=np.integer)
    # blur it just to make damn sure we don't have some kind 
    #     of crappy derivative.
    tmp_row=gaussian_filter(tmp_row,5)
    
    # Detect where our derivative switches sign
    zero_crossings = np.where(np.diff(np.sign(np.diff(tmp_row))))[0]
    
    # chuck zeros
    tmp_row = ma.masked_values(tmp_row,0)#.compressed()
    # convert it to float
    # make lowest point zero
    tmp_row -= np.min(tmp_row)
    # subtract the quarter of the maximum height 
    #     (This makes our measurement Full Width quarter Max).
    #     It is better to get a slightly too large neighborhood!
    tmp_row -= (np.max(tmp_row))/10
    
    # Detect where we cross zero
    zero_crossings=np.append(zero_crossings,np.where(np.diff(np.sign(tmp_row)))[0])
    # We use the values from either of those that are closest to
    zero_crossings=np.sort(zero_crossings)
    
    
    # reuse the cx variable to represent the middle of our sub-window.
    # they're 0-based indexes, so adjust for that...
    cx=window_size/2-1
    if len(zero_crossings)<2 or min(zero_crossings)>cx or max(zero_crossings)<cx:
            return 0    
    # find the zero crossing closest to the left of the peak.
    # First, chuck any values to the right of our peak.
    peak_left_crossings = zero_crossings[zero_crossings<cx-1]
    # the rightmost value is the greatest of those.
    left = peak_left_crossings[-1]
    # First, chuck any values to the left of our peak.
    peak_right_crossings = zero_crossings[zero_crossings>cx+1]
    #  The leftmost value is the closest one.
    right = peak_right_crossings[0]
    # tends to underestimate.  Tweak it.  7 is "empirically derived"
    #  fudge_factor = 7
    width = int(right-left)#+fudge_factor
    # black out our current ROI if it has led us astray
    if width>max_peak_width:
        return 0
    #if width>max_peak_width and width>5:
        #image[yv.clip(0,image.shape[0]-1),
              #xv.clip(0,image.shape[1]-1) ]=0
        #print "width estimation recursing."
        # recurse to (hopefully) a better peak.
        #width = estimate_peak_width(image, window_size=window_size, max_peak_width=max_peak_width)
    #if width<5:
        #return 0
    return width
    
# code from
# http://stackoverflow.com/questions/8647024/how-to-apply-a-disc-shaped-mask-to-a-numpy-array
def draw_mask(array_size, radius, target_locations):
    array = np.zeros((int(array_size[0]),int(array_size[1])))
    for loc in target_locations:
        ay, ax = array_size[0], array_size[1]
        ty, tx = loc[0], loc[1]
        y,x = np.mgrid[-ty:ay-ty, -tx:ax-tx]
        mask = x*x + y*y <= radius*radius
        array[mask] = 1
    return array


def two_dim_findpeaks(image, peak_width=None, medfilt_radius=3, max_peak_width=100):
        """
        Takes an image and detect the peaks using the local maximum filter.
        Returns a boolean mask of the peaks (i.e. 1 when
        the pixel's value is the neighborhood maximum, 0 otherwise)
        
        Code by Ivan:
        http://stackoverflow.com/questions/3684484/peak-detection-in-a-2d-array
        
        Returns a 2D numpy array with one row per peak, two columns (X index first)
        """
        
        from scipy.ndimage.filters import maximum_filter
        from scipy.ndimage.morphology import generate_binary_structure, binary_erosion, \
             iterate_structure
        
        from analyzarr.lib.cv.cv_funcs import xcorr

        if medfilt_radius is not None:
            image = medfilt(image, medfilt_radius)

        if peak_width is None:
            peak_width=estimate_peak_width(image,medfilt=medfilt_radius, 
                                           max_peak_width=max_peak_width)
            
        # the normal gaussian
        xg, yg = np.mgrid[0:peak_width, 0:peak_width]
        templateImage = gaussian(255, (peak_width/2)+1, (peak_width/2)+1, (peak_width/4)+1, 
                        peak_width/4+1)(xg, yg)
            
        cleaned_image = xcorr(templateImage, image)
        #medfilt(image, medfilt_radius)
        #peak_width=estimate_peak_width(cleaned_image,medfilt=None, 
        #                               max_peak_width=max_peak_width)        
            
        # define an 8-connected neighborhood
        neighborhood = generate_binary_structure(2,1)
        neighborhood = iterate_structure(neighborhood, int(peak_width/4))
    
        #apply the local maximum filter; all pixel of maximal value 
        #in their neighborhood are set to 1
        local_max = maximum_filter(cleaned_image, footprint=neighborhood)==cleaned_image
        #local_max = maximum_filter(image, size=(peak_width,peak_width))==image
        #local_max is a mask that contains the peaks we are 
        #looking for, but also the background.
        #In order to isolate the peaks we must remove the background from the mask.
    
        #we create the mask of the background
        background = (cleaned_image==0)
    
        #a little technicality: we must erode the background in order to 
        #successfully subtract it form local_max, otherwise a line will 
        #appear along the background border (artifact of the local maximum filter)
        eroded_background = binary_erosion(background, structure=neighborhood, border_value=1)
    
        #we obtain the final mask, containing only peaks, 
        #by removing the background from the local_max mask
        detected_peaks = local_max - eroded_background
        
        # convert the mask to indices:
        detected_peaks = detected_peaks.nonzero()
        
        # format the two arrays into one
        detected_peaks = np.vstack((detected_peaks[1],detected_peaks[0])).T
        
        detected_peaks=kill_duplicates(detected_peaks)
        detected_peaks=kill_edges(image, detected_peaks, peak_width/2)
    
        return detected_peaks+peak_width/2

def kill_duplicates(arr, minimum_distance=10):
    """
    Attempts to eliminate garbage coordinates
    
    arr is a 2D array of (npeaks)x4 coordinates.
        0:1 is the x and y coordinates.
        2 is the peak height
        3 is the peak width
    """
    import scipy
    from scipy.spatial import KDTree
    tree = KDTree(arr)
    
    match_list = tree.query_ball_tree(tree,minimum_distance)
    match_list=[list_item for list_item in match_list if len(list_item)>1]
    
    chuck_list=[]
    
    for match in match_list:
        # compile the heights from the table
        #heights=arr[match][:,2]
        #best=np.argmax(heights)
        match.remove(match[0])
        chuck_list += match
        
    keepers = range(arr.shape[0])
    [keepers.remove(chuck) for chuck in chuck_list if chuck in keepers]
    return arr[keepers]
    
def kill_edges(image, peaks, peak_width):
    upper_bound_width=image.shape[0]-peak_width
    upper_bound_height=image.shape[1]-peak_width
    lower_bound=peak_width
    mask = np.ma.greater(peaks,lower_bound)
    masked_peaks=np.ma.masked_where(peaks<lower_bound,peaks)
    masked_peaks[:,0]=np.ma.masked_where(masked_peaks[:,0]>upper_bound_width,masked_peaks[:,0])
    masked_peaks[:,1]=np.ma.masked_where(masked_peaks[:,1]>upper_bound_height,masked_peaks[:,1])
    return np.ma.compress_rows(masked_peaks)

def peak_attribs_image(image, peak_width=None, target_locations=None, medfilt_radius=3,
                       progress_object=None):
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
    if target_locations is None:
        # target locations should be a list of arrays.  Each element in the 
        #    list corresponds to a recursion level in peak finding.  The peak 
        #    width can change with each recursion.
        target_locations=two_dim_findpeaks(image, peak_width=peak_width, medfilt_radius=medfilt_radius)
    imsize=image.shape[0]
    
    total_peaks = target_locations.shape[0]
    rlt=np.zeros((total_peaks,9))
    
    if progress_object is not None:
        progress_object.initialize("Characterizing peaks", total_peaks)
    
    rlt_offset=0
    
    if peak_width is None:
        peak_width=estimate_peak_width(image)

    r=int(np.ceil(peak_width/2))
    roi=np.zeros((r*2,r*2))
    mask = draw_mask((r*2,r*2), r, [(r,r)])
    for c in target_locations:
        peak_left=int(c[0]-r)
        peak_top=int(c[1]-r)
        peak_right=int(c[0]+r)
        peak_bottom=int(c[1]+r)
        #if bxmin<0: bxmin=0; bxmax=peak_width
        #if bymin<0: bymin=0; bymax=peak_width
        #if bxmax>imsize: bxmax=imsize; bxmin=imsize-peak_width
        #if bymax>imsize: bymax=imsize; bymin=imsize-peak_width            
        # skip peaks that are too close to edges.
        if (peak_right)>image.shape[1]+r/4 or (peak_bottom)>image.shape[0]+r/4:
            if progress_object is not None:
                progress_object.increment()
            continue
        # set the neighborhood of the peak to zero so we go look elsewhere
                    #  for other peaks            
        x = np.array(np.arange(peak_left, peak_right),dtype=np.integer)
        y = np.array(np.arange(peak_top, peak_bottom),dtype=np.integer)
        xv,yv = np.meshgrid(x,y)
        roi[:,:] = image[yv.clip(0,image.shape[0]-1),
                         xv.clip(0,image.shape[1]-1)] * mask
        #roi[0:,:]=image[bymin:bymax,bxmin:bxmax]
        # skip frames with significant dead pixels (corners of
        #    rotated images, perhaps
        #if np.average(roi)< 0.5*np.average(image):
        #rlt[loc,:2] = (c[1], c[0])
        #continue
        ms=cv.Moments(cv.fromarray(roi))
        # output from get_characteristics is:
        # x, y, height, long_axis, short_axis, orientation, eccentricity, skew_x, skew_y
        rlt[rlt_offset] = get_characteristics(ms)
        
        # order for these is:
        # amp, xShift, yShift, xWidth, height, yWidth, Rotation
        #  WTF???  Why is this different from return order!?
        # I'm a control freak...
        limit_min = [True, True, True, True, True, True, True]
        limit_max = [True, True, True, True, True, True, True]
        
        # 30 pixels seems like a hell of a lot for a peak...
        max_width=30
        max_height = 1.2*np.max(roi)
        ctr = np.array(roi.shape)/2
        min_height = np.mean(image)/1.5
        
        x = rlt[rlt_offset][0]
        y = rlt[rlt_offset][1]
        amp = image[int(peak_top+y),int(peak_left+x)]
        long_axis = rlt[rlt_offset][3]
        short_axis = rlt[rlt_offset][4] 
        orientation = rlt[rlt_offset][5]
        height = 0
        params = [amp, x, y, long_axis, height, short_axis, orientation]
        
        minpars = [min_height, x-2, y-2, 0, 0, 0, 0]
        maxpars = [max_height, x+2, y+2, max_width, 0, max_width, 360]
        
        # TODO: could use existing moments or parameters to speed up...
        
        amp, fit_x, fit_y, width_x, height, width_y, rot = gaussfit(roi,
                                    limitedmin=limit_min, 
                                    limitedmax=limit_max,
                                    maxpars=maxpars,
                                    minpars=minpars,
                                    params=params
                                    )
        # x and y are the locations within the ROI.  Add the coordinates of 
        #    the top-left corner of our ROI on the global image.
        rlt[rlt_offset,:2] = (np.array([peak_top,peak_left]) + np.array([fit_y,fit_x]))
        #rlt[loc,:2] = np.array([y,x])
        # insert the height
        rlt[rlt_offset,2]=amp+height
        # TODO: compare this with OpenCV moment calculation above:
        #  (this is using the gaussfitter value)
        rlt[rlt_offset,5]=rot
        rlt_offset+=1
        if progress_object is not None:
            progress_object.increment()
    # chuck outliers based on median of height
    d = np.abs(rlt[:,2] - np.median(rlt[:,2]))
    mdev = np.median(d)
    s = d/mdev if mdev else 0
    # kill outliers based on height
    rlt=rlt[np.logical_and(s<10, rlt[:,2]<image.max()*1.3)]
    # kill peaks that are too close to other peaks
    # the minimum width is 1.5 times the smallest peak width.
    #min_width = 1.5*target_locations[-1][0][3]
    #rlt = kill_duplicates(rlt,min_width)
    return rlt

def flatten_peak_list(peak_list):
    total_peaks=0
    peak_offset=0
    for arr in peak_list:
        total_peaks+=arr.shape[0]
    rlt=np.zeros((total_peaks,4))
    for arr in peak_list:
        rlt[peak_offset:peak_offset+arr.shape[0]]=arr
        peak_offset+=arr.shape[0]
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

