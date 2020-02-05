(function () {
  'use strict';

  var dependencies = [
    'omni',
    'ui.router',
  ];
  angular.module('omni.customers', dependencies)
    .run(function ($rootScope, $state, $stateParams) {
      // It's very handy to add references to $state and $stateParams to the $rootScope
      // so that you can access them from any scope within your applications.For example,
      // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
      // to active whenever 'contacts.list' or one of its decendents is active.
      $rootScope.$state = $state;
      $rootScope.$stateParams = $stateParams;
    })

    .config(function ($stateProvider, $urlRouterProvider, $locationProvider) {
      $urlRouterProvider.when("", "details");
      $urlRouterProvider.when("/", "details");

      // For any unmatched url, send to /route1
      $urlRouterProvider.otherwise("details");

      $stateProvider
        .state('customers', {
          abstract: true,
          url: '/',
          template: '<ui-view/>'
        })
        .state('customers.details', {
          url: 'details',
          templateUrl: '/omni/partials/customers/details',
          //template: "<p>Details</p>",
          controller: 'CustomersDetailsCtrl'
        })

        .state('customers.details.distribution', {
          url: '/filter/:filterName/:filterValue'
        })

        .state('customers.distribution', {
          url: 'distribution',
          templateUrl: '/omni/partials/customers/distribution',
          controller: 'CustomersDistributionCtrl'
        })
    });

})();
