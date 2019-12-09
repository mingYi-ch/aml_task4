import biosppy.signals.eeg as eeg
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score
from sklearn.metrics import make_scorer
from sklearn.metrics import f1_score
from sklearn.ensemble import AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier
import biosppy.signals.tools as bt

from sklearn.model_selection import GridSearchCV



def read_from_file(X_train_file, X_predict_file,  y_train_file = None, is_testing = False):
    y_train = []
    if is_testing:
        # read from files
        x_train = pd.read_csv(X_train_file, index_col='Id', nrows = 10).to_numpy()
        x_predict = pd.read_csv(X_predict_file, index_col='Id', nrows = 10).to_numpy()
    else:
        x_train = pd.read_csv(X_train_file, index_col='Id').to_numpy()
        x_predict = pd.read_csv(X_predict_file, index_col='Id').to_numpy()
        if y_train_file:
            y_train = pd.read_csv(y_train_file, index_col='Id').to_numpy()
    return x_train, x_predict, y_train

# return a list of statistics
def transform(wave_name):
    mean = np.mean(wave_name)
    var = np.var(wave_name)
    high = np.amax(wave_name)
    low = np.amin(wave_name)
    stats = np.array([mean, var, high, low])
    return stats


def feature_extraction(eeg1, eeg2, emg):
    # remove nan value in nparray
    x_new = []
    for sig_mat in zip(eeg1, eeg2, emg):
        # read signal pairs in the matrix
        elem1 = sig_mat[0].reshape(1, -1)
        elem2 = sig_mat[1].reshape(1, -1)
        emg = sig_mat[2]

        eegs = np.concatenate((elem1, elem2), axis=0)
        eegs = np.transpose(eegs)

        # eeg feature construction
        signal_processed = eeg.eeg(signal=eegs, sampling_rate=128, show=False)
        # theta = signal_processed[3]
        # alow = signal_processed[4]
        # ahigh = signal_processed[5]
        # beta = signal_processed[6]
        # gamma = signal_processed[7]

        sig_trans_eeg1 = bt.analytic_signal(elem1)
        sig_trans_eeg2 = bt.analytic_signal(elem2)

        features = np.array([])
        # add the stats os theta ... gamma
        for idx in range(3, 8):
            wave_type = signal_processed[idx]
            features = np.append(features, [transform(wave_type[:, 0]), transform(wave_type[:, 1])])

        # add the amplitude from the Hilbert transform
        np.append(features, [transform(sig_trans_eeg1[1]), transform(sig_trans_eeg2[1])])

        # emg feature construction
        sig_trans_emg = bt.analytic_signal(emg)
        np.append(features, transform(sig_trans_emg))

        x_new.append(features)
    x_new = np.array(x_new)
    print("features", x_new.shape)
    return x_new


def processed_to_csv(X_train, flag = 'train'):
    X = np.asarray(X_train)
    if flag == 'test':
        np.savetxt(copa + 'X_test_temMed.csv', X)
    else:
        np.savetxt(copa + 'X_train_temMed.csv', X)


def result_to_csv(predict_y, sample_file):
    # write the result to the CSV file
    sample_file = pd.read_csv(sample_file)
    id = sample_file['id'].to_numpy().reshape(-1, 1)
    result = np.concatenate((id, predict_y.reshape(-1, 1)), axis=1)
    result = pd.DataFrame(result, columns=['id', 'y'])
    result.to_csv(copa + 'predict_y.csv', index=False)


def standarlization(train_x, test_x):
    # standarlization
    scalar = StandardScaler()
    train_x = scalar.fit_transform(train_x.astype('float64'))
    test_x = scalar.transform(test_x.astype('float64'))
    return train_x, test_x


