(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/journey_tags', {
          templateUrl: '/partials/journey/tag/list',
          controller: 'JourneyTagListCtrl',
          name: 'journey_tags'
        })
        .when('/journey_tags/edit/:id?', {
          templateUrl: '/partials/journey/tag/edit',
          controller: 'CreateEditJourneyTagCtrl',
          name: 'journey_tags'
        })
    })
})();