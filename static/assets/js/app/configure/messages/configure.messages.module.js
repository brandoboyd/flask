(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/messages/all', {
          templateUrl: '/partials/messages/messages',
          controller: 'AllMessagesCtrl',
          name: 'messages'
        })
        .when('/messages/all/:channel_id', {
          templateUrl: '/partials/messages/messages',
          controller: 'AllMessagesCtrl',
          name: 'messages'
        })
        .when('/messages/edit', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
        .when('/messages/edit/:message_id', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
        .when('/messages/edit/:form_mode/:source_channel_id', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
        .when('/messages/edit/:form_mode/:message_id/:source_channel_id', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
    })
})();