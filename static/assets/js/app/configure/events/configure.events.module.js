(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/events/all', {
          templateUrl: '/partials/events/events',
          controller: 'EventsCtrl',
          name: 'events'
        })
        .when('/event/view/:event_id', {
          templateUrl: '/partials/events/view',
          controller: 'EventViewCtrl',
          name: 'events'
        })
    })
})();