(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('AnalysisRest', AnalysisRest);

  /** @ngInject */
  function AnalysisRest(ModelRest) {
    var Analysis = function () {};
    var BASE_URL = '/analyzers';

    Analysis.prototype = new ModelRest(BASE_URL);

    Analysis.prototype.list = function() {
      this.setUrl(BASE_URL);
      return this.get();
    };

    Analysis.prototype.run = function(params) {
      this.setUrl(BASE_URL);
      return this.post(params);
    };

    Analysis.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    Analysis.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    Analysis.prototype.stop = function(id) {
      this.setUrl([BASE_URL, id, 'stop'].join('/'));
      return this.post();
    };

    return Analysis;
  }
})();