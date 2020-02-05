(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/channel_types', {
          templateUrl: '/partials/channel-types/list',
          controller: 'ChannelTypesListCtrl',
          name: 'channel_types'
        })
        .when('/channel_types/edit/:name', {
          templateUrl: '/partials/channel-types/edit',
          controller: 'EditChannelTypeCtrl',
          name: 'channel_types'
        })
    })
})();