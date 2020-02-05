(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('CompoundChannelService', CompoundChannelService);

  /** @ngInject*/
  function CompoundChannelService($rootScope, ChannelsRest) {
    var _ChannelsRest = new ChannelsRest();
    var sharedService = {
      compound: null,
      LOADED: "ChannelsLoadedEvent",
      CHANGED: "PrimitiveChannelsListChanged",
      channels: [],
      channelsOptions: [],
      channelsByPlatform: {},
      channelsById: {},
      channelsByDispatchability: {}
    };

    var pluckChannelData = function (item) {
      return {
        id: item.id,
        title: item.title
      }
    };

    sharedService.isReady = function () {
      return !!sharedService.channels.length;
    };

    sharedService.prepare = function () {
      if (sharedService.isReady()) {
        $rootScope.$broadcast(sharedService.LOADED);
        return;
      }

      var res = _ChannelsRest.fetchChannels({primitive: true}, function () {
        sharedService.channels = res.list;
        sharedService.channelsOptions = _.map(sharedService.channels, pluckChannelData);
        sharedService.channelsByPlatform = _.groupBy(sharedService.channels, 'platform');
        sharedService.channelsById = _.groupBy(sharedService.channels, 'id');
        sharedService.channelsByDispatchability = _.groupBy(sharedService.channels, 'is_dispatchable');
        $rootScope.$broadcast(sharedService.LOADED);
      });
    };

    sharedService.setCompound = function (channel) {
      if (channel.is_compound || channel.is_service) {
        sharedService.compound = channel;
      }
    };

    sharedService.primitivesChanged = function (data) {
      $rootScope.$broadcast(sharedService.CHANGED, data);
    };

    sharedService.filterOptionsByPlatform = function (options, force, dispatchable) {
      //filter channel options by platform of the first channel in the selected list
      if (options.selected.length == 0) {
        if (arguments.length <= 2) {
          options.options = sharedService.channelsOptions;
        } else {
          options.options = _.map(sharedService.channelsByDispatchability[dispatchable], pluckChannelData);
        }
      } else if (options.selected.length == 1 || force) {
        // show channels of all available platforms
        var selected = options.selected[0],
          channel = sharedService.channelsById[selected][0],
          platform = channel.platform,
          is_dispatchable = channel.is_dispatchable; // should equal dispatchable

        var channels = sharedService.channelsByPlatform[platform];
        if (arguments.length == 3) {
          channels = _.filter(channels, function (item) {
            return item.is_dispatchable === dispatchable;
          });
        }

        options.options = _.map(channels, pluckChannelData);
      }
      return options;
    };

    return sharedService;
  }
})();