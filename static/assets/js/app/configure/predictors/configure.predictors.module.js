(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/predictors', {
          templateUrl: '/partials/predictors/list',
          controller: 'PredictorsCtrl',
          name: 'predictors'
        })
        .when('/predictors/:new_or_id', {
          templateUrl: '/partials/predictors/new_predictor',
          controller: 'NewPredictorCtrl',
          name: 'predictors'
        })
        .when('/predictors_v2/:new_or_id', {
          templateUrl: '/partials/predictors/new_predictor_v2',
          controller: 'NewPredictorV2Ctrl',
          name: 'predictors'
        })
        .when('/predictors/:id/detail', {
          templateUrl: '/partials/predictors/view',
          controller: 'PredictorsViewCtrl',
          name: 'predictors'
        })
        .when('/predictors/:predictorId/models/', {
          templateUrl: '/partials/predictors/models/list',
          controller: 'PredictorModelListController',
          name: 'predictors'
        })
        .when('/predictors/:predictorId/models/edit/:id?/', {
          templateUrl: '/partials/predictors/models/edit',
          controller: 'CreateEditPredictorsModelCtrl',
          name: 'predictors'
        })
    })
})();