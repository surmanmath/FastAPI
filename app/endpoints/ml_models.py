import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from .utils import serie_generator
import datetime
import joblib

def lecture_donnees(file):

    data = pd.read_csv(file,sep=",", index_col=0)
    size = len(data)
    # transformation de la date en variable quantitative
    dates = [data["Date"][i].split("-") for i in range(size)]
    dates = np.array(dates).T
    # ajout au df
    data.insert(10, "Annee", dates[0])
    data.insert(11, "Mois", dates[1])
    data.insert(12, "Jour", dates[2])
    # utilisation de la date comme intervalle de temps depuis la date initiale
    date_initiale = datetime.datetime.strptime("2004-01-01", "%Y-%m-%d")
    date_delta = [(datetime.datetime.strptime(d, "%Y-%m-%d") - date_initiale).days for d in data["Date"]]
    data.insert(13, "Delta", date_delta)

    # liste des variables explicatives / variable cible
    variables_exp = ["N1", "N2", "N3", "N4", "N5", "E1", "E2", "Annee", "Mois", "Jour", "Delta"]
    X = data[variables_exp]
    y = [0 if data.at[i,"Gain"] == 0 else 1 for i in range(size)]
    # découpage en jeu d'entrainement / jeu de test
    test_size = 0.2
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=1)
    scaler = StandardScaler()
    scaler.fit(X_train)
    X_train = scaler.transform(X_train)
    X_test = scaler.transform(X_test)

    # infos correspondantes aux données
    # nombre de tirages gagnants
    nw = np.count_nonzero(y)
    # pourcentage de gagnants 
    pw = nw / (size-nw)
    infos = pd.DataFrame([str(variables_exp), size, test_size, pw], columns=["Valeur"], index=["Variables", "Nombre de données", "Pourcentage des données utilisé pour le test", "Pourcentage de tirages gagnants"])
    
    return X_train, X_test, y_train, y_test, infos


def entrainement(X_train, X_test, y_train, y_test, infos):
    model = RandomForestClassifier()
    model.fit(X_train, np.ravel(y_train))

    # enregistrer le modèle
    file = "app/static/ml_model.joblib.pkl"
    joblib.dump(model, file, compress=9)

    # enregistrement des informations du modèle
    pred = model.predict(X_test)
    # métriques
    accuracy = accuracy_score(y_test, pred)
    precision = precision_score(y_test, pred, average='binary', zero_division=1)
    recall = recall_score(y_test, pred)

    proba = model.predict_proba(X_test)
    pmean = proba[:,1].mean() # probabilité moyenne de gagner sur le jeu de test
    prange = [proba[:,1].min(), proba[:,1].max()] # intervalle de probabilité

    # écrire tout dans un df
    values = ["Random Forest", accuracy, precision, recall, pmean, prange]
    indexes = ["Modele", "Accuracy", "Precision", "Recall", "Probabilité moyenne", "Intervalle de Probalilité"]
    df = pd.DataFrame(values, columns=["Valeur"], index=indexes)
    df_tot = pd.concat([infos, df])
    df_tot.to_csv("app/static/data_model.csv", index=True)

    return(None)


def charger_modele():
    model = joblib.load("app/static/ml_model.joblib.pkl")
    return model

# def save_data(model, X_test, y_test, y_train):
#     """ Enregistre les donnees du modele :
#             - Type de modele utilise
#             - Accuracy, Precision et Recall
#             - Nb de donnees d'entrainement / de test
#             - pourcentage de tirages gagnants

#     Params:
#         model (obj): le modele de machine learning
#         X_test (np.array): les variables explicatives des données de test
#         y_test (np.array): vecteur de la variable cible des données de test
    
#     Returns:
#         None
#     """
#     pred = model.predict(X_test)
#     # métriques
#     accuracy = accuracy_score(y_test, pred)
#     precision = precision_score(y_test, pred, average='binary', zero_division=1)
#     recall = recall_score(y_test, pred, average='binary')

#     proba = model.predict_proba(X_test)
#     pmean = proba[:,1].mean() # probabilité moyenne de gagner sur le jeu de test

#     y = pd.concat([y_train, y_test])
#     # nombre de tirages gagnants
#     nw = np.count_nonzero(y)
#     # pourcentage de gagnants 
#     pw = nw / (len(y)-nw)
#     N = len(y) 

#     # écrire tout dans un df
#     values = ["Random Forest", accuracy, precision, recall, pmean, pw, N, 0.2]
#     indexes = ["Modele","Accuracy", "Precision", "Recall", "Probabilité moyenne", "Pourcentage de gagnants", "Nombre de données", "Jeu de test"]
#     df = pd.DataFrame(values, columns=["Valeur"], index=indexes)
#     df.to_csv("app/static/data_model.csv", index=True)

#     return(None)


def predire(model, x):
    """ Fonction qui prédit la probabilité qu'une suite x de nombre soit gagnante, 
        selon le modèle model

    Args:
        model (type??): le modèle de prédiction
        x (list of int): la série d'entiers correspondant a une grille jouée à l'euromilion

    Returns:
        float: la probabilité que la suite jouée x soit gagnante

    """
    # ajout de la date au tirage
    today = datetime.date.today()
    annee = today.strftime("%Y")
    mois = today.strftime("%m")
    jour = today.strftime("%d")
    delta = (datetime.datetime.now() - datetime.datetime.strptime("2004-01-01", "%Y-%m-%d")).days
    x = np.append(x, [annee, mois, jour, delta])
    
    proba = model.predict_proba(x.reshape(1, -1))
    return(proba[0][1])


def tirer_un_bon(model, prob_min):
    """ Fonction qui trouve un gagnant probable 

    Args : 
        model (obj): le modèle de prédiction
        prob_min (float): le minimum de probabilité de gagner souhaitée
    
    Returns:
        list of int: le tirage de probabilité supérieur à prob_min 
            s'il a été trouvé
            sinon le tirage le plus probable visité
    """

    Kmax = 10**3 # Nombre d'irérations max
    k = 0 # compteur d'itérations
    tirage_best = [] # enregistrement du meilleur tirage visité
    prob_best = 0 # et de sa probabilité de gagner

    # arret au bout de k itérations si impossible de trouver une proba > prob_min
    # retenir le meilleur tirage calculé dans ce cas avec sa proba
    while k < Kmax:
        tirage = serie_generator()
        prob = predire(model=model, x=tirage)
        if prob >= prob_min:
            return tirage, prob, True
        if prob > prob_best:
            tirage_best = tirage
            prob_best = prob
        k += 1
    
    return tirage_best, prob_best, False