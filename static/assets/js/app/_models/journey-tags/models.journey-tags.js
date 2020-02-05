(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('JourneyTagsRest', JourneyTagsRest);

  /** @ngInject */
  function JourneyTagsRest(ModelRest) {
    var JourneyTags = function () {};
    var BASE_URL = '/journey_tags';

    JourneyTags.prototype = new ModelRest(BASE_URL);

    JourneyTags.prototype.list = function() {
      return this.get();
    };

    JourneyTags.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    JourneyTags.prototype.save = function(params) {
      return this.post(params);
    };

    JourneyTags.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    return JourneyTags;
  }
})();