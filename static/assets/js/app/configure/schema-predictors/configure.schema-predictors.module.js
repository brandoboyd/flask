(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/schema-predictors', {
          templateUrl: '/partials/schema-predictors/list',
          controller: 'SchemaPredictorsCtrl',
          name: 'schema-predictors'
        })
    })
})();