def svmClassifier(train_x, train_y, test_x):
    train_y = train_y.ravel()
    classifier = SVC(class_weight='balanced', gamma=0.001, C=10)  # c the penalty term for misclassification
    # make balanced_accuracy_scorer
    score_func = make_scorer(f1_score, average='micro') # additional param for f1_score
    # cross validation
    scores = cross_val_score(classifier, train_x, train_y, cv=5, scoring=score_func)
    print(scores)
    # learn on all data
    classifier.fit(train_x, train_y)
    y_predict_test = classifier.predict(test_x)
    return y_predict_test


def grid_search(train_x, train_y, test_x):
    parameters = {'C': [ 10, 20, 25, 30], 'gamma': [0.001, 0.005, 0.01]}
    svcClassifier = SVC(kernel='rbf', class_weight='balanced')
    score_func = make_scorer(f1_score, average='micro')
    gs = GridSearchCV(svcClassifier, parameters, cv=5, scoring=score_func)
    gs.fit(train_x, train_y)
    print(gs.cv_results_)
    print(gs.best_params_)
    print(gs.best_score_)
    y_predict_test = gs.predict(test_x)
    return y_predict_test


def adaBoostClassifier(train_x, train_y, test_x):
    train_y = train_y.ravel()
    classifier = AdaBoostClassifier(base_estimator=DecisionTreeClassifier(max_depth=None), n_estimators=60, learning_rate=0.8)
    # make balanced_accuracy_scorer
    score_func = make_scorer(f1_score, average='micro')  # additional param for f1_score
    # cross validation
    scores = cross_val_score(classifier, train_x, train_y, cv=5, scoring=score_func)
    print(scores)
    # learn on all data
    classifier.fit(train_x, train_y)
    y_predict_test = classifier.predict(test_x)
    return y_predict_test


if __name__ == '__main__':
    is_start = True
    is_testing = True
    is_colab = False
    copa = ''
    if is_colab:
        copa = '/content/drive/My Drive/aml_task4/'
    # read data from files
    if is_start:
        # read
        eeg1s = read_from_file(copa + "train_eeg1.csv", copa + "test_eeg1.csv", copa + "train_labels.csv", is_testing = is_testing)
        eeg2s = read_from_file(copa + "train_eeg2.csv", copa + "test_eeg2.csv", is_testing = is_testing)
        emgs  = read_from_file(copa + "train_emg.csv", copa + "test_emg.csv", is_testing = is_testing)

        # get different files
        train_eeg1 = eeg1s[0]
        train_eeg2 = eeg2s[0]
        train_emg = emgs[0]

        test_eeg1 = eeg1s[1]
        test_eeg2 = eeg2s[1]
        test_emg = emgs[1]

        # feature extraction
        train_features = feature_extraction(train_eeg1, train_eeg2, train_emg)
        test_features =  feature_extraction(test_eeg1, test_eeg2, test_emg)

        # standarlization
        x_std = standarlization(train_features, test_features)
        x_train_std = x_std[0]
        x_test_std = x_std[1]

        # write processed data to csv
        processed_to_csv(x_train_std)
        processed_to_csv(x_test_std, flag = 'test')

    if not is_start:
        x_train_std =  pd.read_csv(copa + 'X_train_temMed.csv', delimiter=' ', index_col=False, header = None).to_numpy()
        x_test_std = pd.read_csv(copa + 'X_test_temMed.csv', delimiter=' ', index_col=False, header=None).to_numpy()
        
        # print(x_train_std[[10, 14, 17, 18]][:, -2:])
    # prediction
    y_train = pd.read_csv(copa + "train_labels.csv", index_col='Id').to_numpy()
    # y_predict = grid_search(x_train_std, y_train, x_test_std)
    y_predict = svmClassifier(x_train_std, y_train, x_test_std)
    # neural net
    # y_predict = neurNet_classifier(x_train_std, y_train, x_test_std)
    # Adaboost classifier
    # y_predict = adaBoostClassifier(x_train_std, y_train, x_test_std)
    # grid search
    result_to_csv(y_predict, copa + 'sample.csv')
