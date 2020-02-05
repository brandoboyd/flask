(function () {
  'use strict';

  var dependencies = [
    'omni',
    'ui.router'
  ];
  angular
    .module('omni.journeys', dependencies)
    .run(
      function ($rootScope, $state, $stateParams) {
        // It's very handy to add references to $state and $stateParams to the $rootScope
        // so that you can access them from any scope within your applications.For example,
        // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
        // to active whenever 'contacts.list' or one of its decendents is active.
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;
      })
    .config(function ($stateProvider, $urlRouterProvider) {
      $urlRouterProvider.when("", "details");
      $urlRouterProvider.when("/", "details");
      // For any unmatched url, send to /route1
      $urlRouterProvider.otherwise("details");
      $stateProvider
        .state('journeys', {
          abstract: true,
          url: '/',
          template: '<ui-view/>'
        })
        .state('journeys.details', {
          url: 'details',
          templateUrl: '/omni/partials/journeys/details',
          //template: "<p>Details</p>",
          controller: 'JourneysDetailsCtrl'
        })
        .state('journeys.details.distribution', {
          url: '/filter/:filterName/:filterValue'
        })
        .state('journeys.details.trends', {
          url: '/filter/:filterName/:filterValue/:timestamp/:drilldown'
        })
        .state('journeys.details.flow', {
          abstract: true
        })
        .state('journeys.details.flow.link', {
          url: '/filter/:sourceName/:targetName/:step/:filterName/:filterValue'
        })
        .state('journeys.details.flow.stage', {
          url: '/filter/:stage/:step'
        })
        .state('journeys.details.mcp', {
          url: '/filter/:stagePaths'
        })
        .state('journeys.trends', {
          url: 'trends',
          templateUrl: '/omni/partials/journeys/trends',
          controller: 'JourneysTrendsCtrl'
        })
        .state('journeys.distribution', {
          url: 'distribution',
          templateUrl: '/omni/partials/journeys/distribution',
          controller: 'JourneysDistributionCtrl'
        })
        .state('journeys.flow', {
          url: 'flow',
          templateUrl: '/omni/partials/journeys/flow',
          controller: 'JourneysFlowCtrl'
        })
        .state('journeys.crosstab', {
          url: 'crosstab',
          templateUrl: '/omni/partials/journeys/crosstab',
          controller: 'JourneysCrosstabCtrl'
        })
        .state('journeys.crossfilter', {
          url: 'crossfilter',
          templateUrl: '/omni/partials/journeys/crossfilter',
          controller: 'JourneysCrossfilterCtrl'
        })
        .state('journeys.funnels', {
          url: 'funnels',
          templateUrl: '/omni/partials/journeys/funnels',
          controller: 'JourneysFunnelsCtrl'
        })
        .state('journeys.reports', {
          url: 'reports?id',
          templateUrl: '/omni/partials/journeys/reports',
          controller: 'JourneysReportsCtrl'
        })
        .state('journeys.details.search', {
          url: '/search/{period}/{channels}/{smart_tags}/{journey_type}/{status}/{customer_segments}'
        })
        .state('journeys.trends.search', {
          url: '/search/{period}/{channels}/{smart_tags}/{journey_type}/{status}/{customer_segments}'
        })
        .state('journeys.distribution.search', {
          url: '/search/{period}/{channels}/{smart_tags}/{journey_type}/{status}/{customer_segments}'
        })
        .state('journeys.path', {
          url: 'path',
          templateUrl: '/omni/partials/journeys/path',
          controller: 'JourneysPathAnalysisCtrl'
        })
    });
})();
