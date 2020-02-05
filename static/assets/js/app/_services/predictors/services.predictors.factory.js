(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('PredictorService', PredictorService);

  /**@ngInject */
  function PredictorService($http, $q) {

    var predictorFacets = {};
    var factory = {
      getAllPredictors: getAllPredictors,
      doClassifier: doClassifier,
      getPredictorTypes: getPredictorTypes,
      predictorFacets: predictorFacets,
      getSelectedPredictors: getSelectedPredictors,
      listAllPredictors: listAllPredictors
    };

    return factory;
    /////////////////////////////////////

    function getSelectedPredictors(ids) {
      var predictors;
      if (ids) {
        return $http({
          method: 'GET',
          url: '/predictors/json'
        }).then(function (res) {
          predictors = _.filter(res.data.list, function (item) {
            return ids.indexOf(item.id) !== -1;
          })
        }).then(function () {
          return predictors;
        });
      } else {
        return $q.when([]);
      }
    }

    function listAllPredictors(params) {
      var predictors;

      return $http({
        method: 'GET',
        url: '/predictors/json',
        params: params
      }).then(function (res) {
        predictors = res.data.list;
      }).then(function () {
        return predictors;
      });

    }

    function getAllPredictors(params) {

      var predictors = {};

      if (typeof params === 'undefined') {
        params = {}
      }
      params['aggregate'] = true

      var promise = $http({
        method: 'GET',
        url: '/predictors/json',
        params: params
      }).then(function (res) {

        //filter out complex predictors for now
        predictors['list'] = _.filter(res.data.list, function (pr) {
          return pr.predictor_type !== 'Composite Predictor'
        });

        var promises = _.map(predictors.list, function (predictor) {
          return $http({
            method: 'GET',
            url: '/predictors/' + predictor.id + '/detail?facets=1'
          }).then(processFacet);
        });
        return $q.all(promises);
      }).then(function () {
        return predictors;
      });

      return promise;
      ///////////////

      function processFacet(res) {
        if (!res.data) return;

        var facet = {
          action_vector: {},
          context_vector: {},
          models: {
            all: true,
            list: []
          }
        };

        facet.models.list = _.map(res.data.models_data, function (model) {
          return {
            id: model.model_id,
            display_name: model.display_name,
            enabled: false
          }
        });

        _.each(['action_vector', 'context_vector'], function (key) {

          var mappedKey = (key == 'action_vector') ? 'action_features' : 'context_features';

          _.each(res.data[mappedKey], function (item) {

            facet[key][item.feature] = {
              id: item.feature,
              all: true,
              visible: false,
              description: item.description,
              list: _.map(item.values, function (val) {
                return {
                  display_name: val,
                  enabled: false
                };
              })
            };

          });

        });

        predictorFacets[res.data.id] = facet;
      }

    }

    function getPredictorTypes() {
      /* [{
       display_name: "Agent Matching",
       description: "Predictor for matching agent against customer."
       }, {
       display_name: "Supervisor Alert",
       description: "Predictor for making decision on alert supervisor."
       }, {
       display_name: "Chat Offer",
       description: "Predictor for making decision on chat engagement."
       }] */
      var promise = $http({
        method: 'GET',
        url: '/predictors/default-template'
      }).then(function (res) {
        var types = res.data.template.types;
        if (res.data.template) {
          return _.map(res.data.template.types, function (type) {
            var item = _.find(res.data.template, function (e, key) {
              return e.predictor_type == type;
            });
            return {
              display_name: type,
              description: (item) ? item.description : '',
              enabled: false
            };
          });
        } else {
          return [];
        }
      });
      return promise;
    }

    function doClassifier(action, predictor_id) {
      if (action !== 'reset' && action !== 'retrain') {
        throw Error("Only actions 'reset' and 'retrain' supported. Given '" + action + "'");
      }
      var promise = $http({
        method: 'POST',
        url: '/predictors/command/' + action + '/' + predictor_id
      }).then(function (res) {
        return res.data;
      });
      return promise;
    }

  }
})();