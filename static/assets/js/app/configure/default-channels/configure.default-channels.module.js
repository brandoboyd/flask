(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
    $routeProvider
      .when('/outbound_channels/', {
        templateUrl: '/partials/configure/outbound_channels',
        controller: 'OutboundChannelsCtrl',
        name: 'profile_channels',
        title: 'User Profile - Default Channels'
      })
      .when('/outbound_channels/:acct_id', {
        templateUrl: '/partials/configure/outbound_channels',
        controller: 'OutboundChannelsCtrl',
        name: 'account_channels',
        title: 'Account - Default Channels'
      })
  })
})();