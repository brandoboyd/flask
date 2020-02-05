(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysDistributionCtrl', JourneysDistributionCtrl);

  /** @ngInject */
  function JourneysDistributionCtrl($scope, $rootScope, $http, $state) {
    $scope.$on("ON_JOURNEY_FACETS_UPDATE", function () {
      $scope.buildPlot();
    });

    var init = function () {
      $scope.loading = true;
      angular.element('#analysis').hide();
    };

    init();

    $scope.buildPlot = _.debounce(function () {
      $scope.loading = true;
      var data = $scope.getJourneySearchParams();
      buildDistributionPlot(data);
    }, 500);


    var buildDistributionPlot = function (data) {
      data.plot_type = 'avg_distributions';
      data.group_by = $scope.getActiveFilter($scope.group_by_options);
      data.computed_metric = $scope.getActiveFilter($scope.metric_options);
      //data.level     = 'day';

      $http.post('/journeys/plots', data).success(function (res) {
        $scope.data = res.list;
        $scope.loading = false;
        $scope.extra_settings = _.extend(data, {
          drilldownEnabled: true,
          chart_type: 'PIE',
          target: 'OMNI',
          valueFormat: $scope.getYAxisFormat('DISTRIBUTION'),
          active_filter: $scope.getActiveFilterName($scope.group_by_options)
        });
      })
    };

    $scope.buildPlot();

    //drill down triggered from charts directive
    $rootScope.$on('journeys.details.distribution', function (event, params) {
      $state.go('journeys.details.distribution', params)
    })
  }
})();
