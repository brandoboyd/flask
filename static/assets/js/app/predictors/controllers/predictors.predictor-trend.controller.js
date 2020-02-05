(function () {
  'use strict';

  angular
    .module('predictors')
    .controller('PredictorTrendCtrl', PredictorTrendCtrl);

  /** @ngInject */
  function PredictorTrendCtrl($scope, $rootScope, $state, PredictorsTabRenderFactory) {
    var off = [];
    var debouncedRender = _.debounce(render, 200);

    //expose underscore to use in expressions
    $scope._ = _;

    var init = function () {
      $scope.distribGroupings = PredictorsTabRenderFactory.initGroupings($scope.facets);

      $scope.flags = {
        rendering: false
      };

      if (!$scope.predictor) {
        return
      }

      $scope.$emit('PLOT_BY_REQUEST', function cb(plot_by) {
        setActiveFilter(plot_by);
      });

      off.push($scope.$on('FACETS_CHANGED', function () {
        debouncedRender();
      }));
    };

    off.push($scope.$on('SELECT_PREDICTOR', function () {
      init();
    }));

    $scope.$watch('distribGroupings.length', function(nVal) {
      if(nVal && nVal > 0) {
        $scope.selectedDistribGrouping = $scope.distribGroupings[0];
      }
    });

    $scope.$watch('selectedDistribGrouping', function(nVal) {
      if(nVal) {
        $scope.setFilter($scope.distribGroupings, nVal.type)
      }
    });

    function setActiveFilter(filter) {
      var isOneSet = false; // track if at least one button is active
      _.each($scope.distribGroupings, function(item) {
        if (item.value === filter) {
          item.active = true;
          isOneSet = true;
        } else {
          item.active = false;
        }
      });

      if (!isOneSet) {
        var allButton = _.find($scope.distribGroupings, { value: 'all' });
        allButton.active = true;
        $scope.$emit('PLOT_BY_CHANGED', 'all');
      }
    }

    function render() {
      var attrs = {
        predictor: $scope.predictor,
        flags: $scope.flags,
        metric: $scope.metric,
        params: $scope.getMetricParams(),
        tab_options: $scope.tab_options
      };
      attrs.params.plot_type = 'time';
      attrs.chart_settings = {
        chart_type: 'LINE',
        drilldownEnabled: true,
        isMetric: true,
        level: attrs.params.level,
        target: 'PREDICTORS',
        yAxisLabel: attrs.metric.display_name || $scope.predictor.metric,
        active_filter: attrs.params.plot_by.toLowerCase()
      };
      if ($scope.predictor.reward_type === 'Boolean') {
        attrs.chart_settings.yAxisFormat = '.0f';
      } else {
        var yformat = 's';
        var max = $scope.predictor.metric_values_range[1];

        if (max <= 100) {
          yformat = '.0f';
        }

        attrs.chart_settings.yAxisFormat = yformat;
        attrs.chart_settings.yDomain = $scope.predictor.metric_values_range;
      }
      PredictorsTabRenderFactory.render(attrs, function (res) {
        $scope.charts = res.charts;
        $scope.flags = res.flags;
        $scope.tab_options = res.tab_options;
      });
    }

    $rootScope.$on('predictors.details.trends', function (event, params) {
      $state.go('predictors.details.trends', params)
    });

    var destructor = function () {
      off.forEach(function (unbind) {
        unbind();
      });
      off = null;
    };

    off.push($scope.$on('$destroy', destructor));
    init();
  }
})();
