import datetime
import pandas as pd
import numpy as np
import requests
import zipfile
import io
import warnings
import os
from sklearn import ensemble, model_selection
from evidently.report import Report
from evidently.metric_preset import RegressionPreset, DataDriftPreset, TargetDriftPreset
from evidently.pipeline.column_mapping import ColumnMapping
from evidently.ui.workspace import Workspace

warnings.filterwarnings('ignore')

DATA_URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
TARGET = 'cnt'
PREDICTION = 'prediction'
NUM_FEATURES = ['temp', 'atemp', 'hum', 'windspeed', 'mnth', 'hr', 'weekday']
CAT_FEATURES = ['season', 'holiday', 'workingday']
WEEKLY_PERIODS = {
    "week1": ('2011-01-29 00:00:00', '2011-02-07 23:00:00'),
    "week2": ('2011-02-07 00:00:00', '2011-02-14 23:00:00'),
    "week3": ('2011-02-15 00:00:00', '2011-02-21 23:00:00'),
}
WORKSPACE_DIR = "examen_evidently_workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)


# Fonction permettant de rajouter les projets dans le workspace
def add_report_to_workspace(workspace: Workspace, project_name: str, 
                            project_description: str, report: Report):
    """
    Ajoute un rapport à un projet Evidently (crée le projet s’il n’existe pas).
    """
    # Vérifie si le projet existe
    project = None
    for p in workspace.list_projects():
        if p.name == project_name:
            project = p
            break
    # Sinon, le créer
    if project is None:
        project = workspace.create_project(project_name)
        project.description = project_description
    # Ajouter le rapport
    workspace.add_report(project.id, report)
    print(f"Le rapport '{project_name} a été bien ajouté au projet'")

# Chargment des données
def _fetch_data() -> pd.DataFrame:
    content = requests.get(DATA_URL, verify=False).content
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        df = pd.read_csv(archive.open("hour.csv"), parse_dates=['dteday'])
    df.index = df.apply(lambda row: datetime.datetime.combine(row.dteday.date(), datetime.time(row.hr)), axis=1)
    return df


def main():
    # Initialisation du workspace Evidently
    workspace = Workspace(WORKSPACE_DIR)

    # Chargement des données
    raw_data = _fetch_data()
    jan_data = raw_data.loc['2011-01-01 00:00:00':'2011-01-28 23:00:00']
    feb_data = raw_data.loc['2011-01-29 00:00:00':'2011-02-28 23:00:00']

    # Split train/test
    X = jan_data[NUM_FEATURES + CAT_FEATURES]
    y = jan_data[TARGET]
    X_train, X_test, y_train, y_test = model_selection.train_test_split(X, y, test_size=0.3, random_state=42)

    # Entrainement du modèle
    model = ensemble.RandomForestRegressor(n_estimators=50, random_state=0)
    model.fit(X_train, y_train)

    # Ajout des colonnes target/prediction
    X_train['target'] = y_train
    X_train['prediction'] = model.predict(X_train[NUM_FEATURES + CAT_FEATURES])
    X_test['target'] = y_test
    X_test['prediction'] = model.predict(X_test[NUM_FEATURES + CAT_FEATURES])

    # Mapping des colonnes
    col_map = ColumnMapping()
    col_map.target = 'target'
    col_map.prediction = 'prediction'
    col_map.numerical_features = NUM_FEATURES
    col_map.categorical_features = CAT_FEATURES

    # Rapport de validation
    report_validation = Report(metrics=[RegressionPreset()])
    report_validation.run(reference_data=X_train, current_data=X_test, column_mapping=col_map)
    report_validation.save_html("report_validation.html")
    report_validation.save_json(f"{WORKSPACE_DIR}/report_validation.json")
    add_report_to_workspace(workspace, "examen_bike_drift_validation", "Validation train/test sur janvier", report_validation)

    # Réentraînement sur janvier complet pour la prod
    model.fit(jan_data[NUM_FEATURES + CAT_FEATURES], jan_data[TARGET])
    jan_data['prediction'] = model.predict(jan_data[NUM_FEATURES + CAT_FEATURES])
    jan_data['target'] = jan_data[TARGET]

    # Rapport prod janvier
    report_prod_jan = Report(metrics=[RegressionPreset()])
    report_prod_jan.run(reference_data=None, current_data=jan_data, column_mapping=col_map)
    report_prod_jan.save_html("report_production_jan.html")
    report_prod_jan.save_json(f"{WORKSPACE_DIR}/report_production_jan.json")
    add_report_to_workspace(workspace, "examen_bike_drift_production", "Performance du modèle sur janvier complet", report_prod_jan)

    # Rapports hebdomadaires
    for week, (start, end) in WEEKLY_PERIODS.items():
        week_data = feb_data.loc[start:end].copy()
        week_data['prediction'] = model.predict(week_data[NUM_FEATURES + CAT_FEATURES])
        week_data['target'] = week_data[TARGET]

        report_week = Report(metrics=[RegressionPreset()])
        report_week.run(reference_data=jan_data, current_data=week_data, column_mapping=col_map)
        report_week.save_html(f"report_{week}.html")
        report_week.save_json(f"{WORKSPACE_DIR}/report_{week}.json")
        add_report_to_workspace(workspace, f"examen_bike_drift_{week}", f"Analyse de la semaine {week[-1]}", report_week)

    # Dérive de la cible (target drift - semaine 3)
    week3_data = feb_data.loc[WEEKLY_PERIODS["week3"][0]:WEEKLY_PERIODS["week3"][1]].copy()
    week3_data['prediction'] = model.predict(week3_data[NUM_FEATURES + CAT_FEATURES])
    week3_data['target'] = week3_data[TARGET]

    target_drift = Report(metrics=[TargetDriftPreset()])
    target_drift.run(reference_data=jan_data, current_data=week3_data, column_mapping=col_map)
    target_drift.save_html("report_target_drift_week3.html")
    target_drift.save_json(f"{WORKSPACE_DIR}/report_target_drift_week3.json")
    add_report_to_workspace(workspace, "examen_bike_drift_target_week3", "Dérive de la cible – semaine 3", target_drift)

    # Dérive des données numériques (data drift)
    col_map_drift = ColumnMapping()
    col_map_drift.target = TARGET
    col_map_drift.prediction = PREDICTION
    col_map_drift.numerical_features = NUM_FEATURES

    data_drift = Report(metrics=[DataDriftPreset()])
    data_drift.run(reference_data=jan_data, current_data=week3_data, column_mapping=col_map_drift)
    data_drift.save_html("report_data_drift_week3.html")
    data_drift.save_json(f"{WORKSPACE_DIR}/report_data_drift_week3.json")
    add_report_to_workspace(workspace, "examen_bike_drift_data_week3", "Dérive des features numériques – semaine 3", data_drift)

if __name__ == '__main__':
    main()
