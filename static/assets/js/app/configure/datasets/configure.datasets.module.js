(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/datasets', {
          templateUrl: '/partials/datasets/list',
          controller: 'DatasetsListCtrl',
          name: 'datasets'
        })
        .when('/datasets/edit/:name*', {
          templateUrl: '/partials/datasets/edit',
          controller: 'EditDatasetsCtrl',
          name: 'datasets'
        })
    })
})();