(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('JourneyFunnelsRest', JourneyFunnelsRest);

  /** @ngInject */
  function JourneyFunnelsRest(ModelRest) {
    var JourneyFunnels = function () {};
    var BASE_URL = '/funnels';

    JourneyFunnels.prototype = new ModelRest(BASE_URL);

    JourneyFunnels.prototype.list = function() {
      return this.get();
    };

    JourneyFunnels.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    JourneyFunnels.prototype.save = function(params, isEditMode) {
      // Edit mode doesn't accept 'POST' request.
      if (isEditMode) {
        return this.put(params);
      } else {
        return this.post(params);
      }
    };
    
    JourneyFunnels.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    return JourneyFunnels;
  }
})();