(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/channels', {
          templateUrl: '/partials/channels/list',
          controller: 'ChannelsListCtrl',
          name: 'channels'
        })
        .when('/new_channel', {
          templateUrl: '/partials/channels/new_channel2',
          controller: 'ChannelConfigureCtrl',
          name: 'channels'
        })

        .when('/new_channel/no-channels', {
          templateUrl: '/partials/channels/new_channel2',
          controller: 'ChannelConfigureCtrl',
          name: 'channels-no-channels'
        })

        .when('/update_channel/:channel_id', {
          templateUrl: '/partials/channels/update_channel',
          controller: 'UpdateChannelCtrl',
          name: 'channels'
        })
    })
})();