(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('EventTypesRest', EventTypesRest);

  /** @ngInject */
  function EventTypesRest(ModelRest) {
    var EventTypes = function () {};
    var BASE_URL = '/event_type';

    EventTypes.prototype = new ModelRest(BASE_URL);

    EventTypes.prototype.list = function(channel_type_id) {
      if (channel_type_id) {
        this.setUrl([BASE_URL, 'list?channel_type_id=' + channel_type_id].join('/'));
      } else {
        this.setUrl([BASE_URL, 'list'].join('/'));
      }
      return this.get();
    };

    EventTypes.prototype.getOne = function(name) {
      this.setUrl([BASE_URL, 'get', name].join('/'));
      return this.get();
    };

    EventTypes.prototype.updateSchema = function (name, params) {
      this.setUrl([BASE_URL, 'update_schema', name].join('/'));
      return this.post(params);
    };

    EventTypes.prototype.applySchema = function (name) {
      this.setUrl([BASE_URL, 'sync/apply', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.acceptSchema = function (name) {
      this.setUrl([BASE_URL, 'sync/accept', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.cancelSchema = function (name) {
      this.setUrl([BASE_URL, 'sync/cancel', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.delete = function(name) {
      this.setUrl([BASE_URL, 'delete', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.create = function (params) {
      this.setUrl([BASE_URL, 'create'].join('/'));
      return this.post(params);
    };

    EventTypes.prototype.importData = function(params) {
      this.setUrl([BASE_URL, 'import_data'].join('/'));

      var formData = new FormData();
      if (params.name) {
        formData.append('name', params.name);
      }
      if (params.file) {
        formData.append('file', params.file);
      }
      if (params.sep) {
        formData.append('sep', params.sep);
      }
      if (params.channel_id) {
        formData.append('channel_id', params.channel_id);
      }

      return this.request({
        method: 'POST',
        data: formData,
        transformRequest: angular.identity,
        headers: { 'Content-Type': undefined }
      });
    };

    EventTypes.prototype.discoverSchema = function(params) {
      this.setUrl([BASE_URL, 'discover_schema'].join('/'));

      var formData = new FormData();
      if (params.name) {
        formData.append('name', params.name);
      }
      if (params.file) {
        formData.append('file', params.file);
      }
      if (params.sep) {
        formData.append('sep', params.sep);
      }

      return this.request({
        method: 'POST',
        data: formData,
        transformRequest: angular.identity,
        headers: { 'Content-Type': undefined }
      });
    };

    return EventTypes;
  }
})();