# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from sklearn import decomposition

def PCA(data, n_components=None, whiten=False):
    estimator = decomposition.PCA(n_components = n_components, 
                                            whiten = whiten)
    estimator.fit(data)
    factors = estimator.components_
    scores = estimator.transform(data)
    return factors, scores, estimator.explained_variance_ratio_

def ICA(data, n_components, whiten = False, max_iter = 10):
    estimator = decomposition.FastICA(n_components = n_components, 
                                            whiten = whiten, 
                                            max_iter = max_iter)
    estimator.fit(data)
    factors = est.transform(data)
    scores = estimator.get_mixing_matrix()
    return factors, scores

def NMF(data, n_components, beta = 5.0, tol = 5e-3, sparseness = 'components'):
    estimator = decomposition.NMF(n_components = n_components, beta = beta,
                                  tol = tol, sparseness = sparseness)
    estimator.fit(data)
    scores = est.fit_transform(data)
    return factors, scores
    
