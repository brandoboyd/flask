(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysTrendsCtrl', JourneysTrendsCtrl);

  /** @ngInject */
  function JourneysTrendsCtrl($scope, $rootScope, $http, $state, FilterService) {

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

      var active_group_by = $scope.getActiveFilter($scope.group_by_options);

      _.each($scope.group_by_options, function (item) {
        if (item.value === active_group_by) {
          $scope.group_by_options[0].active = false;
          item.active = true;
        }
      });

      buildTrendsPlot(data);

    }, 500);


    var buildTrendsPlot = function (data) {
      data.plot_type = 'timeline';
      data.group_by = $scope.getActiveFilter($scope.group_by_options);
      data.computed_metric = $scope.getActiveFilter($scope.metric_options);
      data.level = _.indexOf(['today', 'yesterday'], FilterService.getSelectedDateRangeAlias()) !== -1 ? 'hour' : 'day';

      $http.post('/journeys/plots', data).success(function (res) {
        //data for charts directive
        $scope.loading = false;
        $scope.data = res.list;
        $scope.extra_settings = _.extend(data, {
          drilldownEnabled: true,
          chart_type: 'LINE',
          target: 'OMNI',
          yAxisFormat: $scope.getYAxisFormat('TRENDS'),
          active_filter: $scope.getActiveFilterName($scope.group_by_options)
        });
      })
    }

    $scope.buildPlot();

    //drill down triggered from charts directive
    $rootScope.$on('journeys.details.trends', function (event, params) {
      $state.go('journeys.details.trends', params)
    })

  }
})();
