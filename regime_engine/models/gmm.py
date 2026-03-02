import numpy as np
from sklearn.mixture import GaussianMixture

class RegimeGMM:
    def __init__(self, n_regimes=3, covariance_type='full', random_state=42):
        self.n_regimes = n_regimes
        self.model = GaussianMixture(n_components=n_regimes, covariance_type=covariance_type, random_state=random_state)
    def fit(self, X):
        self.model.fit(X)
    def predict(self, X):
        return self.model.predict(X)
