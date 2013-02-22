# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

try:
  import cv
except:
  try:
    import cv2.cv as cv
  except:
    raise ImportError('OpenCV could not be imported')
  
import numpy as np

def cv2array(cv_im):
  depth2dtype = {
        cv.IPL_DEPTH_8U: 'uint8',
        cv.IPL_DEPTH_8S: 'int8',
        cv.IPL_DEPTH_16U: 'uint16',
        cv.IPL_DEPTH_16S: 'int16',
        cv.IPL_DEPTH_32S: 'int32',
        cv.IPL_DEPTH_32F: 'float32',
        cv.IPL_DEPTH_64F: 'float64',
    }
  
  arrdtype=cv_im.depth
  a = np.fromstring(
         cv_im.tostring(),
         dtype=depth2dtype[cv_im.depth],
         count=cv_im.width*cv_im.height*cv_im.nChannels)
  a.shape = (cv_im.height,cv_im.width,cv_im.nChannels)
  return a
    
def array2cv(a):
  dtype2depth = {
        'uint8':   cv.IPL_DEPTH_8U,
        'int8':    cv.IPL_DEPTH_8S,
        'uint16':  cv.IPL_DEPTH_16U,
        'int16':   cv.IPL_DEPTH_16S,
        'int32':   cv.IPL_DEPTH_32S,
        'float32': cv.IPL_DEPTH_32F,
        'float64': cv.IPL_DEPTH_64F,
    }
  try:
    nChannels = a.shape[2]
  except:
    nChannels = 1
  cv_im = cv.CreateImageHeader((a.shape[1],a.shape[0]), dtype2depth[str(a.dtype)], nChannels)
  cv.SetData(cv_im, a.tostring(),a.dtype.itemsize*nChannels*a.shape[1])
  return cv_im

def xcorr(templateImage,exptImage):
  #cloning is for memory alignment issue with numpy/openCV.
  if type(templateImage).__name__=='ndarray':
    # cast array to 8-bit, otherwise cross correlation fails.
    tmp = templateImage-float(np.min(templateImage))
    tmp = tmp/float(np.max(tmp))
    tmp = np.array(tmp*255,dtype=np.uint8)
    tmp = array2cv(tmp)
  if type(exptImage).__name__=='ndarray':
    expt = exptImage-float(np.min(exptImage))
    expt = expt/float(np.max(expt))
    expt = np.array(expt*255,dtype=np.uint8)
    expt = array2cv(expt)
  tmp=cv.CloneImage(tmp)
  padImage=cv.CloneImage(expt)
  resultWidth = padImage.width - tmp.width + 1
  resultHeight = padImage.height - tmp.height + 1
  result = cv.CreateImage((resultWidth,resultHeight),cv.IPL_DEPTH_32F,1)
  cv.MatchTemplate(padImage,tmp,result,cv.CV_TM_CCOEFF_NORMED)
  #cv.MatchTemplate(padImage,tmp,result,cv.CV_TM_CCORR)
  result=np.squeeze(cv2array(result))
  return result
