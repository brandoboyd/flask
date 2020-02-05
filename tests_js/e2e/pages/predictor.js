'use strict';

var Predictor = function() {
      var simplePredictorName = 'SimpleTestPredictor#' + Date.now();

      this.navigateToPredictorsList = function() {
        element(by.css('.nav-side-tabs')).element(by.linkText('Predictors')).click();
      };

      this.clickAddNewPredictorBtn = function() {
        var createBtn = element(by.css('a[href="#/predictors_v2/new"]'));
        createBtn.click();
      };

      this.addDataset = function() {
        var dataset     = element(by.id('dataset'));
        //Click to select dataset option
        var select = dataset.click();
        select.$('[value="0"]').click();
      };

      this.addPredictorName = function(predictorName) {
        element(by.id('predictor_name')).clear().sendKeys(predictorName);
      };

      this.getPredictorNameValue = function() {
        return element(by.id('predictor_name')).getAttribute('value');
      };

      this.addMetric = function(label) {
        var metric = element(by.model('predictor.metric'));
        //Fill in Metric field
        metric.click();
        metric.element(by.css('.ui-select-search')).sendKeys(label, protractor.Key.ENTER);
      };

      this.getModelValue = function(model) {
        return element(by.model(model)).getText();
      };

      this.addActionId = function(label) {
        var actionId = element(by.model('predictor.action_id_expression'));
        //Fill in Action ID field
        actionId.click();
        actionId.element(by.css('.ui-select-search')).sendKeys(label, protractor.Key.ENTER);
      };

      this.addActionType = function(optionName) {
        var actionType  = element(by.cssContainingText('option', optionName));
        //Fill in Action Type
        actionType.click();
      };

      this.getActionTypeValue = function() {
        return element(by.id('action_type')).element(by.css('option:checked')).getText();
      };

      this.addActionFeature = function(rowNum, label) {
        var addNewActionFeatureBtn  = element.all(by.css('[ng-click="onAddFeature($event, featureType.key)"]')).get(0);
        //Add Action Features
        addNewActionFeatureBtn.click();
        var feature = element(by.repeater('feature in predictor[featureType.key]').row(rowNum));
        feature.element(by.css('.ui-select-search')).sendKeys(label, protractor.Key.ENTER);
      };

      this.getFeatureLabelValue = function(rowNum) {
        var feature = element(by.repeater('feature in predictor[featureType.key]').row(rowNum));
        return feature.element(by.model('feature.label')).getAttribute('value');
      };

      this.getFeatureTypeValue = function(rowNum) {
        var feature = element(by.repeater('feature in predictor[featureType.key]').row(rowNum));
        return feature.element(by.model('feature.type')).element(by.css('option:checked')).getText();
      };

      this.addContextFeature = function(rowNum, label) {
        var addNewContextFeatureBtn = element.all(by.css('[ng-click="onAddFeature($event, featureType.key)"]')).get(1);
        //Add Context Features
        addNewContextFeatureBtn.click();
        var cfeature1 = element(by.repeater('feature in predictor[featureType.key]').row(rowNum));
        cfeature1.element(by.css('.ui-select-search')).sendKeys(label, protractor.Key.ENTER);
      };

      this.generateData = function() {
        element(by.buttonText('Generate')).click();
      }
};

module.exports = Predictor;
