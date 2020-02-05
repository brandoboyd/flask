(function () {
  'use strict';

  angular.module('predictors', [
      'ui.router',
      'angular-svg-round-progress',
      'xeditable',

      'slr.components'
    ])
    .config(["$stateProvider", "$urlRouterProvider", function ($stateProvider, $urlRouterProvider) {
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
    }])
    .value('uiJqConfig', {
      tooltip: {
        animation: false,
        placement: 'bottom',
        container: 'body'
      }
    })
})();
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
  PredictorsTabCtrl.$inject = ["$scope", "$stateParams", "PredictorService", "MetadataService", "WidgetService", "AccountsService", "FilterService", "AnalysisService"];
})();

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
  PredictorTrendCtrl.$inject = ["$scope", "$rootScope", "$state", "PredictorsTabRenderFactory"];
})();

(function () {
  'use strict';

  angular
    .module('predictors')
    .controller('PredictorDistributionCtrl', PredictorDistributionCtrl);

  /** @ngInject */
  function PredictorDistributionCtrl($scope, $rootScope, $state, PredictorsTabRenderFactory) {
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
      attrs.params.plot_type = 'distribution';
      attrs.chart_settings = {
        chart_type: 'PIE',
        drilldownEnabled: true,
        level: attrs.params.level,
        target: 'PREDICTORS',
        yAxisLabel: attrs.metric.label,
        valueFormat: ',.2f',
        active_filter: attrs.params.plot_by.toLowerCase()
      };
      PredictorsTabRenderFactory.render(attrs, function (res) {
        $scope.charts = res.charts;
        $scope.flags = res.flags;
        $scope.tab_options = res.tab_options;
      });
    }

    $rootScope.$on('predictors.details.distribution', function (event, params) {
      $state.go('predictors.details.distribution', params)
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
  PredictorDistributionCtrl.$inject = ["$scope", "$rootScope", "$state", "PredictorsTabRenderFactory"];
})();

(function () {
  'use strict';

  angular
    .module('predictors')
    .controller('PredictorDetailsCtrl', PredictorDetailsCtrl);

  /** @ngInject */
  function PredictorDetailsCtrl($scope, $modal, $state, PredictorsRest) {
    var _PredictorsRest = new PredictorsRest();
    var off = [];

    var init = function () {
      $scope.flags = {
        loading: false,
        moreDataAvailable: true
      };
      $scope.filters = {
        search: ''
      };
      $scope.table = {
        sort: {
          predicate: '',
          reverse: false
        }
      };
      $scope.details = [];

      $scope.debouncedLoad();

      off.push($scope.$on('FACETS_CHANGED', function () {
        if (!$scope.flags.loading) {
          $scope.details = [];
          $scope.flags.moreDataAvailable = true;
          $scope.debouncedLoad();
        }
      }));
    };

    off.push($scope.$on('SELECT_PREDICTOR', function () {
      init();
    }));

    off.push($scope.$watch('predictor', function(n, o) {
      if (n && n.id !== o.id) {
        $scope.details = [];
        $scope.debouncedLoad();
      }
    }, true));

    $scope.load = function (attrs) {
      if (!$scope.flags.moreDataAvailable || !$scope.predictor) {
        $scope.flags.loading = false;
        return;
      }

      $scope.flags.loading = true;
      var params = attrs || _.extend($scope.getMetricParams(), {offset: $scope.details.length, limit: 50});

      _PredictorsRest.getDetails($scope.predictor.id, params)
        .success(function (res) {
          $scope.details = $scope.details.concat(res.list);
          $scope.flags.loading = false;
          $scope.flags.moreDataAvailable = res.more_data_available;
        })
    };
    $scope.debouncedLoad = _.debounce($scope.load, 200);

    // DRILLDOWN
    var getActiveFacet = function (facetName) {
      console.log(facetName);
      var active_facet;
      if (facetName === 'models') {
        active_facet = $scope.facets.models;
      }
      if (!active_facet) {
        active_facet = _.find($scope.facets.context_vector, function (value, key) {
          return key.toLowerCase() === facetName;
        });
      }
      if (!active_facet) {
        active_facet = _.find($scope.facets.action_vector, function (value, key) {
          return key.toLowerCase() === facetName;
        });
      }
      return active_facet;
    };

    var setActiveFacet = function (active_facet, selected_value) {
      console.log(active_facet, selected_value);
      var v = _.find(active_facet.list, function (f) {
        if (selected_value.indexOf(':') === -1) {
          return f.display_name.toLowerCase() === decodeURI(selected_value).toLowerCase();
        } else {
          return f.display_name.toLowerCase() === decodeURI(selected_value.split(':')[0].toLowerCase()) ||
                 f.display_name.toLowerCase() === decodeURI(selected_value.split(':')[1].toLowerCase());
        }
      });
      active_facet.all = false;

      _.each(active_facet.list, function (f) {
        f.enabled = false;
      });
      if (v) v.enabled = true;
    };

    var formatDate = function (date) {
      return dateFormat(date, "yyyy-mm-dd HH:MM:ss", true)
    };

    $scope.$on('$stateChangeSuccess', function (event, toState, toParams) {
      $scope.resetPagination();
      // var state = $rootScope.$state;
      var active_facet = getActiveFacet(toParams.filterName);
      active_facet && setActiveFacet(active_facet, toParams.filterValue);
      var params = _.extend({
        limit: 50, offset: $scope.details.length
      }, $scope.getMetricParams());

      if ($state.is('predictors.details.distribution')) {
        // avoid duplicated call
        !active_facet && $scope.debouncedLoad(params);
      } else if ($state.is('predictors.details.trends')) {
        $scope.debouncedLoad();
      }
    });

    $scope.resetPagination = function () {
      $scope.details = [];
      $scope.flags.moreDataAvailable = true;
    };

    $scope.showMatchingResults = function (evt, item) {
      evt.preventDefault();

      var modalInstance = $modal.open({
        backdrop: true,
        keyboard: true,
        backdropClick: true,
        templateUrl: 'predictors/partials/matching-results-modal',
        controller: matchResultsCtrl,
        size: 'lg',
        resolve: {
          contextRow: function() { return item },
          predictorId: function() { return $scope.predictor.id },
          _PredictorsRest: function() { return _PredictorsRest },
        }
      });
    };

    var destructor = function () {
      off.forEach(function (unbind) {
        unbind();
      });
      off = null;
    };

    off.push($scope.$on('$destroy', destructor));
    init();
  }
  PredictorDetailsCtrl.$inject = ["$scope", "$modal", "$state", "PredictorsRest"];

  function matchResultsCtrl($scope, $timeout, predictorId, contextRow, _PredictorsRest) {
    $scope.contextRow = contextRow;
    $scope.dataFetched = false;

    reloadResults();

    function reloadResults() {
      $scope.loading = true;
      _PredictorsRest.getMatchResults(predictorId, {
        context_row: $scope.contextRow
      }).success(function(res) {
        $scope.dataFetched = true;

        $scope.context_schema = res.context_schema;
        $scope.action_schema = res.action_schema;
        $scope.metric_name = res.metric_name;
        $scope.agents = res.considered_agents;
        $scope.context = res.context;
        $scope.context_options =  res.context_options;
        $scope.selectedAgentId = res.selected_agent_id;
      }).finally(function(err) {
        $timeout(function() {
          $scope.loading = false;  
        }, 300);
      });
    }
    
    $scope.onChangeContext = function() {
      angular.extend($scope.contextRow, $scope.context);
      reloadResults();
    };

    $scope.getAgentValue = function(agent, key) {
      return agent[key] || agent[key.toUpperCase()] || agent[key.toLowerCase()];
    };

    $scope.getContextValue = function(key) {
      var context = $scope.context;
      return context[key] || context[key.toUpperCase()] || context[key.toLowerCase()];
    };

    $scope.isKeyInContext = function(key) {
      var contextKeys = Object.keys($scope.context_options);
      return contextKeys.indexOf(key) > -1;
    };
  }
  matchResultsCtrl.$inject = ["$scope", "$timeout", "predictorId", "contextRow", "_PredictorsRest"];
})();

(function () {
  'use strict';

  angular
    .module('predictors')
    .controller('PredictorReportsCtrl', PredictorReportsCtrl);

  /** @ngInject */
  function PredictorReportsCtrl($scope, AnalysisService, $window, $rootScope, $stateParams, Utils, AnalysisReport, PredictorsRest) {
    var Predictors = new PredictorsRest();
    var reports = AnalysisService.getReports();

    var init = function () {
      $scope.reports = [];
      $scope.ready = false;
      $scope.layout = {
        slimscroll: {
          height: '850px', // TODO
          wheelStep: 25,
          width: '215px'
        }
      };
      $scope.flags = AnalysisReport.disableFlags();
      angular.element('#analysis').hide();

      $scope.reports = _.sortBy(reports, 'created_at').reverse();

      if (!AnalysisService.isBuilt()) {
        _.each($scope.reports, function (report, index) {
          AnalysisReport.buildReport(report, function (data) {
            $scope.reports[index] = data.report;
            $scope.reports[index].tabs = data.tabs;
            $scope.reports[index].metric_buckets = data.report.metric_values;
            $scope.reports[index].parsedFilters = getParsedPredictorFilters(data.report.parsedFilters);

            if (data.metricData) {
              $scope.reports[index].metricData = data.metricData;
            }
          });
        });
      }

      var reportIndex = _.findIndex($scope.reports, {id: $stateParams.id});
      if (reportIndex > -1) {
        $scope.viewReport($scope.reports[reportIndex]);
      } else {
        $scope.viewReport($scope.reports[0]);
      }
    };

    $scope.getScrollHeight = function () {
      return $window.innerHeight - 145;
    };

    $scope.viewReport = function (report) {
      if (!report) return;
      $scope.metricData = {};
      $scope.tabs = [{
        name: 'Overall',
        active: true
      }];

      $scope.report = report;
      $scope.tabs = $scope.tabs.concat(report.tabs);
      $scope.metric_buckets = report.metric_values;
      $scope.metricData = report.metricData;
      $scope.selectFeature($scope.tabs[0]);

      _.each($scope.reports, function (r) {
        r.selected = (r.id == report.id);
      });
    };

    $scope.selectFeature = function (feature) {
      $scope.selectedFeature = feature.name;
      $scope.charts = [];

      _.each($scope.tabs, function (t) {
        t.active = false;
        if (t.name === feature.name) {
          t.active = true;
          $scope.flags = AnalysisReport.disableFlags();

          AnalysisReport.selectFeature({
            report: $scope.report, metricData: $scope.metricData, flags: $scope.flags, feature: t.name
          }, function (rep) {
            $scope.flags = rep.flags;
            $scope.charts = rep.charts;
            $scope.table = rep.table;
            $scope.feature_order = rep.feature_order;
            $scope.feature_order_label = 'Feature Score';
          });
        }
      });
      $scope.ready = true;
    };

    $scope.removeReport = function (report) {
      AnalysisReport.deleteReport(report, function (res) {
        if (res) {
          $rootScope.$broadcast('DELETE_BUILT_REPORTS', report);
          _.remove($scope.reports, {id: report.id});
          if ($scope.reports.length) {
            $scope.viewReport($scope.reports[0]);
          }
        }
      });
    };

    $scope.exportTable = function () {
      AnalysisReport.exportTable($scope.report, $scope.selectedFeature);
    };

    $scope.switchChart = function () {
      $scope.flags.showBar = !$scope.flags.showBar;
      $scope.flags.showScatter = !$scope.flags.showScatter;

      _.each($scope.charts, function (each, index) {
        $scope.charts[index].settings.visible = !each.settings.visible;
      });
    };

    $scope.switchView = function () {
      $scope.flags.showTable = !$scope.flags.showTable;
      $scope.flags.showCharts = !$scope.flags.showCharts;
    };

    $scope.paginate = function (direction, chart) {
      $scope.charts = AnalysisReport.paginate(direction, $scope.charts, chart);
    };

    function initReports() {
      if (reports.length) {
        init();
      } else {
        var debounce = _.debounce(function () {
          reports = AnalysisService.getReports();
          initReports();
        }, 10);
        debounce();
      }
    }

    function getParsedPredictorFilters(filters) {
      var _filters = _.reject(filters, function (f) {
        return ['plot_type', 'request_url', 'plot_by', 'level'].indexOf(f.key) >= 0;
      });

      var vectors = [];

      _.each(_filters, function (filter) {
        if (filter.key == "predictor_id") {
          Predictors.getOne(filter.value)
            .success(function (res) {
              var predictor = res.predictor;
              filter.value = predictor.name;

              var found = _.findWhere(_filters, {key: 'models'});
              if (!found) return;

              var model_ids = found.value;
              var model_names = [];
              _.each(model_ids, function (m_id) {
                var found_model = _.findWhere(predictor.models_data, {model_id: m_id});
                if (found_model) {
                  model_names.push(found_model.display_name);
                }
              });

              if (model_names.length) {
                _filters[_filters.indexOf(found)].value = model_names.join(', ').toString();
              }
            });
        } else if (['action_vector', 'context_vector'].indexOf(filter.key) >= 0) {
          var vector = (filter.key == 'action_vector' ? 'agent' : 'customer');
          var filtered_value = _.omit(filter.value, function (v, i) {
            return !filter.value[i].length
          });
          var values = _.values(filtered_value);

          var keys = _.map(_.keys(filtered_value), function (k) {
            return vector + '_' + k;
          });

          vectors.push(_.object(keys, values));
        }
      });

      _filters = _.filter(_filters, function (f) {
        return ['action_vector', 'context_vector'].indexOf(f.key) < 0
      });

      _.each(vectors, function (v) {
        var parsed_v = Utils.objToArray(v);
        _.each(parsed_v, function (pv) {
          pv.value = pv.value.join(', ').toString();
          _filters.push(pv);
        });
      });

      return _filters;
    }

    initReports();
  }
  PredictorReportsCtrl.$inject = ["$scope", "AnalysisService", "$window", "$rootScope", "$stateParams", "Utils", "AnalysisReport", "PredictorsRest"];
})();
(function () {
  'use strict';

  angular
    .module('predictors')
    .factory('PredictorsTabRenderFactory', PredictorsTabRenderFactory);

  /**
   * Common Factory for Trends, Distribution controllers
   */
  /** @ngInject */
  function PredictorsTabRenderFactory($resource) {
    var Factory = {};
    var Resource = $resource('/predictors/facets/json', {}, {getGraphData: {method: 'POST', isArray: false}});

    Factory.initGroupings = function (facets) {
      //plot_bys derived from the actual feature facets
      var features = _.extend({},
          {'all': 'all', 'models': 'models', 'ab testing': 'ab testing'},
          facets.context_vector,
          facets.action_vector);
      var groupings = _.map(features, function (val, key) {
        return {
          type: key,
          value: key,
          active: false || key == 'all'
        }
      });

      return groupings;
    };

    Factory.render = function (attrs, cb) {
      if (!attrs.predictor) return;

      var charts = [{data: [], settings: {}}];
      var params = attrs.params;
      var settings = attrs.chart_settings;

      attrs.flags.rendering = true;
      attrs.tab_options.type = 'metrics';

      Resource.getGraphData({}, params, function (res) {
        attrs.flags.rendering = false;
        if (res.list.length) {
          // if there is negative value, then distribute as Discrete Bar Chart, otherwise as Pie Chart
          var isBar = _.some(res.list, function (each) {
            return each.value < 0;
          });

          if (isBar) {
            settings.chart_type = 'DISCRETEBAR';
          }

          charts = [{data: res.list, settings: settings}];
        }

        cb({
          charts: charts,
          flags: attrs.flags,
          tab_options: attrs.tab_options
        });
      });
    };

    return Factory;
  }
  PredictorsTabRenderFactory.$inject = ["$resource"];
})();