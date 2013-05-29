#!/usr/bin/env python
## Copyright (C) 2011 by Michael Sarahan

## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:

## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
## THE SOFTWARE.

import rpy2.robjects as ro
from rpy2.robjects.packages import importr
import numpy as np
import sys
import rpy2.robjects.numpy2ri #automatically converts numpy arrays to R types
from scipy.stats import poisson,norm
from scipy import integrate

# TODO: put in rpy version and R version (and, ideally, version of any plugin used.)
name="mda_rpy_"#+ sklearn.__version__

getmethod = ro.baseenv.get("getMethod")
StrVector = ro.StrVector

def pca(data,weight=True):
    if weight:
        # Weighting described in detail in Keenan and Kotula,
        # Surface Interface Analysis, 2004.
        aG=np.sqrt(np.sum(data,axis=1)/data.shape[1])
        bH=np.sqrt(np.sum(data,axis=0)/data.shape[0])
        aG[aG==0]=0.000000000001  # bad hack to avoid division by 0.
        bH[bH==0]=0.000000000001  # Sets all zero elements to 1E-12
        # This newaxis stuff is some numpy voodoo to avoid creating the huge
        # diagonal matrices for this matrix multiplication.  More info here:
        # http://www.mail-archive.com/numpy-discussion@scipy.org/msg02063.html
        data=(((1/aG)[:,np.newaxis])*data)*(1/bH)
        #data=bH[:,np.newaxis]*(np.dot(data,np.diag(aG,0)))
    res=ro.r.prcomp(data,retx=True,center=False)
    factors=np.array(res.rx2("rotation"))
    scores=np.array(res.rx2("x"))
    eigenvalues=np.array(res.rx2("sdev"))
    if weight:
        factors=bH[:,np.newaxis]*factors
        scores=aG[:,np.newaxis]*scores
    return factors,scores,eigenvalues

def gauss(val,mu,sigmasq):
    res=1/(np.sqrt(2*np.pi*sigmasq))*np.exp(-(val-mu)**2/(2*sigmasq))
    return res

def likelihood(vals,q,func='gauss'):
    #vals=(vals-np.min(vals))/np.max(vals-np.min(vals))
    muleft=np.average(vals[:q])
    muright=np.average(vals[q:])
    if func is 'gauss':
        varl=np.var(vals[:q])
        varr=np.var(vals[q:])
        p=len(vals)
        sigmasq=((q-1)*varl**2+(p-q-1)*varr**2)/(p-2)
        lhs=np.sum(np.array([gauss(val,muleft,sigmasq) for val in vals[:q]]))
        rhs=np.sum(np.array([gauss(val,muright,sigmasq) for val in vals[q:]]))
        #lhs=np.sum(np.array([norm.pdf(val,muleft,sigmasq) for val in vals[:q]]))
        #rhs=np.sum(np.array([norm.pdf(val,muleft,sigmasq) for val in vals[q:]]))
    elif func is 'poiss':
        lhs=np.sum(np.array([poisson.pmf(val,muright) for val in vals[q:]]))
        rhs=np.sum(np.array([poisson.pmf(val,muright) for val in vals[:q]]))
    return np.log10(lhs)+np.log10(rhs)

def screeML(vals,retls=False):
    """
    Maximum likelihood eigenvalue profile estimation.  Tries to tell you how
    many factors you need to accurately represent your data.

    For more details, see Zhu and Ghodsi
    """
    ls=np.array([likelihood(vals,q) for q in xrange(2,len(vals)-1)])
    if retls:
        return ls
    else:
        return np.argmax(ls)+1

def reconstruct(factors,scores,nFactors=None):
    """
    Reconstruct your data from a limited set of factors.

    Can be used one of three ways:
    - nFactors is None or not passed to the function (default).  This
      reconstructs using all available factors.
    - nFactors is an integer less than the total number of factors.  This
      reconstructs using the first nFactors factors.  NOTE: this only makes
      sense for MSA methods that give you factors sorted by eigenvalue or
      some similar measure of information content.
    - nFactors is a list of factors.  This reconstructs using only the listed
      factors.

    """
    if type(nFactors).__name__ is 'list':
      tfactors=np.zeros((factors.shape[0],len(nFactors)))
      tscores=np.zeros((len(nFactors),scores.shape[1]))
      for i in xrange(len(nFactors)):
        tfactors[:,i]=factors[:,nFactors[i]]
        tscores[i,:]=scores[nFactors[i],:]
      return np.dot(tfactors,tscores)
    elif not nFactors:
      return np.dot(factors,scores)
    else:
      return np.dot(factors[:,:nFactors],scores[:nFactors,:])

def linfit(vals,end,windowsize=10):
    """
    Fits lines along your eigenvalue plot.  Computes the std dev for each line,
    and tries to find the point at which the std deviations start increasing.
    Ideally, this indicates the lowest eigenvalue index which contains 
    important information.

    This function progresses from the end of the data set to the beginning.
    The end parameter indicates the number of points from the end to skip.  This
    is necessary because the eigenvalue plot often drops suddenly near its end.
    """
    slopes=[np.polyfit(np.arange(windowsize),vals[i-windowsize:i],1)[0] for i in np.arange(end,end-10,-1)]
    avg=[np.average(slopes)]
    stdev=[np.std(slopes)]
    i=end-10
    while i>windowsize:
        slopes.append(np.polyfit(np.arange(windowsize),vals[i-windowsize:i],1)[0])
        avg.append(np.average(slopes))
        stdev.append(np.std(slopes))
        i=i-1
    return np.argmin(np.array(stdev))+windowsize

