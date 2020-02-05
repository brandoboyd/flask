(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/journey_types/', {
          templateUrl: '/partials/journey/type/list',
          controller: 'JourneyTypeListCtrl',
          name: 'journey_types'
        })
        .when('/journey_types/edit/:id?/', {
          templateUrl: '/partials/journey/type/edit',
          controller: 'CreateEditJourneyTypeCtrl',
          name: 'journey_types'
        })
        .when('/journey_types/edit/:jtId/stage/:id?/', {
          templateUrl: '/partials/journey/stage/edit',
          controller: 'CreateEditJourneyStageCtrl',
          name: 'journey_types'
        })
    })
})();