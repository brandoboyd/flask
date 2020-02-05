(function() {
  'use strict';

  angular.module('jobs')
    .config(jobsAppConfig);

  function jobsAppConfig($stateProvider, $urlRouterProvider) {
    $urlRouterProvider.when('', 'reports');
    $urlRouterProvider.when('/', 'reports');
    $urlRouterProvider.otherwise('reports');

    $stateProvider
      .state('jobs', {
        abstract    : true,
        url         : '/',
        template    : '<ui-view/>',
      })

      .state('jobs.reports', {
        url         : 'reports?wid',
        templateUrl : '/jobs/partials/reports.tab',
        controller  : 'JobReportsCtrl',
        controllerAs: 'vm',
      })

      .state('jobs.details', {
        url         : 'details',
        templateUrl : '/jobs/partials/details.tab',
        controller  : 'JobDetailsCtrl',
        controllerAs: 'vm',
      })
  }
})();