(function () {
  'use strict';
  angular
    .module('predictors')
    .controller('PredictorsTabCtrl', PredictorsTabCtrl);

  /** @ngInject */
  function PredictorsTabCtrl($scope, $stateParams, PredictorService, MetadataService, WidgetService, AccountsService, FilterService, AnalysisService) {
    var PR_REPORTS_SREF = 'predictors.reports';

    var Apps = MetadataService.getApps();
    var debouncedRender = _.debounce(render, 200);
    var off = [];

    var init = function () {
      $scope.currentDate = FilterService.getSelectedDateRangeName();
      $scope.currentTab = "";
      $scope.dateRange = FilterService.getDateRange();
      $scope.drilledDateRange = {};
      $scope.facets = {
        predictors: {
          selected: null
        },
        ab_testing: {
          is_predicted : true
        }
      };

      $scope.analysis = {
        filters: {},
        params: {}
      };

      $scope.flags = {
        loaded: false
      };
      $scope.metric = {};
      $scope.predictors = [];
      $scope.tab_options = [
        {name: 'Trend', sref: 'predictors.trend', class: 'icon-bar-graph-variable-2'},
        {name: 'Distribution', sref: 'predictors.distribution', class: 'icon-agent-status-ready-partial'},
        {name: 'Details', sref: 'predictors.details', class: 'icon-view-lists'},
        {name: 'Reports', sref: PR_REPORTS_SREF, class: 'icon-doc-report-b'}
      ];

      PredictorService.getAllPredictors()
        .then(function (response) {
          $scope.flags.loaded = true;
          if (!response.list.length) {
            return;
          }

          $scope.predictors = response.list;

          $scope.facets.predictors.all = false;
          $scope.facets.predictors.list = 
            _($scope.predictors)
              .map(function(p) {
                return { id: p.id, display_name: p.name, enabled: false };
              })
              .value();

          $scope.facets.predictors.selected = $scope.predictors[0].id;
          $scope.facets.predictors.list[0].enabled = true;

          initializeWidget();
        });

      AnalysisService.fetchReports(PR_REPORTS_SREF);  // should HTTP GET once per section
    };

    /** Analysis */
    $scope.getAnalysisFilters = function () {
      return $scope.getMetricParams();
    };

    $scope.getAnalysisExtraParams = function () {
      $scope.predictor.metric_type = $scope.predictor.reward_type;
      return {
        metrics: [{
          metric: $scope.predictor.metric,
          metric_values: $scope.predictor.metric_values || [],
          metric_type: $scope.predictor.reward_type, // TODO[sabr]: rename to metric_type
          metric_values_range: $scope.predictor.metric_values_range || [0, 1000]
        }],
        application: Apps.PRR,
        sref: PR_REPORTS_SREF
      };
    };

    /** Facet */
    function render() {
      $scope.$broadcast('FACETS_CHANGED');
      updateAnalysisParams();
    }

    $scope.updateFacets = function() {
      debouncedRender();
    };
    
    $scope.setFilter = function (groupings, value) {
      _.each(groupings, function (item) {
        item.active = (item.value === value);
      });
      $scope.plot_by = value;
      debouncedRender();
    };

    $scope.resetDrilledDateRange = function () {
      if (!$scope.predictor) return;
      $scope.drilledDateRange.status = false;
      $scope.drilledDateRange.from = null;
      $scope.drilledDateRange.to = null;
      $scope.drilledDateRange.level = null;
      debouncedRender();
    };

    $scope.selectPredictor = function () {
      // Disable 'All Predictors' checkbox
      if ($scope.facets.predictors.all) {
        $scope.facets.predictors.all = false;
        $scope.facets.predictors.selected = $scope.predictor.id;
        _.each($scope.facets.predictors.list, function (facet) {
          if (facet.id == $scope.predictor.id) {
            facet.enabled = true;
          }
        });
        return;
      }

      getFacets();
      updateAnalysisParams();
    };

    function updateAnalysisParams() {
      if (!$scope.predictor) return;
      $scope.analysis.params = $scope.getAnalysisExtraParams();
      $scope.analysis.filters = $scope.getAnalysisFilters();
      // $scope.getAnalysisFilters();
      // $scope.getAnalysisExtraParams();
    }

    function getPlotType() {
      if ($scope.currentTab === 'trend') {
        return 'time';
      } else if ($scope.currentTab === 'distribution') {
        return 'distribution';
      }
      return null;
    }

    function getChartType() {
      if ($scope.currentTab === 'trend') {
        return 'LINE';
      } else if ($scope.currentTab === 'distribution') {
        return 'PIE';
      }
      return null;
    }

    function getFacets() {
      $scope.predictor = _.find($scope.predictors, {id: $scope.facets.predictors.selected});
      $scope.metricParams = $scope.getMetricParams();

      if (!$scope.predictor) return;

      var reward;
      if (_.has($scope.predictor, 'configuration')) {
        reward = _.find($scope.predictor.configuration.rewards, {var_name: $scope.predictor.reward});
      }
      _.extend($scope.facets,
        _.pick(PredictorService.predictorFacets[$scope.predictor.id],
          ['action_vector', 'context_vector', 'models']));

      if (!reward) {
        reward = {};
        reward.display_name = $scope.predictor.metric;
        reward.description = $scope.predictor.reward_type;
        reward.display_name = $scope.predictor.metric;
      }

      _.extend($scope.metric, {
        display_name: reward.display_name || $scope.predictor.metric,
        description: reward.description || $scope.predictor.reward_type,
        label: reward.display_name || $scope.predictor.metric,
        active: false,
        value: 'reward'
      });

      $scope.$broadcast('SELECT_PREDICTOR');
    }

    $scope.getMetricParams = function() {
      if (!$scope.predictor) return;

      function _getFacetParams(facet_options) {
        var params = {};
        _.each(facet_options, function (item, key) {
          var options = _.filter(item.list, {enabled: true});
          params[key] = options.length ? _.pluck(options, 'display_name') : [];
        });
        return params;
      }

      var level = FilterService.getSelectedGraphLevel();

      if ($stateParams && $stateParams.timestamp) {
        var from_ts = parseInt($stateParams.timestamp);
        var to_ts = moment.utc(from_ts).startOf(level).add(level, 1).valueOf();

        var from = moment.utc(from_ts).format('MM/DD/YYYY');
        var to = moment.utc(to_ts).format('MM/DD/YYYY');
      } else {
        var from = $scope.dateRange.from;
        var to = $scope.dateRange.to;
      }

      return {
        predictor_id: $scope.predictor.id,
        models: ($scope.facets.models) ? _($scope.facets.models.list).filter(function (item) {
          return item.enabled
        }).pluck('id').value() : [],
        plot_type: getPlotType(),
        plot_by: $scope.plot_by,
        from: from,
        to: to,
        level: level,
        request_url: '/predictors/facets/json',  // required for zooming and 'Add to Dashboard' settings
        action_vector: _getFacetParams($scope.facets.action_vector),
        context_vector: _getFacetParams($scope.facets.context_vector),
        ab_testing :  $scope.facets.ab_testing.is_predicted.toString()
      };
    };

    /** Widget */
    function locationChanged() {
      var w = $scope.widget;
      if (w.removing) {
        return;
      }
      WidgetService.loadFromLocation();
    }

    function loadWidgetSettings() {
      var w = $scope.widget.item;
      if (!w || !w.settings) {
        return;
      }

      var settings = w.settings;
      // Load date range
      if (settings.from && settings.to) {
        FilterService.updateDateRange({
          from: moment.utc(settings.from),
          to  : moment.utc(settings.to)
        });
      }

      $scope.dateRange = FilterService.getDateRange();
      $scope.currentDate = FilterService.getSelectedDateRangeName();

      // Load Predictor
      $scope.facets.predictors.selected = settings.predictor_id;
      _.each($scope.facets.predictors.list, function(p) {
        p.enabled = p.id === settings.predictor_id;
      });

      $scope.plot_by = settings.plot_by; // Load plot_by before SELECT_PREDICTOR broadcast
      $scope.selectPredictor();

      // Load predictor models, ab_testing
      _.each($scope.facets.models.list, function(m) {
        m.enabled = (settings.models.indexOf(m.id) > -1);
      });
      $scope.facets.ab_testing.is_enabled = (settings.ab_testing === 'true');

      // Load action feature and context features
      _.each($scope.facets.action_vector, function(vector, key) {
        $scope.facets.action_vector[key].all = false;
        _.each(vector.list, function(f) {
          f.enabled = (settings.action_vector[key].indexOf(f.display_name) > -1);
        });
      });
      _.each($scope.facets.context_vector, function(vector, key) {
        $scope.facets.context_vector[key].all = false;
        _.each(vector.list, function(f) {
          f.enabled = (settings.context_vector[key].indexOf(f.display_name) > -1);
        });
      });
    }

    function initializeWidget() {
      $scope.widget = {
        removing: false,
        updating: false,
        item: null,
        getParams: function () {
          return {
            settings: $scope.getMetricParams(),
            extra_settings: {
              request_url   : '/predictors/facets/json',
              source        : '/predictors#/' + $scope.currentTab + '?wid=',
              predictor_id  : $scope.predictor && $scope.predictor.id,
              target        : 'PREDICTORS',
              directive     : 'chart',
              chart_type    : getChartType(),
              isMetric      : true,
              level         : $scope.metricParams.level,
              yAxisLabel    : $scope.metric.display_name,
              yAxisFormat   : ',.2f',
              numberFormat  : 'float',
              account_info  : AccountsService.getCompactAccount()
            }
          };
        },
        setup: function (w) {
          if ($scope.widget.updating) {
            $scope.widget.updating = false;
          }
          if (!w || _.isEmpty(w)) {
            return;
          }

          loadWidgetSettings();
          // $scope.$broadcast('setupFacets', w);
        }
      };

      $scope.widget["remove"] = WidgetService.makeRemove($scope.widget, 'removing');

      off.push($scope.$watch('widget.item', $scope.widget.setup));
      off.push($scope.$watch('location.search()', locationChanged));
      off.push($scope.$on(WidgetService.CHANGED, function (evt, data) {
        var w = $scope.widget;
        w.updating = true;
        w.item = data.widget;
      }));
    }

    /** Watchers */
    off.push($scope.$watch('facets.predictors.selected', function (nVal, oVal) {
      if (nVal && nVal !== oVal) {
        $scope.selectPredictor();
      }
    }));

    off.push($scope.$watch('facets.ab_testing.is_predicted', function() {
      $scope.updateFacets();
    }, true));

    off.push($scope.$watch('plot_by', function(nVal) {
      $scope.updateFacets();
    }, true));

    off.push($scope.$on('PLOT_BY_REQUEST', function(evt, cb) {
      cb($scope.plot_by);
    }));

    off.push($scope.$on('PLOT_BY_CHANGED', function(evt, newVal) {
      $scope.plot_by = newVal;
    }));

    off.push($scope.$on('$stateChangeSuccess',
      function (event, toState) {
        if (toState.name.indexOf('predictors.details') > -1) {
          $scope.currentTab = 'details';
        } else {
          $scope.currentTab = toState.name.replace('predictors.', '');
        }
      }
    ));

    off.push($scope.$on(FilterService.DATE_RANGE_CHANGED, function () {
      $scope.resetDrilledDateRange();
    }));

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
