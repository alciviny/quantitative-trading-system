from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
import pandas as pd

def train_ensemble(X_train, y_train, random_state=42):
    ensemble = VotingClassifier(estimators=[
        ('rf', RandomForestClassifier(n_estimators=200, random_state=random_state, n_jobs=-1)),
        ('gb', GradientBoostingClassifier(n_estimators=100, random_state=random_state)),
        ('lr', LogisticRegression(max_iter=1000, random_state=random_state))
    ], voting='soft', n_jobs=-1)
    ensemble.fit(X_train, y_train)
    return ensemble

def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)
    return report, cm, y_pred
