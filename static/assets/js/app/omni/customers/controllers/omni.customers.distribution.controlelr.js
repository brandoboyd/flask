(function () {
  'use strict';

  angular.module('omni.customers')
    .controller('CustomersDistributionCtrl', function ($scope, $rootScope, $http, $state) {
      $scope.$on("ON_CUSTOMER_FACETS_UPDATE", function () {
        $scope.buildPlot();
      });

      $scope.$on('customers.details.distribution', function(e, params) {
        $state.go('customers.details.distribution', params, {inherit: false})
      });

      $scope.buildPlot = _.debounce(function () {
        var data = $scope.getSearchParams();
        if ($scope.has_schema) {
          buildDistributionPlot(data);
        }
      }, 300);

      var buildDistributionPlot = function (data) {
        data.group_by = $scope.getActiveFilter($scope.plot_by_options);
        data.metric = 'count';

        $http.post('/facet-search/customer/distribution', data)
          .success(function (res) {
            $scope.extra_settings = {
              active_filter : $scope.getActiveFilterName($scope.plot_by_options),
              valueFormat   : ',.0d',
              target        : 'OMNI_CUSTOMERS',
              chart_type    : 'PIE',
              drilldownEnabled: true
            };
            $scope.chartData = _.map(res.data, function(item) {
              return {
                data: [item.value],
                label: item.label
              }
            });
          });
      };

      $scope.buildPlot();
    });

})();