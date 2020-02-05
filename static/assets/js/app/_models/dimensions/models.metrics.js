(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('MetricsRest', MetricsRest);

  /** @ngInject */
  function MetricsRest(ModelRest) {
    var Metrics = function() {}; // TODO: this end-point does not exist for time being
    var BASE_URL = '/journeys';

    Metrics.prototype = new ModelRest(BASE_URL);

    Metrics.prototype.list = function() {
      this.get();
    };

    return Metrics;
  }
})();