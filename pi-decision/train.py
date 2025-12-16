#!/usr/bin/env python3
"""Simple training script to fit RandomForestRegressor on historic profiles.
Expect CSV with columns: mean_rms_db,target_noisiness
"""
import argparse
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib


def train(csv_path, model_out):
    df = pd.read_csv(csv_path)
    X = df[["mean_rms_db"]].values
    y = df["target_noisiness"].values
    model = RandomForestRegressor(n_estimators=100)
    model.fit(X, y)
    joblib.dump(model, model_out)
    print("Saved model to", model_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--out", default="model.joblib")
    args = parser.parse_args()
    train(args.csv, args.out)
