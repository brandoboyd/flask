(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('ChannelsRest', ChannelsRest);

  /** @ngInject */
  function ChannelsRest(ModelRest) {
    var Channels = function () {
    };
    var BASE_URL = '/channels'; // todo: implement REST end-points in server

    Channels.prototype = new ModelRest(BASE_URL);

    Channels.prototype.list = function () {
      return this.get();
    };

    Channels.prototype.save = function (params) {
      return this.post(params);
    };

    // TODO: Methods below do not satisfy RESTful pattern, they are very specifc, and need to be refactored
    
    Channels.prototype.fetchChannels = function (params) {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.post(params);
    };

    var configureChannelUrl = '/configure/channel_update/json';
    Channels.prototype.getOne = function (id) {
      this.setUrl(configureChannelUrl + '?channel_id=' + id);
      return this.get();
    };

    Channels.prototype.updateConfigureChannel = function (params) {
      this.setUrl(configureChannelUrl);
      return this.post(params);
    };

    Channels.prototype.getConfigureChannels = function (params) {
      this.setUrl(configureChannelUrl);
      return this.get(params);
    };

    Channels.prototype.getChannelTypes = function () {
      this.setUrl('/configure/channel_types/json');
      return this.get();
    };

    var newChannelUrl = '/configure/channels/json';
    Channels.prototype.saveNewChannel = function (params) {
      this.setUrl(newChannelUrl);
      return this.post(params);
    };

    // from _commons/channels
    Channels.prototype.loadChannelsByType = function (params) {
      this.setUrl('/channels_by_type/json');
      return this.post(params);
    };

    return Channels;
  }
})();