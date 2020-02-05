(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/event_types', {
          templateUrl: '/partials/event-types/list',
          controller: 'EventTypesListCtrl',
          name: 'event_types'
        })
        .when('/event_types/edit/:name', {
          templateUrl: '/partials/event-types/edit',
          controller: 'EditEventTypeCtrl',
          name: 'event_types'
        })
    })
})();