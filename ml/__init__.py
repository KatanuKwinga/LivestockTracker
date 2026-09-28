"""Machine-learning pipeline for Livestock Tracker: sickness-risk prediction
(will an animal fall sick within the next 14 days?).

How the pieces fit together (read in this order):

    synthetic.py  -> generates realistic practice data shaped exactly like
                     our livestock / weight_records / health_records tables
    data.py       -> moves data between the MySQL database and pandas
                     DataFrames (load for training, seed synthetic data in)
    features.py   -> turns raw records into one row of numbers per
                     (animal, date) — the "features" the model learns from
    train.py      -> trains and compares candidate models, evaluates the
                     winner honestly, saves it to ml/artifacts/
    predict.py    -> loads the saved model and scores a farmer's animals
                     as of today (this is what the Flask page calls)
    seed.py       -> command-line tool to load synthetic data into the DB

Nothing in synthetic.py / features.py / train.py's core functions imports
Flask, so the modelling code can be run and tested on its own.
"""
