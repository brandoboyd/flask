(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/schema_agent_profile', {
          templateUrl: '/partials/schema-profiles/index',
          controller: 'SchemaProfileCtrl',
          name: 'schema_agent_profile',
          resolve: {
            entityType: function() { return 'agent' }
          }
        })
        .when('/schema_customer_profile', {
          templateUrl: '/partials/schema-profiles/index',
          controller: 'SchemaProfileCtrl',
          name: 'schema_customer_profile',
          resolve: {
            entityType: function() { return 'customer' }
          }
        });
    })
})();