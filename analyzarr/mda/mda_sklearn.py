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
    
def kmeans_cluster_stack(self, cells, clusters=None):
    import mdp
    if self._unfolded:
        self.fold()
    # if clusters not given, try to determine what it should be.
    if clusters is None:
        pass
    d=cells
    kmeans=mdp.nodes.KMeansClassifier(clusters)
    cluster_arrays=[]

    avg_stack=np.zeros((clusters,d.shape[1],d.shape[2]))
    kmeans.train(d.reshape((-1,d.shape[0])).T)
    kmeans.stop_training()
    groups=kmeans.label(d.reshape((-1,d.shape[0])).T)
    try:
        # test if location data is available
        self.mapped_parameters.locations[0]
    except:
        messages.warning("No cell location information was available.")
    for i in xrange(clusters):
        # get number of members of this cluster
        members=groups.count(i)
        cluster_array=np.zeros((members,d.shape[1],d.shape[2]))
        cluster_idx=0
        positions=np.zeros((members,3))
        for j in xrange(len(groups)):
            if groups[j]==i:
                cluster_array[cluster_idx,:,:]=d[j,:,:]
                try:
                    positions[cluster_idx]=self.mapped_parameters.locations[j]
                except:
                    pass
                cluster_idx+=1
        cluster_array_Image=Image({
            'data':avg_stack,
            'mapped_parameters':{
                'title' : 'Cluster %s from %s'%(i,
                    self.mapped_parameters.title),
                'locations':positions,
                'members':members,}
        })
        cluster_arrays.append(cluster_array_Image)
        avg_stack[i,:,:]=np.sum(cluster_array,axis=0)
    members_list=[groups.count(i) for i in xrange(clusters)]
    avg_stack_Image=Image({'data':avg_stack,
                'mapped_parameters':{
                    'title':'Cluster averages from %s'%self.mapped_parameters.title,
                    'member_counts':members_list,
                    }
                })
    return avg_stack_Image, cluster_arrays