from solariat.db.abstract import fields
from solariat_bottle.db.predictors.models.linucb import LinUCBPredictorModel


class LinearRegressorModel(LinUCBPredictorModel):

    avg_error = fields.NumField(db_field='avg', default=0)
    nr_scores = fields.NumField(db_field='nr_scores', default=0)
    rmse = fields.NumField(db_field='rmse')
    mse = fields.NumField(db_field='mse') # mean square error
    mae = fields.NumField(db_field='mae') # mean absolute error
    r2_score = fields.NumField(db_field='re') 
    fraction_below_quantile = fields.NumField(db_field='fbq')

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        from solariat_bottle.db.predictors.classifiers import PassiveAggresiveRegressor, QuantileGradentBoostingRegressor
        return QuantileGradentBoostingRegressor

    @property
    def performance_metrics(self):
        return "Avg Error: %.2f;  Number of Predictions: %s" % (self.avg_error, self.nr_scores)

    def reset_performance_stats(self):
        self.avg_error = 0
        self.nr_scores = 0
        self.save()

    def to_json(self, fields_to_show=None):
        base_json = super(LinearRegressorModel, self).to_json(fields_to_show=fields_to_show)
        base_json['perfomance_metrics'] = self.performance_metrics
        base_json['quality'] = [
            dict(measure='RMSE', score=self.rmse),
            dict(measure='MSE', score=self.mse),
            dict(measure='FBQ', score=self.fraction_below_quantile),
            dict(measure='MAE', score=self.mae),
            dict(measure='R2S', score=self.r2_score)
        ]
        return base_json

    def class_validity_check(self, values, min_samples_thresould):
        return len(values) >= min_samples_thresould


class LinearClassifierModel(LinUCBPredictorModel):

    true_positives = fields.NumField(db_field='tp', default=0)
    false_positives = fields.NumField(db_field='fp', default=0)
    true_negatives = fields.NumField(db_field='tn', default=0)
    false_negatives = fields.NumField(db_field='fn', default=0)
    auc = fields.NumField(db_field='auc')

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        from solariat_bottle.db.predictors.classifiers import PassiveAggresiveClassifier, QuantileGradientBoostingClassifier
        return QuantileGradientBoostingClassifier

    def reset_performance_stats(self):
        self.true_positives = 0
        self.false_positives = 0
        self.true_negatives = 0
        self.false_negatives = 0
        self.save()

    def score(self, filtered_context, filtered_actions):
        return self.clf.score(filtered_context, filtered_actions)

    def to_json(self, fields_to_show=None):
        base_json = super(LinearClassifierModel, self).to_json(fields_to_show=fields_to_show)
        base_json['perfomance_metrics'] = self.performance_metrics
        base_json['quality'] = [dict(measure='AUC', score=self.auc)]
        return base_json

    @property
    def performance_metrics(self):
        precision = 'NaN'
        if self.true_positives or self.false_positives:
            precision = self.true_positives / float(self.true_positives + self.false_positives)
            precision = float("%.2f" % precision)

        recall = 'NaN'
        if self.true_positives or self.false_negatives:
            recall = self.true_positives / float(self.true_positives + self.false_negatives)
            recall = float("%.2f" % recall)

        return "Precision: %s;  Recall: %s, TP: %s, FP: %s, FN: %s, TN: %s" % (precision, recall,
                                                                                   self.true_positives,
                                                                                   self.false_positives,
                                                                                   self.false_negatives,
                                                                                   self.true_negatives)

    def class_validity_check(self, values, min_samples_thresould):
        return len(values) >= min_samples_thresould and len(set(values)) > 1
