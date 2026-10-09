
from models.isolation_forest_model import run_model as run_if
from models.local_outlier_factor_model import run_model as run_lof
from models.one_class_svm_model import run_model as run_svm

CSV_FILE = "data set/updated_lof_downgraded_dataset (1).csv"

run_if(CSV_FILE)
run_lof(CSV_FILE)
run_svm(CSV_FILE)
