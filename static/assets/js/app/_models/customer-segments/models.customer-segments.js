(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('CustomerSegmentsRest', CustomerSegmentsRest);

  /** @ngInject */
  function CustomerSegmentsRest(ModelRest) {
    var CustomerSegments = function () {};
    var BASE_URL = '/api/customer_segments';

    CustomerSegments.prototype = new ModelRest(BASE_URL);

    CustomerSegments.prototype.list = function() {
      return this.get();
    };

    CustomerSegments.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    CustomerSegments.prototype.save = function(params) {
      return this.post(params);
    };

    CustomerSegments.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    return CustomerSegments;
  }
})();