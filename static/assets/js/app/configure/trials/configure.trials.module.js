(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/trials/', {
          templateUrl: '/partials/trials/list',
          controller: 'TrialsListCtrl',
          name: 'trials'
        })
        .when('/trials/edit/:id?/', {
          templateUrl: '/partials/trials/edit',
          controller: 'CreateUpdateTrialCtrl',
          name: 'trials.edit'
        })
    })
})();