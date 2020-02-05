(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('JourneysRest', JourneysRest);

  /** @ngInject */
  function JourneysRest(ModelRest) {
    var Journeys = function () {};
    var BASE_URL = '/journeys';

    Journeys.prototype = new ModelRest(BASE_URL);

    Journeys.prototype.mcp = function(params) {
      this.setUrl([BASE_URL, 'mcp'].join('/'));
      return this.post(params);
    };

    return Journeys;
  }
})();