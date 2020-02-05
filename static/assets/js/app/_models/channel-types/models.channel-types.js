(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('ChannelTypesRest', ChannelTypesRest);

  /** @ngInject */
  function ChannelTypesRest($q, ModelRest) {
    var ChannelTypes = function () {};
    var BASE_URL = '/channel_type';

    ChannelTypes.prototype = new ModelRest(BASE_URL);

    ChannelTypes.prototype.list = function(params) {
      this.setUrl([BASE_URL, 'list'].join('/'));
      return this.get(params);
    };

    ChannelTypes.prototype.getOne = function(name) {
      this.setUrl([BASE_URL, 'get', name].join('/'));
      return this.get();
    };

    ChannelTypes.prototype.create = function (params) {
      this.setUrl([BASE_URL, 'create'].join('/'));
      return this.post(params);
    };

    ChannelTypes.prototype.update = function (name, params) {
      this.setUrl([BASE_URL, 'update', name].join('/'));
      return this.post(params);
    };

    ChannelTypes.prototype.applySync = function (name, params) {
      this.setUrl([BASE_URL, 'apply_sync', name].join('/'));
      return this.post();
    };

    ChannelTypes.prototype.delete = function (name) {
      this.setUrl([BASE_URL, 'delete', name].join('/'));
      return this.post();
    };

    return ChannelTypes;
  }
})();