def lstsq_project(factors,data):
    prj_data=np.zeros((factors.shape[1],data.shape[1]))
    for col in xrange(data.shape[1]):
        prj=np.linalg.lstsq(factors,data[:,col])
        prj_data[:,col]=prj[0]
    return prj_data

def bpca(data,nFactors):
    """
    Bayesian PCA, not orthogonal.  Slow.
    """
    ro.r.library('pcaMethods')
    res=ro.r.bpca(data,nPcs=nFactors)
    factors=res.do_slot('scores')
    scores=res.do_slot('loadings')
    return np.asarray(factors),np.asarray(scores)    

def ica(data,nFactors,sort=True):
    ro.r.library('fastICA')
    res = ro.r.fastICA(data,nFactors,method='C')
    factors=np.array(res.rx2("S"))
    scores=np.array(res.rx2("A"))
    if sort:
        factors,scores=icasort(factors,scores)
    return factors,scores

def diff_ica(data,nFactors,sort=True):
    """
    Numerically differentiates your data using a digital impulse response filter.
    You should differentiate your data prior to running ICA on it.
    See Bonnet and Nuzillard, Ultramicroscopy, 2004
    """
    diffdata=data.copy()
    deriv_kernel=np.array([-1,0,0,0,0,0,1])
    for i in xrange(data.shape[1]):
        diffdata[:,i]=np.convolve(data[:,i],deriv_kernel)[3:-3]
    factors,scores=ica(diffdata,nvecs)
    factors=np.array([integrate.cumtrapz(factors[:,i]) for i in xrange(factors.shape[1])]).T
    return factors, scores

def icasort(factors,scores):
    sums=[[ct,np.sum(np.abs(factors[:,ct]))] for ct in xrange(factors.shape[1])]
    sums.sort(lambda x,y: cmp(x[1],y[1]),reverse=True)
    sfactors=factors.copy()
    sscores=scores.copy()
    for i in xrange(factors.shape[1]):
        sfactors[:,i]=factors[:,sums[i][0]]
        sscores[i]=scores[sums[i][0]]
    return sfactors,sscores

def nmf(data,nFactors,nruns=50,ncpus=8):
    ro.r.library('NMF')
    ro.r('''
        donmf <- function(data, nFactors=%i,nrun=%i,ncpus=%i) {
            nmf(data,nFactors,'snmf/l',nrun=nrun,.opt='v',.pbackend=ncpus)
        }
        '''%(nFactors,nruns,ncpus))
    donmf = ro.globalenv['donmf']
    res = donmf(data,nFactors,nrun=nruns)
    factors=np.array(ro.r.basis(res))
    scores=np.array(ro.r.coef(res))
    return factors,scores

def OrthoRotation(data,method='varimax'):
    ro.r.library('GPArotation')
    data=data.T  # You have to have more observations (columns) than variables
    # (rows).  If you use a row-centric rotation method, then this transpose
    # should be OK...
    orthoMethods=['targetT','pstT','entropy','quartimax','varimax','bentlerT','tandemI','tandemII','geominT','infomaxT','mccammon']
    if not method in orthoMethods:
        print 'Method %s is not intended for orthogonal application, or not implemented.  Valid methods are: '%method
        print orthoMethods
        sys.exit()
    res=ro.r.GPForth(data,method=method)
    factors=res.rx2("loadings")
    scores=res.rx2("Th")
    return np.asarray(factors).T,np.asarray(scores).T
    
def ObliqueRotation(data,method='oblimin'):
    ro.r.library('GPArotation')
    obliqueMethods=['oblimin','quartimin','targetQ','pstQ','oblimax','simplimax','bentlerQ','geominQ','cfQ','infomaxQ']
    if not method in obliqueMethods:
        print 'Method %s is not intended for oblique application, or not implemented.  Valid methods are: '%method
        print obliqueMethods
        sys.exit()
    
    res=ro.r.GPFoblq(data,method=method,normalize=True)
    factors=res.rx2("loadings")
    scores=res.rx2("Th")
    covariance=res.rx2("Phi")
    return np.asarray(factors).T,np.asarray(scores).T,np.asarray(covariance).T
    
if __name__=='__main__':
    #ro.r.data('smoke',package='ca')
    ro.r.data('Harman',package='GPArotation')
    testdata=np.asarray(ro.r.Harman8)
    smokedata=np.asarray(ro.r['smoke'],dtype=np.float64)
    pcavec,pcaval=pca(testdata)
    print pcaval.shape
    # print ca(smokedata) # infinite or missing values in SVD
    print bpca(testdata,2)
    print ica(testdata,2)
    print OrthoRotation(testdata)
    print ObliqueRotation(testdata)
