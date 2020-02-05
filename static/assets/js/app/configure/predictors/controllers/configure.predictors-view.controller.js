(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PredictorsViewCtrl', PredictorsViewCtrl);

  /** @ngInject */
  function PredictorsViewCtrl($scope, $routeParams, PredictorsRest) {
    var Predictors = new PredictorsRest();

    $scope.contextTable = {
      sort: {
        predicate: 'feature',
        reverse: false
      }
    };
    $scope.actionTable = {
      sort: {
        predicate: 'feature',
        reverse: false
      }
    };

    Predictors.getPredictorDetails($routeParams.id).success(function (res) {
      function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
      }

      $scope.predictor = res;

      // Capitalize the first letter of feature description
      _.each($scope.predictor.context_features, function (feature) {
        feature.description = capitalizeFirstLetter(feature.description);
      });
      _.each($scope.predictor.action_features, function (feature) {
        feature.description = capitalizeFirstLetter(feature.description);
      });
    });
  }
})();