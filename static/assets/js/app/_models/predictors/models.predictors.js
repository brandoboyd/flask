(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('PredictorsRest', PredictorsRest);

  /** @ngInject */
  function PredictorsRest(ModelRest, $q) {
    var Predictors = function () {
    };
    var BASE_URL = '/predictors';

    Predictors.prototype = new ModelRest(BASE_URL);

    Predictors.prototype.facets = {};

    Predictors.prototype.getOne = function (predictorId) {
      this.setUrl([BASE_URL, predictorId].join('/'));
      return this.get();
    };

    Predictors.prototype.list = function (params) {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.get(params);
    };

    Predictors.prototype.getPredictorFacets = function (predictor) {
      this.setUrl([BASE_URL, predictor.id, 'detail?facets=1'].join('/'));
      return this.get();
    };

    Predictors.prototype.getDefaultPredictor = function () {
      this.setUrl([BASE_URL, 'default-template'].join('/'));
      return this.get();
    };

    Predictors.prototype.getPredictorDetails = function (predictorId) {
      this.setUrl([BASE_URL, predictorId, 'detail'].join('/'));
      return this.get();
    };

    Predictors.prototype.doClassifier = function (action, predictor_id) {
      this.setUrl([BASE_URL, 'command', action, predictor_id].join('/'));

      if (action !== 'reset' && action !== 'retrain') {
        throw Error("Only actions 'reset' and 'retrain' supported. Given '" + action + "'");
      }
      return this.get();
    };

    Predictors.prototype.generatePredictorData = function (predictorId, fromDt, toDt) {
      this.setUrl([BASE_URL, 'command', 'generate_data', predictorId].join('/'));
      return this.post({'from_dt': fromDt, 'to_dt': toDt});
    };

    Predictors.prototype.purgePredictorData = function (predictorId, fromDt, toDt) {
      this.setUrl([BASE_URL, 'command', 'purge_data', predictorId].join('/'));
      return this.post({'from_dt': fromDt, 'to_dt': toDt});
    };

    Predictors.prototype.checkGenerationStatus = function (predictorId) {
        this.setUrl([BASE_URL, 'command', 'check_status', predictorId].join('/'));
        return this.get();
    };

    Predictors.prototype.removePredictor = function (predictorId) {
      this.setUrl([BASE_URL, predictorId].join('/'));
      return this.delete();
    };

    // MODELS
    Predictors.prototype.getOneModel = function (predictorId, modelId) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId].join('/'));
      return this.get();
    };

    Predictors.prototype.listModels = function (predictorId, with_deactivated) {
      var url = [BASE_URL, predictorId, 'models'].join('/');
      if (with_deactivated) {
        url += '?with_deactivated=true';
      }
      this.setUrl(url);
      return this.get();
    };

    Predictors.prototype.saveModel = function (predictorId, params) {
      this.setUrl([BASE_URL, predictorId, 'models'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.doModelAction = function (predictorId, modelId, action, params) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId, action].join('/'));
      return this.post(params);
    };

    Predictors.prototype.updateModel = function (predictorId, modelId, params) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId].join('/'));
      return this.put(params);
    };

    Predictors.prototype.removeModel = function (predictorId, modelId) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId].join('/') + '?hard=true');
      return this.delete();
    };

    Predictors.prototype.create = function (params) {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.getDetails = function (id, params) {
      this.setUrl([BASE_URL, id, 'data/json'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.getMatchResults = function (id, params) {
      this.setUrl([BASE_URL, id, 'search'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.update = function (predictorId, params) {
      this.setUrl([BASE_URL, predictorId].join('/'));
      return this.post(params);
    };

    return Predictors;
  }
})();
