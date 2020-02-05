(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('SmartTagsRest', SmartTagsRest);

  /** @ngInject */
  function SmartTagsRest(ModelRest) {
    var BASE_URL = '/smart_tags';
    var SmartTags = function () {
      this.listUrl = [BASE_URL, 'json'].join('/')
    };

    SmartTags.prototype = new ModelRest(BASE_URL);

    SmartTags.prototype.list = function(params) {
      this.setUrl(this.listUrl);
      return this.get(params);
    };

    SmartTags.prototype.action = function(action, params) {
      this.setUrl([BASE_URL, action, 'json'].join('/'));
      return this.post(params);
    };

    return SmartTags;
  }
})();