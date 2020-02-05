(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory("selectedPredictorsService", selectedPredictorsService);

  /** @ngInject */
  function selectedPredictorsService() {
    var selected = [];
    return {
      setSelected: function (predictors) {
        selected = predictors;
      },
      getSelected: function () {
        return selected
      }
    };
  }
})();