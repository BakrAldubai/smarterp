import datetime
import csv
import json


from sklearn.ensemble import RandomForestClassifier
from sklearn import preprocessing
from sklearn.model_selection import KFold
from sklearn.model_selection import cross_val_score
import pandas as pd
import numpy as np

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression

import joblib

class Learner:
    def __init__(self, path):
        self.models = {}
        self.feature_labelencoder = None
        self.target_labelencoder = None
        self.features = []
        self.target = []
        self.models["rf"] = RandomForestClassifier(n_estimators=400)

        self.path = path
        self.filename_model = "rfclf.pkl"
        self.filename_le = "rfle.npy"


    def select_features_all(self,df,training=True):
        select_cols = [
            "owner",
            "modified_by",
            "customer",
            "raised_by",
            "status",
            "domain",
            "day_of_week"
        ]
        select_cols = select_cols + [col for col in df.columns.tolist() if col.startswith("avg")]
        select_cols = select_cols + [col for col in df.columns.tolist() if col.startswith("std")]
        if(training): select_cols.append("todo_owner")
        df = df[select_cols]

        return df
    
    def encode_target(self, target_series_train):
        
        #Labelencoding verwandelt NaN in eine Kategorie
        le = preprocessing.LabelEncoder()
        tst_reshaped = target_series_train.values.ravel()
        le.fit(tst_reshaped)
        self.target_labelencoder = le

        encoded = le.transform(tst_reshaped)
            
        return encoded

    def le_features(self,df_final):
        df = df_final.copy()
        #Create labelencoders
        if(self.feature_labelencoder == None):
            print("Creating new label encoders for features.")
            self.feature_labelencoder = {}
            #Labelencoding verwandelt NaN in eine Kategorie
            cat_cols = df.select_dtypes(include=['object','category'])
            for col in cat_cols:
                le = preprocessing.LabelEncoder()
                df.loc[:,col] = le.fit_transform(df[col].astype(str))
                self.feature_labelencoder[col] = le
            float64_cols = df.select_dtypes(include=["float64"])
            for col in float64_cols:
                df.loc[:,col] = df.loc[:,col].astype(np.float32)
        #Work with already existing labelencoders
        else:
            print("Using existing label encoders for features.")
            cat_cols = df.select_dtypes(include=['object','category'])
            for col in cat_cols:
                le = self.feature_labelencoder[col]
                df.loc[:,col] = le.transform(df[col].astype(str))
                self.feature_labelencoder[col] = le
            float64_cols = df.select_dtypes(include=["float64"])
            for col in float64_cols:
                df.loc[:,col] = df.loc[:,col].astype(np.float32)

        return df

    def remove_duplicates(self, df):
        df = df.sort_values("start_date",ascending=True)
        is_duplicate = df.duplicated(subset=["todo_owner","name"], keep="last")
        new_df = df[~is_duplicate]
        return new_df

    def remove_nan_rows(self,df):
        return df.dropna(axis="index")

    def rf_cross_val(self,df):
        #Preprocess
        df = self.remove_duplicates(df)
        df = self.select_features_all(df)
        #df = self.remove_nan_rows(df)
        
        #Select
        features = df.columns.tolist()
        features.remove("todo_owner")
        target = ["todo_owner"]

        #Transform
        X = df[features]
        y = df[target]
        X = self.le_features(X) #Encode only test set
        y = self.encode_target(y)

        #Cross Val
        clf = make_pipeline(RandomForestClassifier(n_estimators=400))
        cv = KFold(n_splits=10, random_state=123, shuffle=True)
        accs = cross_val_score(self.models["rf"], X, y, scoring="accuracy", cv=cv)
        print(accs)
        print(np.mean(accs))

    def svc_cross_val(self,df):
        #Preprocess
        df = self.remove_duplicates(df)
        df = self.select_features_all(df)

        #Select
        features = df.columns.tolist()
        features.remove("todo_owner")
        target = ["todo_owner"]

        #Transform
        X = df[features]
        y = df[target]

        X = pd.get_dummies(X)
        float64_cols = X.select_dtypes(include=["float64"])
        for col in float64_cols:
            X.loc[:,col] = X.loc[:,col].astype(np.float32)
        
        y = self.encode_target(df[target])

        #Cross Val
        clf = make_pipeline(StandardScaler(),SVC(gamma="auto"))
        cv = KFold(n_splits=10, random_state=123, shuffle=True)
        accs = cross_val_score(clf, X, y, scoring="accuracy", cv=cv)
        print(accs)
        print(np.mean(accs))

    def train_rf(self,df):
        #Clean
        df = self.remove_duplicates(df)
        df = self.select_features_all(df)
        #df = self.remove_nan_rows(df)

        #Seperate
        features = df.columns.tolist()
        features.remove("todo_owner")
        target = ["todo_owner"]

        #Transform
        X = self.le_features(df[features]) #Encode only test set
        y = self.encode_target(df[target])

        #Train
        self.models["rf"].fit(X,y)

    def save(self):
        joblib.dump(self.models["rf"],self.path + self.filename_model, compress=9)
        np.save(self.path + self.filename_le, self.target_labelencoder.classes_)
        with open(self.path + "le_features_keys.json", mode="w") as f:
            for key,val in self.feature_labelencoder.items():
                np.save(self.path + key + ".npy",val.classes_)
                f.write(key + "\n")

    def load(self):
        self.models["rf"] = joblib.load(self.path + self.filename_model)
        self.target_labelencoder = preprocessing.LabelEncoder()
        self.target_labelencoder.classes_ = np.load(self.path + self.filename_le, allow_pickle = True)
        keys = []
        with open(self.path + "le_features_keys.json", mode="r") as f:
            for key in f.readlines():
                keys.append(key.replace("\n",""))
        self.feature_labelencoder = {}
        for key in keys:
            self.feature_labelencoder[key] = preprocessing.LabelEncoder()
            self.feature_labelencoder[key].classes_ = np.load(self.path + key + ".npy", allow_pickle = True)


    def predict_rf(self,df):
        print("Shape of sample that goes into prediction: " + str(df.shape))
        #Clean
        df = self.select_features_all(df,training=False)

        #Transform
        df = self.le_features(df)

        #Predict
        result = self.models["rf"].predict(df)
        proba = self.models["rf"].predict_proba(df)
        
        #For debugging
        #print(self.target_labelencoder.classes_)
        #print(self.target_labelencoder.inverse_transform(result))
        #print(proba)

        assignment_probs = []
        for results in proba:
            for i in range(len(results)):
                name = self.target_labelencoder.classes_[i]
                p = results[i]
                assignment_probs.append({"name":name,"probability":p})
        
        #print(assignment_probs)

        sort = sorted(assignment_probs, key=lambda item:item["probability"], reverse=True)
        print(sort)

        return assignment_probs