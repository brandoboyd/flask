(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('ChannelsService', ChannelsService);

  /** @ngInject */
  function ChannelsService($rootScope, $q, ChannelsRest) {
    var _ChannelsRest = new ChannelsRest();
    var ChannelsService = {};

    var channels = [];
    var selected_channel = null;

    ChannelsService.ON_CHANNELS_LOADED = 'on_channels_load';
    ChannelsService.ON_CHANNELS_FAILED = 'on_channels_load_fail';
    ChannelsService.ON_CHANNELS_SELECTED = 'on_channels_selected';
    ChannelsService.ON_BOOKMARK_LOADED = 'on_bookmark_loaded';

    ChannelsService.load = function (type, serviced_only, parent_names) {
      _ChannelsRest.loadChannelsByType({
        type: type,
        serviced_only: serviced_only,
        parent_names: parent_names
      }).success(function (res) {
        channels = res.list;
        selected_channel = res.list[0];
        $rootScope.$broadcast(ChannelsService.ON_CHANNELS_LOADED, res);
      })
        .error(function onError(res) {
          $rootScope.$broadcast(ChannelsService.ON_CHANNELS_FAILED, res);
        });
    };

    // same as above only return promise object here
    ChannelsService.getAll = function (type, serviced_only, parent_names) {
      var deferred = $q.defer();
      var params = {
        type: type,
        serviced_only: serviced_only,
        parent_names: parent_names
      };
      _ChannelsRest.loadChannelsByType(params)
        .success(function (res) {
          channels = res.list;
          selected_channel = selected_channel ? selected_channel : res.list[0];
          deferred.resolve(channels);
        });
      
      return deferred.promise;
    };

    ChannelsService.getList = function () {
      return channels;
    };

    ChannelsService.setDefault = function (channel) {
      _ChannelsRest.setSelected(channel);
    };

    ChannelsService.setSelected = function (channel) {
      selected_channel = channel;
      $rootScope.$broadcast(ChannelsService.ON_CHANNELS_SELECTED);
    };

    ChannelsService.getSelected = function () {
      return selected_channel;
    };

    ChannelsService.getSelectedId = function () {
      return selected_channel ? selected_channel.id : null;
    };

    ChannelsService.getType = function () {
      return selected_channel.type;
    };

    return ChannelsService;
  }
})();