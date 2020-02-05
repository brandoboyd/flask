(function () {
  'use strict';

  angular.module('predictors', [
      'ui.router',
      'angular-svg-round-progress',
      'xeditable',

      'slr.components'
    ])
    .config(function ($stateProvider, $urlRouterProvider) {
      $urlRouterProvider.when("", "trend");
      $urlRouterProvider.when("/", "trend");
      $urlRouterProvider.otherwise("trend");

      $stateProvider
        .state('predictors', {
          abstract: true,
          url: '/',
          template: '<ui-view/>'
        })
        .state('predictors.trend', {
          url: 'trend',
          templateUrl: '/predictors/partials/trend',
          controller: 'PredictorTrendCtrl'
        })
        .state('predictors.distribution', {
          url: 'distribution',
          templateUrl: '/predictors/partials/distribution',
          controller: 'PredictorDistributionCtrl'
        })
        .state('predictors.details.distribution', {
          url: '/filter/:filterName/:filterValue'
        })
        .state('predictors.details.trends', {
          url: '/filter/:filterName/:filterValue/:timestamp/:drilldown'
        })
        .state('predictors.details', {
          url: 'details',
          templateUrl: '/predictors/partials/details',
          controller: 'PredictorDetailsCtrl'
        })
        .state('predictors.reports', {
          url: 'reports?id',
          templateUrl: '/predictors/partials/reports',
          controller: 'PredictorReportsCtrl'
        })
    })
    .value('uiJqConfig', {
      tooltip: {
        animation: false,
        placement: 'bottom',
        container: 'body'
      }
    })
})();