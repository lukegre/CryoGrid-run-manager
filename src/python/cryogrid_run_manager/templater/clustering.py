"""
Purpose is to determine the correct number of clusters for a given bounding box.

For this to work, we need to:
1) read in the config file,
2) extract the cluster variables,
3) create the clustering variables,
4) cluster (K-means) with a range of cluster numbers,
5)
"""

import faiss
import numpy as np


class FaissKMeans:
    def __init__(self, n_clusters=8, n_init=10, max_iter=300):
        self.n_clusters = n_clusters
        self.n_init = n_init
        self.max_iter = max_iter
        self.kmeans = None
        self.cluster_centers_ = None
        self.inertia_ = None

    def fit(self, X, *args, **kwargs):
        self._X = X
        self.kmeans = faiss.Kmeans(
            d=X.shape[1], k=self.n_clusters, niter=self.max_iter, nredo=self.n_init
        )
        self.kmeans.train(X.astype(np.float32))
        self.cluster_centers_ = self.kmeans.centroids
        self.inertia_ = self.kmeans.obj[-1]

    def predict(self, X, *args, **kwargs):
        return self.kmeans.index.search(X.astype(np.float32), 1)[1]

    def fit_predict(self, X, *args, **kwargs):
        self.fit(X, *args, **kwargs)
        return self.predict(X, *args, **kwargs)

    def score(self, type="silhouette"):
        X = self._X
        if type == "silhouette":
            return self._score_silhouette(X)
        elif type == "elbow":
            return self.intertia_

    def _score_silhouette(self, X):
        from sklearn.metrics import silhouette_score

        labels = self.predict(X)
        return silhouette_score(X, labels)
