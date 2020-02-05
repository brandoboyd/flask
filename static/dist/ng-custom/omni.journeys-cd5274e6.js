(function () {
  'use strict';

  var dependencies = [
    'omni',
    'ui.router'
  ];
  angular
    .module('omni.journeys', dependencies)
    .run(
      ["$rootScope", "$state", "$stateParams", function ($rootScope, $state, $stateParams) {
        // It's very handy to add references to $state and $stateParams to the $rootScope
        // so that you can access them from any scope within your applications.For example,
        // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
        // to active whenever 'contacts.list' or one of its decendents is active.
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;
      }])
    .config(["$stateProvider", "$urlRouterProvider", function ($stateProvider, $urlRouterProvider) {
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
    }]);
})();

(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('OmniJourneysCtrl', OmniJourneysCtrl);

  /** @ngInject */
  function OmniJourneysCtrl($scope,
                            $timeout,
                            $http,
                            $q,
                            $state,
                            $stateParams,
                            $window,
                            $location,
                            FilterService,
                            MetadataService,
                            DynamicFacetsService,
                            WidgetService,
                            AccountsService,
                            AnalysisService) {

    var JA_REPORTS_SREF = 'journeys.reports';
    var Apps = MetadataService.getApps();
    var listeners = [];
    var is_loading_widget = false;

    $scope.currentTab = "";
    $scope.tabs = [
      {name: 'Path Analysis', sref: 'journeys.path', icon: 'icon-bar-graph-variable-1'},
      {name: 'Trends', sref: 'journeys.trends', icon: 'icon-bar-graph-variable-2'},
      {name: 'Distribution', sref: 'journeys.distribution', icon: 'icon-agent-status-ready-partial'},
      {name: 'Flow', sref: 'journeys.flow', icon: 'icon-app-chart'},
      {name: 'Funnels', sref: 'journeys.funnels', icon: 'icon-iw-queue'},
      {name: 'Details', sref: 'journeys.details', icon: 'icon-view-lists'},
      {name: 'Reports', sref: JA_REPORTS_SREF, icon: 'icon-doc-report-b'}
    ];

    $scope.facets = {
      segments: {visible: true, all: true, list: [], id: 'segment'},
      channels: {visible: true, all: true, list: [], id: 'channel'},
      smart_tags: {visible: true, all: true, list: [], id: 'smart_tag'},
      journey_tags: {visible: true, all: true, list: [], id: 'journey_tag'},
      journey_statuses: {visible: true, all: true, list: [], id: 'status'},
      journey_stages: {visible: true, all: true, list: [], id: 'stage'},
      nps: {visible: true, all: true, list: [], id: 'nps'}
    };

    $scope.labeling = { strategy: 'default' };
    $scope.funnelData = {};

    $scope.group_by_options = [];
    $scope.metric_options = [];
    $scope.filters = {
      journey_type: null,
      group_by: null,
      metric: null,
    };

    $scope.dateRange = FilterService.getDateRange();
    $scope.currentDate = FilterService.getSelectedDateRangeName();


    (function activateController() {
      AnalysisService.fetchReports(JA_REPORTS_SREF);  // should HTTP GET once per section
      $q.when()
        .then(function() {
          loadJourneyStatuses();
          return loadChannels();
        })
        .then(function() {
          return loadJourneyTypes();
        })
        .then(function() {
          return configureWidget();
        });
    })();


    $scope.$on('$stateChangeSuccess',
      function (event, toState, toParams, fromState, fromParams) {
        if (toState.name.indexOf('journeys.details') > -1) {
          $scope.currentTab = 'details';
        } else {
          $scope.currentTab = toState.name.replace('journeys.', '');
        }
      }
    );

    $scope.$on('SEND_LABEL_STRATEGY', function (e, data) {
      $scope.labelStrategy = data;
    });

    $scope.$watch('labeling', function (nVal, oVal) {
      if (nVal != oVal) {
        updateFacets();
      }
    }, true);

    $scope.$on(JA_REPORTS_SREF, function (event, params) {
      $state.go(JA_REPORTS_SREF, params);
    });

    $scope.$watch("dynamic.facets", function(nVal, oVal) {
      if(nVal) {
        $scope.$broadcast('ON_JOURNEY_FACETS_UPDATE');
      }
    },true);

    $scope.$on(FilterService.DATE_RANGE_CHANGED, function () {
      // $scope.from stores utc equivalent of local timerange boundary
      // convert utc to local time so as to make utc timerange boundary
      $scope.currentDate = FilterService.getSelectedDateRangeName();
      var selectedPeriod = FilterService.getDateRangeObj();
      $scope.from = moment.utc(selectedPeriod.from).local().format('YYYY-MM-DD HH:mm:ss');
      $scope.to = moment.utc(selectedPeriod.to).local().format('YYYY-MM-DD HH:mm:ss');
      updateFacets();
    });

    $scope.$on('FUNNEL_SELECTED', function (evt, data) {
      $timeout(function () {
        $scope.funnelData = angular.copy(data);
        $scope.selectedMetric = _.find($scope.analysisMetrics, {name: 'Conversion'});
        $scope.$broadcast('ANALYSIS_FUNNEL_SELECTED', {
          funnelData: $scope.funnelData
        });
      });
    });


    $scope.getJourneySearchParams = function () {
      var params =  {
        from: $scope.from,
        to: $scope.to,
        journey_tags: getJourneyTagsParams(),
        channels: getChannelsParams(),
        status: getJourneyStatusesParams(),
        stage: getJourneyStagesParams(),
        journey_type: getJourneyTypesParams(),
        facets: $scope.getDynamicFacetsValues()
      };

      if ($state.current.name === 'journeys.details.trends') {
        var level = FilterService.getSelectedGraphLevel();
        var timestamp = parseInt($stateParams.timestamp);
        var from = moment.utc(timestamp);
        var to = moment.utc(timestamp).startOf(level).add(level, 1);

        var ext_params = {
          from: from.format('YYYY-MM-DD HH:mm:ss'),
          to: to.format('YYYY-MM-DD HH:mm:ss')
        };
      }

      if ($state.current.name === 'journeys.details.flow.stage') {
        var ext_params = {
          step_name: $stateParams.stage,
          step: parseInt($stateParams.step),
          labeling_strategy: $scope.labeling.strategy
        };
      }

      if ($state.current.name === 'journeys.details.flow.link') {
        var ext_params = {
          sourceName: $stateParams.sourceName,
          targetName: $stateParams.targetName,
          step: parseInt($stateParams.step),
          labeling_strategy: $scope.labeling.strategy
        };
      }

      if ($state.current.name === 'journeys.details.mcp') {
        var ext_params = {
          node_sequence_agr: $stateParams.stagePaths.split('&')
        }
      }

      params = _.extend(params, ext_params)
      return params;
    };

    $scope.setFilter = function (groupings, type) {
      _.each(groupings, function (item) {
        item.type === type ? item.active = true : item.active = false
      });
      updateFacets();
    };

    function findActiveFilter(groupings) {
      return _.find(groupings, { active: true });
    }

    $scope.getActiveFilter = function (groupings) {
      var active = findActiveFilter(groupings);
      return active ? active.value : null
    };

    $scope.getActiveFilterName = function (groupings) {
      var active = findActiveFilter(groupings);
      return active ? active.type : null
    };

    $scope.getActiveLabel = function (metrics) {
      var active = _.find(metrics, function (item) {
        return item.active === true
      });
      return active ? active.label : 'Journeys'
    };

    $scope.getYAxisFormat = function (viewMode) {
      var computed_metric = $scope.getActiveFilter($scope.metric_options);
      if (computed_metric === 'count') {
        return ',.0d';
      }
      if (computed_metric === 'nps') {
        return (viewMode === 'TRENDS') ? ',.0d' : ',.2f';
      }
      if (computed_metric === 'csat') {
        return ',.2f';
      }
      return ',.2f';
    }

    function getJourneyTypesParams() {
      return ($scope.filters.journey_type) ? [$scope.filters.journey_type.id] : [];
    }
    function getChannelsParams() {
      return _.pluck(
        _.filter($scope.facets.channels.list, { enabled: true }),
        'id'
      );
    }
    function getJourneyTagsParams() {
      return _.pluck(
        _.filter($scope.facets.journey_tags.list, { enabled: true }),
        'id'
      );
    }
    function getJourneyStagesParams() {
      return _.pluck(
        _.filter($scope.facets.journey_stages.list, { enabled: true }),
        'display_name'
      );
    }
    function getJourneyStatusesParams() {
      return _.pluck(
        _.filter($scope.facets.journey_statuses.list, { enabled: true }),
        'display_name'
      );
    }

    $scope.$watch('filters.journey_type.id', function (nVal, oVal) {
      if (nVal) {
        var journey_type = _.find($scope.journey_types_list, { id: nVal });

        $q.when()
          .then(function() {
            return loadDynamicFacets(journey_type.display_name);
          })
          .then(function() {
            return loadJourneyTags(journey_type.id);
          })
          .then(function() {
            return loadJourneyStages(journey_type.id);
          })
          .then(function() {
            finishJourneyTypeWatcher();
          });

        $scope.$broadcast('ON_JOURNEY_TYPE_CHANGE');
      }
    }, true);

    $scope.$watch('filters.metric', function(nVal) {
      if (nVal) {
        $scope.setFilter($scope.metric_options, nVal.type)
      }
    });

    $scope.$watch('filters.group_by', function(nVal) {
      if (nVal) {
        $scope.setFilter($scope.group_by_options, nVal.type);
      }
    });

    /********* END OF STAGES *********/


    $scope.getDynamicFacetsValues = function() {
      var facets = {};
      if($scope.dynamic && $scope.dynamic.facets) {
        _.each($scope.dynamic.facets, function(facet) {
          facets[facet.id] = _.pluck(_.where(facet.list, {enabled:true}), 'display_name');
          //Don't pass attributes if 'All' selected
          if (facets[facet.id].length == 0) delete facets[facet.id]
        });
      }
      return facets
    };

    /********* Facets loader functions *********/
    function loadJourneyStatuses() {
      var items = [
        { display_name: 'finished', enabled: false },
        { display_name: 'abandoned', enabled: false },
        { display_name: 'ongoing', enabled: false }
      ]
      Array.prototype.push.apply($scope.facets.journey_statuses.list, items);
    }

    function loadJourneyTypes() {
      return $http
        .get("/journey_types")
        .success(function (res) {
          $scope.journey_types_list = res.data;
          $scope.filters.journey_type = $scope.journey_types_list[0];
          $scope.analysis.params = $scope.getAnalysisExtraParams();
          $scope.analysis.filters = $scope.getJourneySearchParams();
          $scope.$broadcast('ANALYSIS_PARAMS_CHANGED', $scope.analysis.params);
        });
    }

    function loadChannels() {
      return $http
        .post('/channels_by_type/json', {
          type: 'inbound',
          serviced_only: false,
          parent_names: true
        })
        .success(function (res) {
          $scope.facets.channels.list = _.map(res.list, function (item) {
            return { id: item.id, display_name: item.title, enabled: false }
          });
        });
    }

    /***** load facets which are dependant on journey type *****/
    function loadDynamicFacets(journey_type_name) {
      return DynamicFacetsService.getFacetsBySection('journey', journey_type_name)
        .then(function(res) {
          $scope.dynamic = res;

          $scope.group_by_options = $scope.dynamic.group_by;
          $scope.metric_options = $scope.dynamic.metrics;
          $scope.sankeyGroupings = $scope.dynamic.sankey_group_by;

          $scope.filters.group_by = $scope.group_by_options[0];
          $scope.filters.metric = $scope.metric_options[0];
        });
    }

    function loadJourneyTags(journey_type_id) {
      return $http({
        url: '/journey_tags',
        method: 'GET',
        params: { journey_type_id: journey_type_id }
      })
        .success(function (res) {
          $scope.facets.journey_tags.list = _.uniq(_.map(res.data, function (item) {
            return _.defaults(item, {enabled: false});
          }));
        });
    }

    function loadJourneyStages(journey_type_id) {
      return $http.get('/journey_types/{jid}/stages'.replace('{jid}', journey_type_id))
        .success(function (res) {
          $scope.facets.journey_stages.list = _.map(res.data, function (item) {
            return _.defaults(item, {enabled: false});
          });
        });
    }

    function finishJourneyTypeWatcher() {
      if (is_loading_widget) {
        loadWidgetSettings($scope.widget.item);
      }

      $scope.analysis.params = $scope.getAnalysisExtraParams();
      $scope.analysis.filters = $scope.getJourneySearchParams();
      $scope.$broadcast('ANALYSIS_PARAMS_CHANGED', $scope.analysis.params);
    }

    $scope.updateFacets = function() {
      updateFacets();
    };

    var updateFacets = _.debounce(function () {
      $scope.$broadcast("ON_JOURNEY_FACETS_UPDATE");
      $scope.analysis.filters = $scope.getJourneySearchParams();
    }, 100);

    function loadWidgetSettings(w) {
      is_loading_widget = false;
      if (!w || !w.settings) return;
      var settings = w.settings;

      // Load Date Range
      if (settings.from && settings.to) {
        FilterService.updateDateRange({
          from: moment(settings.from).utc(),
          to: moment(settings.to).utc()
        });
      }

      // static facets
      $scope.facets.channels.all = (settings['channels'].length == 0);
      _.each(settings['channels'], function(label) {
        var v = _.find($scope.facets.channels.list, { id: label });
        if (v) v.enabled = true;
      });

      $scope.facets.journey_statuses.all = (settings['status'].length == 0);
      _.each(settings['status'], function(label) {
        var v = _.find($scope.facets.journey_statuses.list, { display_name: label });
        if (v) v.enabled = true;
      });

      $scope.facets.journey_tags.all = (settings['journey_tags'].length == 0);
      _.each(settings['journey_tags'], function(label) {
        var v = _.find($scope.facets.journey_tags.list, { id: label });
        if (v) v.enabled = true;
      });

      $scope.facets.journey_stages.all = (settings['stage'].length == 0);
      _.each(settings['stage'], function(label) {
        var v = _.find($scope.facets.journey_stages.list, { display_name: label });
        if (v) v.enabled = true;
      });

      // dynamic facets
      _.each($scope.dynamic.facets, function (facet) {
        if (_.has(settings.facets, facet.id) && settings.facets[facet.id].length) {
          facet.all = false;
          _.each(settings.facets[facet.id], function (label) {
            var v = _.find(facet.list, { display_name: label });
            if (v) { v.enabled = true }
          });
        }
      });

      // Set active filter
      $scope.filters.group_by = _.find($scope.group_by_options, { type:  settings.group_by });
      $scope.filters.metric = _.find($scope.metric_options, { type: settings.computed_metric }) || $scope.metric_options[0];

      // For funnel
      if (settings.funnel_id) {
        $scope.$broadcast('FUNNEL_WIDGET_LOADED', {'funnel_id': settings.funnel_id});
      }
    }

    function configureWidget() {
      $scope.widget = {
        removing: false,
        updating: false,
        item: null,
        getParams: function () {
          var searchParams = $scope.getJourneySearchParams();

          if ($state.current.url == 'distribution') {
            var settings = angular.extend(searchParams, {
              plot_type: 'avg_distributions',
              group_by: $scope.getActiveFilter($scope.group_by_options),
              computed_metric: $scope.getActiveFilter($scope.metric_options),
              // level: 'day'
            });
            var extra_settings = {
              request_url : '/journeys/plots',
              source      : '/omni/journeys#/distribution?wid=',
              directive   : 'chart',
              target      : 'OMNI',
              chart_type  : 'PIE',
              yAxisFormat : $scope.getYAxisFormat('DISTRIBUTION'),
              account_info: AccountsService.getCompactAccount(),
            };
            return { settings: settings, extra_settings: extra_settings };
          } else if ($state.current.url == 'trends') {
            var settings = angular.extend(searchParams, {
              plot_type: 'timeline',
              group_by: $scope.getActiveFilter($scope.group_by_options),
              computed_metric: $scope.getActiveFilter($scope.metric_options),
              level: _.indexOf(['today', 'yesterday'], FilterService.getSelectedDateRangeAlias()) !== -1 ? 'hour' : 'day'
            });
            var extra_settings = {
              request_url : '/journeys/plots',
              source      : '/omni/journeys#/trends?wid=',
              directive   : 'chart',
              target      : 'OMNI',
              chart_type  : 'LINE',
              yAxisLabel  : $scope.getActiveLabel($scope.metric_options),
              yAxisFormat : $scope.getYAxisFormat('TRENDS'),
              account_info: AccountsService.getCompactAccount(),
            };
            return { settings: settings, extra_settings: extra_settings };
          } else if ($state.current.url == 'flow') {
            return {
              settings: _.omit(searchParams, 'status'),
              extra_settings: {
                request_url: '/journeys/sankey',
                source: '/omni/journeys#/flow?wid=',
                directive: 'sankey-chart',
                target: 'JOURNEY-SANKEY',
                account_info: AccountsService.getCompactAccount()
              }
            };
          } else if ($state.current.url == 'funnels') {
            var dashParams = {
              settings: _.extend(searchParams, { group_by: 'abandonment_rate'}),
              extra_settings: {
                request_url: '/funnel/facets',
                source: '/omni/journeys#/funnels?wid=',
                directive: 'funnel-chart',
                target: 'JOURNEY-FUNNEL',
                funnel_steps: $scope.funnelData.funnel_steps,
                journey_stages: $scope.funnelData.journey_stages,
                account_info: AccountsService.getCompactAccount()
              }
            };
            if (dashParams.settings.from) dashParams.settings.from = moment.utc(dashParams.settings.from).format('MM/DD/YYYY');
            if (dashParams.settings.to) dashParams.settings.to = moment.utc(dashParams.settings.to).format('MM/DD/YYYY');
            dashParams.settings.funnel_id = $scope.funnelData.funnel_id;

            return dashParams;
          }
        },
        setup: function (w) {
          var wscope = $scope.widget;
          if (wscope.updating) {
            wscope.updating = false;
          }

          if (!w || _.isEmpty(w)) {
            return;
          }

          console.log('Widget Setup', w);
          // This will trigger journey type id watcher to load all dynamic options
          is_loading_widget = true;
          $scope.filters.journey_type = _.find(
            $scope.journey_types_list,
            { id: w.settings.journey_type[0] }
          );
        }
      };
      $scope.widget["remove"] = WidgetService.makeRemove($scope.widget, 'removing');
      $scope.$on(WidgetService.CHANGED, function (evt, data) {
        var w = $scope.widget;
        w.updating = true;
        w.item = data.widget;
      });
      $scope.$watch('widget.item', $scope.widget.setup);
      $scope.$watch('location.search()', locationChanged);
      function locationChanged() {
        var w = $scope.widget;
        if (w.removing) {
          return;
        }
        WidgetService.loadFromLocation().then(function (res) {
          w.item = WidgetService.getCurrent();
          w.setup(w.item);
        });
      }
    }

    /******* Analysis Panel ******/
    $scope.layout = {
      slimscroll: {
        height: '100%',
        width: '200px',
        wheelStep: 25
      }
    };

    $scope.analysis = {
      filters: {},
      params: {}
    };

    $scope.getScrollHeight = function () {
      return $window.innerHeight - 95;
    };

    $scope.getAnalysisExtraParams = function () {
      var cardinalities = $scope.filters.journey_type.journey_attributes_cardinalities;
      var journey_attributes_schema = _.filter($scope.filters.journey_type.journey_attributes_schema, function (each) {
        var key = cardinalities[each.name] || cardinalities[each.label];
        return ['integer', 'double', 'float'].indexOf(key.type) >= 0 && _.has(key, 'values');
      });

      var metrics = _.map(journey_attributes_schema, function (m) {
        var key = cardinalities[m.name] || cardinalities[m.label];
        var numeric_values = _.filter(key.values, function (v) {
          return !isNaN(parseInt(v));
        });
        var metric_values = [_.min(numeric_values), _.max(numeric_values)];
        return _.extend(m, {
          metric: m.name,
          metric_values: metric_values,
          metric_values_range: metric_values,
          metric_type: MetadataService.processDataType(m.type)
        });
      });

      var selectedMetric = metrics[0];

      return {
        metrics: metrics,
        metricParams: selectedMetric,
        application: Apps.JA,
        sref: JA_REPORTS_SREF,
        labelStrategy: $scope.labelStrategy
      };
    };
    /*** End of Analysis Panel ***/

    $scope.$watch(function () {
      return $location.path();
    }, function (value) {
      $timeout(function () {
        if (value === '/funnels') {
          angular.element('option[label="conversion"]').show();
        } else {
          angular.element('option[label="conversion"]').hide();
        }
        if (value === '/flow') {
          angular.element('option[label="stage-paths"]').show();
        } else {
          angular.element('option[label="stage-paths"]').hide();
        }
        if (value === '/path') {
          angular.element('option[label="paths-comparison"]').show();
        } else {
          angular.element('option[label="paths-comparison"]').hide();
        }
      });
    });

    listeners.push($scope.$on('$destroy', destructor));
    function destructor () {
      listeners.forEach(function (unbind) {
        unbind();
      })
      listeners = null;
    }
  }
  OmniJourneysCtrl.$inject = ["$scope", "$timeout", "$http", "$q", "$state", "$stateParams", "$window", "$location", "FilterService", "MetadataService", "DynamicFacetsService", "WidgetService", "AccountsService", "AnalysisService"];
})();

(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysDetailsCtrl', JourneysDetailsCtrl);

  /** @ngInject */
  function JourneysDetailsCtrl($scope, $rootScope, $http, $state, $timeout, FilterService) {

    $scope._ = _;

    $scope.$on("ON_JOURNEY_FACETS_UPDATE", function () {
      $scope.debouncedSearchDetails($scope.getJourneySearchParams());
    });

    var init = function () {
      angular.element('#analysis').hide();
    };

    init();

    $scope.journeysDetailsTable = {
      sort: {
        predicate: 'ucb_score',
        reverse: true
      }
    };

    $scope.getTimelineParams = function (journey) {
      // console.log("Timeline params", journey);
      var journeyTags = _.map(journey.journey_tags, function (id) {
        return {
          id: id, title: $scope.getJourneyTagName(id)
        };
      });

      return _.extend($scope.dateRange, journey, {
        assignedTags: journeyTags,
        journey_stages: $scope.facets.journey_stages
      });
    };

    $scope.getSmartTagName = function (tag_id) {
      var tag = _.find($scope.facets.smart_tags.list, function (t) {
        return t.id === tag_id
      });
      return tag ? (tag.display_name) : null;
    };

    $scope.getJourneyTagName = function (tag_id) {

      var tag = _.find($scope.facets.journey_tags.list, function (t) {
        return t.id === tag_id
      });

      // console.log("J NAME IS", tag);
      return tag ? (tag.display_name) : null;
    };

    var formatDate = function (date) {
      return dateFormat(date, "yyyy-mm-dd HH:MM:ss", true)
    };

    var getActiveFacet = function (facetName) {
      var active_facet;
      if ($scope.dynamic) {
        active_facet = _.find($scope.dynamic.facets, {id: facetName});
      }
      if (!active_facet) {
        active_facet = _.find($scope.facets, {id: facetName});
      }
      return active_facet;
    };

    var setActiveFacet = function (active_facet, selected_value) {
      var v = _.find(active_facet.list, function (f) {
        if (f.value == decodeURI(selected_value)) {
          return true;
        }
        return f.display_name == decodeURI(selected_value)
      });
      active_facet.all = false;

      if (active_facet.id == 'type' && v) {
        //single values facet are set differently - we have only one of such type
        // $scope.facets.journey_types.selected = v.id;
      } else {
        // use of timeout will not reflect the correct results when getJourneySearchParams() is
        // called immediately after
        //$timeout(function () {
        _.each(active_facet.list, function (f) {
          f.enabled = false;
        });
        if (v) v.enabled = true;
        //}, 0);
      }
    };

    $scope.$on('$stateChangeSuccess', function (event, toState, toParams, fromState, fromParams) {

      var state = $rootScope.$state;
      var active_facet = getActiveFacet(toParams.filterName);
      //console.log('active_facet', active_facet);
      active_facet && setActiveFacet(active_facet, toParams.filterValue);

      $scope.debouncedSearchDetails($scope.getJourneySearchParams());
    });

    $scope.journeys = {};
    $scope.journeys.table_header = [];
    $scope.journeys.table_data = [];

    $scope.resetPagination = function () {
      $scope.offset = 0;
      $scope.limit = 10;
      //delete $scope.journeys;
      $scope.journeys.table_data = [];
      $scope.hasMore = true;
    };

    $scope.loadMore = function () {
      if ($scope.hasMore) {
        var params = $scope.getJourneySearchParams();
        console.log('loadMore debouncing with params', params);
        $scope.debouncedSearchDetails(params, {loadMore: true});
      }
    };

    $scope.searchDetails = function (params, options) {

      if (!options || !options.loadMore) {
        $scope.resetPagination();
      }

      //delete 'level' param since it's not supported by this endpoint
      if ('level' in params) {
        delete params['level']
      }

      $scope.loading = true;

      var page_params = {
        offset: $scope.offset,
        limit: $scope.limit,
        short_fields: 'true'
      };

      _.extend(params, page_params);

      console.log('making request with params', params);
      $http.post("/journeys/json", params)
        .success(function (data) {
          $scope.loading = false;


          if (data.list.length) {
            $scope.journeys.table_header =
              _.reject(
                _.keys(data.list[0]), function(d) {
                  var rejected_keys = ['customer_name', 'customer_id', 'id', 'journey_attributes'];
                  return _.indexOf(rejected_keys, d) >= 0
              });

            $scope.journeys.journey_attributes_header = _.reject(
              _.keys(data.list[0]['journey_attributes']), function(d) {
                  var rejected_keys = [];
                  return _.indexOf(rejected_keys, d) >= 0
              });


          }

          if (data.list.length === 0) {
            $scope.hasMore = false;
            $scope.loading = false;
          } else {
            $scope.hasMore = data.more_data_available;
            $scope.journeys.table_data = $scope.journeys.table_data.concat(data.list);
            $scope.offset = $scope.journeys.table_data.length;
            $scope.loading = false;
          }

        });
    }
    $scope.debouncedSearchDetails = _.debounce($scope.searchDetails, 300);
  }
  JourneysDetailsCtrl.$inject = ["$scope", "$rootScope", "$http", "$state", "$timeout", "FilterService"];
})();

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
  JourneysDistributionCtrl.$inject = ["$scope", "$rootScope", "$http", "$state"];
})();

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
  JourneysTrendsCtrl.$inject = ["$scope", "$rootScope", "$http", "$state", "FilterService"];
})();

(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysFlowCtrl', JourneysFlowCtrl);

  /** @ngInject */
  function JourneysFlowCtrl($scope, $rootScope, $timeout, $http, $state) {

    //$scope.sankey = {};

    $scope.$watch('sankeyGroupings', function(nVal, oVal) {
      if(nVal && nVal.length > 0) {
        $scope.sankeyGroup = nVal[0];
      }
    },true);


    $scope.$on("ON_JOURNEY_FACETS_UPDATE", function () {
      if($scope.sankeyGroup) {
        $scope.getJourneysFlowData($scope.sankeyGroup.type, $scope.labeling.strategy)
      }
    })

    var init = function () {
      $scope.loading = true;
      angular.element('#analysis').hide();
    };

    init();

    $scope.$broadcast('SEND_LABEL_STRATEGY', $scope.labeling.strategy);

    $scope.getJourneysFlowData = _.debounce(
      function (group, strategy) {
        var params = $scope.getJourneySearchParams();
        //have no status filed in flow chart - make sure we never send it even if it set
        if ('status' in params) {
          delete params['status']
        }

        params['group_by'] = group;
        params['labeling_strategy'] = strategy;

        $scope.extra_settings = {
          drilldownEnabled: true,
          chart_type: 'SANKEY',
          target: 'OMNI',
          noDataMsg: 'Please select a Journey Type in order to view paths'
        };

        if ($scope.filters.journey_type !== null) {
          $http.post("/journeys/sankey", params)
            .success(function (data) {
              $scope.loading = false;
              $scope.data = data.list.data;
              $scope.extra_settings = {
                drilldownEnabled: true,
                chart_type: 'SANKEY',
                target: 'OMNI'
              };
            }) //success handler
        } else {
          $scope.loading = false;
          $scope.data = []
        }
      }, 500); //debounce


    $scope.sankeyMode = false;


    $rootScope.$on("DRILL_DOWN_MODE", function (e, isOn) {
      $timeout(function () {
        $scope.sankeyMode = isOn;
      }, 0)
    })

   /*
    $rootScope.$on("DYNAMIC_FACETS_CHANGED", function (e, facets) {
      console.log("DYN FACETS CHANED!!!")
      $timeout(function () {
          $scope.getJourneysFlowData($scope.sankey.group, $scope.labeling.strategy);
      }, 0)
    })
*/

    $scope.$watch('sankeyGroup', function (nVal, oVal) {
      if (nVal) {
        $scope.loading = true;
        $scope.getJourneysFlowData(nVal.type, $scope.labeling.strategy);
      }
    }, true)

    //$scope.getJourneysFlowData()
    $rootScope.$on('journeys.details.flow.link', function (event, params) {
      params.filterName = $scope.sankeyGroup.type;
      $state.go('journeys.details.flow.link', params)
    })
    $rootScope.$on('journeys.details.flow.stage', function (event, params) {
      $state.go('journeys.details.flow.stage', params)
    })






  }
  JourneysFlowCtrl.$inject = ["$scope", "$rootScope", "$timeout", "$http", "$state"];
})();
(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysReportsCtrl', JourneysReportsCtrl);

  /** @ngInject */
  function JourneysReportsCtrl($scope, AnalysisService, AnalysisReport, $rootScope, $window, $stateParams,
                               JourneyTypesRest,
                               JourneyTagsRest,
                               JourneyFunnelsRest,
                               ChannelsRest) {
    var JourneyTypes = new JourneyTypesRest(),
      JourneyTags = new JourneyTagsRest(),
      JourneyFunnels = new JourneyFunnelsRest(),
      _ChannelsRest = new ChannelsRest();
    var reports = AnalysisService.getReports();

    var init = function () {
      $scope.reports = [];
      $scope.ready = false;
      $scope.layout = {
        slimscroll: {
          height: '850px',
          wheelStep: 25,
          width: '215px'
        }
      };
      $scope.flags = AnalysisReport.disableFlags();
      angular.element('#analysis').hide();

      $scope.reports = _.sortBy(reports, 'created_at').reverse();

      if (!AnalysisService.isBuilt()) {
        _.each($scope.reports, function (report, index) {
          AnalysisReport.buildReport(report, function (rep) {
            $scope.reports[index] = rep.report;
            $scope.reports[index].tabs = rep.tabs;
            $scope.reports[index].metric_buckets = rep.report.metric_values;
            $scope.reports[index].parsedFilters = getParsedJourneyFilters(rep.report);
            if (rep.metricData) {
              $scope.reports[index].metricData = rep.metricData;
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
        if (AnalysisService.isEmpty()) {
          return;
        }

        var debounce = _.debounce(function () {
          reports = AnalysisService.getReports();
          initReports();
        }, 10);
        debounce();
      }
    }

    function getParsedJourneyFilters(report) {
      var filters = report.parsedFilters;
      var dynFacets = report.dynFacets;
      var funnel;

      var processed_facets = [];
      var facet_keys = _.keys(dynFacets);

      _.each(facet_keys, function (facet_key) {
        var facet_val = dynFacets[facet_key];
        if (dynFacets[facet_key].length) {
          facet_val = dynFacets[facet_key].join(', ');
        }
        processed_facets.push({
          key: facet_key,
          value: facet_val
        });
      });

      // values
      _.each(filters, function (f) {
        if (f.key == 'journey_type' && (f.value.length || f.value)) {
          if (f.value.length) {
            f.value = f.value[0]; // due to historical changes, journey_type can be the array of 1 only element...
          }
          JourneyTypes.getOne(f.value)
            .success(function (res) {
              f.value = res.data.display_name;
            });

        } else if (f.key === 'journey_tags' && f.value.length) {
          var jTags = [];
          _.each(f.value, function (id) {
            JourneyTags.getOne(id)
              .success(function (res) {
                jTags.push(res.data.display_name);
              });
          });
          f.value = jTags.join(', ').toString();

        } else if (f.key === 'funnel_id' && f.value) {
          JourneyFunnels.getOne(f.value)
            .success(function (res) {
              funnel = res.data;

              var found = _.findWhere(filters, {key: 'stage_id'});

              if (typeof found !== 'undefined') {
                JourneyTypes.getStages(funnel.journey_type)
                  .success(function (stage) {
                    filters[filters.indexOf(found)].value = _.findWhere(stage.data, {id: found.value}).display_name;
                  });
              }

              f.value = funnel.name;
            });
        } else if (f.key === 'channels' && f.value.length) {
          _ChannelsRest.getOne(f.value)
            .success(function (res) {
              f.value = res.item.title;
            });
        } else {
          f.value = f.value.toString();
        }
      });

      filters = _.without(filters, _.findWhere(filters, function (f) {
        return ['timerange', 'facets'].indexOf(f.key) >= 0;
      }));

      if (dynFacets) {
        filters = filters.concat(processed_facets);
      }

      return filters; // we already have - from, to
    }

    initReports();
  }
  JourneysReportsCtrl.$inject = ["$scope", "AnalysisService", "AnalysisReport", "$rootScope", "$window", "$stateParams", "JourneyTypesRest", "JourneyTagsRest", "JourneyFunnelsRest", "ChannelsRest"];
})();
(function () {
    'use strict';

    angular.module('omni.journeys')
        .controller('JourneysFunnelsCtrl', ["$scope", "$http", "JourneyTypesRest", "JourneyFunnelsRest", function ($scope, $http, JourneyTypesRest, JourneyFunnelsRest) {
            var JourneyTypes = new JourneyTypesRest();
            var JourneyFunnels = new JourneyFunnelsRest();

            var ordinalColors = ['#4AC764', '#F8A740', '#EA4F6B'];
            $scope.allFunnels = [];
            $scope.currentFunnelId = null;
            $scope.currentFunnel = null;
            $scope.currentBar = null;
            $scope.selectedStageId = null;
            $scope.loading = true;

            angular.element('#analysis').hide();

            $http
                .post('/select_strategy', {strategy: 'default'})
                .then(function() {
                    $scope.loading = false;
                    var fetchFunnels = JourneyFunnels.list();
                    return (fetchFunnels.then && fetchFunnels || fetchFunnels.$promise);
                })
                .then(function(res) {
                    $scope.allFunnels = res.data.data;
                    $scope.funnels = _.filter($scope.allFunnels, function (item) {
                        return item.journey_type == $scope.filters.journey_type.id
                    });
                    if ($scope.funnels.length) {
                        $scope.currentFunnelId = $scope.funnels[0].id;
                    }

                    JourneyTypes.list().success(function (jTypes) {
                        $scope.journeyStages = {};
                        _.each(jTypes.data, function (jt) {
                            JourneyTypes.getStages(jt.id)
                              .success(function (stages) {
                                $scope.journeyStages[jt.id] = stages.data;
                                $scope.funnelSelected();
                            });
                        });
                    });
                });

            $scope.toggleAnalyticsPanel = function(toShow) {
                var analysisPanel = angular.element('#analysis');
                if (toShow && analysisPanel.is(':hidden'))
                    analysisPanel.show('fast');
                else if (!toShow && analysisPanel.is(':visible'))
                    analysisPanel.hide('fast');
            };

            $scope.funnelSelected = function() {
                $scope.currentFunnel = _.find($scope.funnels, {'id': $scope.currentFunnelId});
                $scope.searchDetails($scope.getJourneySearchParams());
                $scope.emitFunnelStatus();
            };

            $scope.emitFunnelStatus = function() {
                if (!$scope.currentFunnel) return;
                var jtId = $scope.currentFunnel.journey_type;
                var stages = _.map($scope.journeyStages[jtId], _.partialRight(_.pick, ['id', 'display_name']));

                $scope.$emit('FUNNEL_SELECTED', {
                    funnel_id: $scope.currentFunnelId,
                    funnel_name: $scope.currentFunnel && $scope.currentFunnel.name,
                    journey_stages: stages,
                    funnel_steps: $scope.currentFunnel.steps,
                    stage_id: $scope.selectedStageId,
                    stage_name: $scope.getJourneyStageName($scope.currentFunnel.journey_type, $scope.selectedStageId)
                });
            };

            $scope.$on('FUNNEL_WIDGET_LOADED', function(evt, data) {
                $scope.currentFunnelId = data.funnel_id;
                $scope.funnelSelected();
            });

            $scope.getJourneyStageName = function(journeyTypeId, journeyStageId) {
                if ($scope.journeyStages && $scope.journeyStages[journeyTypeId]) {
                    var stage = _.find($scope.journeyStages[journeyTypeId], {'id': journeyStageId});
                    if (stage) return stage.display_name;
                }
                return 'N/A';
            };

            $scope.isLastStep = function(stepId) {
                if (!$scope.currentFunnel) return false;
                var temp = angular.copy($scope.currentFunnel.steps);
                return stepId == temp.pop();
            };

            $scope.searchDetails = _.debounce(function (params) {
                if (!$scope.currentFunnelId) {
                    return;
                }

                var postParams = angular.extend(params, {
                    funnel_id: $scope.currentFunnelId,
                    group_by: 'abandonment_rate',
                })
                postParams.from = moment(params.from).format('MM/DD/YYYY');
                postParams.to = moment(params.to).format('MM/DD/YYYY');

                function isEmpty(data) {
                    return !(_.some(data, function(item) {
                        return item['count']['sum'] > 0;
                    }));
                }

                $http.post("/funnel/facets", postParams)
                    .success(function(resp){
                        var statuses = ['converted', 'stuck', 'abandoned'];
                        var rawData = resp.list.data;
                        var chartData = [];

                        if (!isEmpty(rawData)) {
                            chartData = _.map(statuses, function (status) {
                                var obj = {
                                    key: status,
                                    values: []
                                };
                                var funnel = $scope.currentFunnel;

                                obj.values = _.map(funnel.steps, function (step, index) {
                                    return {x: step, y: rawData[index]['count'][status] || 0};
                                });
                                return obj;
                            });
                        }

                        $scope.chartData = chartData;

                        $scope.renderFunnels(chartData, rawData);
                    })
                    .error(function(err) {
                        console.log(err);
                    });

            }, 600);


            $scope.renderFunnels = function(chartData, originalData) {

                var chartDrawFinished = function() {
                    // Show count of journeys on each bar snippet
                    d3.select('g.labels').remove();
                    var allBars = d3.selectAll('.nv-bar')[0];
                    var gValues = d3.select('.nv-wrap g').append('g').classed('labels', true);

                    _.each(allBars, function(bar) {
                        var w = +bar.getAttribute('width');
                        var h = +bar.getAttribute('height');
                        var x = +bar.getAttribute('x');
                        var y = +bar.getAttribute('y');
                        var value = bar.__data__.y;

                        if (h < 20 || value == 0) return;
                        gValues.append('text')
                            .attr('text-anchor', 'middle')
                            .attr('fill', 'white')
                            .attr('x', x + w/2)
                            .attr('y', y + h/2 + 5)
                            .attr('series', bar.__data__.series)
                            .attr('stage', bar.__data__.x)
                            .attr('transform', bar.getAttribute('transform'))
                            .text(d3.format('s')(value))
                    });

                    // Show arrows with transition percent inside
                    d3.select('g.arrows').remove();
                    var transBars = d3.selectAll('.nv-series-0 .nv-bar')[0];
                    var gArrows = d3.select('.nv-wrap g').append('g').classed('arrows', true);

                    _.each(transBars, function(bar) {
                        var barWidth = +bar.getAttribute('width');
                        var barHeight = +bar.getAttribute('height');
                        var x = barWidth * 2 - barWidth / 6;
                        var y = +bar.getAttribute('y') + barHeight / 2;
                        var w = barWidth * 2 / 3;
                        var h = 30;

                        var stageId = bar.__data__.x;
                        var steps = $scope.currentFunnel.steps;
                        var ind = steps.indexOf(stageId);
                        var percent = 0;
                        if ($scope.isLastStep(stageId) || !originalData[ind]) return;
                        var convertedCount = originalData[ind]['count']['converted'];
                        var totalCount = originalData[ind]['count']['sum'];
                        if (convertedCount > 0 && totalCount > 0) {
                            percent = convertedCount / totalCount;
                        }

                        if (barHeight < h) {
                            y = y - h/2;
                        }

                        var pts = (x-w) + ',' + (y-h/2) + ' ' +
                            (x-.2*w) + ',' + (y-h/2) + ' ' +
                            x + ',' + y + ' ' +
                            (x-.2*w) + ',' + (y+h/2) + ' ' +
                            (x-w) + ',' + (y+h/2);

                        gArrows.append('polygon')
                            .attr('points', pts)
                            .attr('transform', bar.getAttribute('transform'))
                            .attr('style', 'fill: rgba(0,0,0,0.5);');

                        var px = barWidth + barWidth / 6 + barWidth * 4 / 15;

                        gArrows.append('text')
                            .attr('text-anchor', 'middle')
                            .attr('fill', 'white')
                            .attr('transform', bar.getAttribute('transform'))
                            .attr('x', px)
                            .attr('y', y + 5)
                            .text(d3.format('.3p')(percent));
                    });

                    // Show total count of journeys on top of each bar
                    d3.select('g.labels-total').remove();
                    var totalBars = d3.selectAll('.nv-series-2 .nv-bar')[0];
                    var gTotalValues = d3.select('.nv-wrap g').append('g').classed('labels-total', true);

                    _.each(totalBars, function(bar) {
                        var w = +bar.getAttribute('width');
                        var x = +bar.getAttribute('x');
                        var y = +bar.getAttribute('y');
                        if (!$scope.isLastStep(bar.__data__.x)) return;

                        gTotalValues.append('text')
                            .attr('text-anchor', 'middle')
                            .attr('fill', 'black')
                            .attr('x', x + w/2)
                            .attr('y', y - 10)
                            .attr('transform', bar.getAttribute('transform'))
                            .text('END')
                    });

                    // Remove bars with zero value which are drawn as simple line
                    d3.selectAll('.nv-bar')
                        .attr('style', function(d) {
                            if (d.y == 0) return 'display:none';
                        });


                    // Draw buttons for x-axis ticks (steps)
                    var xAxisTicks = d3.selectAll('.nv-x .tick.zero text')[0];

                    _.each(xAxisTicks, function(tick) {
                        var rect = tick.getBBox();
                        var tickContainer = tick.parentElement;
                        if (!rect || !tickContainer) return;
                        
                        var x = rect.x;
                        var y = rect.y;
                        var w = rect.width;
                        var h = rect.height;

                        d3.select(tickContainer)
                            .selectAll('rect')
                            .remove();

                        // When the graph is squeezed, x-axis tick might be hidden, 
                        // in this case, don't draw rect around it.
                        var isHidden = d3.select(tick).style('opacity') === '0';
                        if (isHidden) { return }

                        d3.select(tickContainer)
                            .insert('rect', 'text')
                            .attr('x', x - 20)
                            .attr('y', y - (30 - h) / 2)
                            .attr('rx', 4)
                            .attr('ry', 4)
                            .attr('width', w + 40)
                            .attr('height', 30);
                    });

                };


                //////////////////////////////
                // Generate multi bar chart //
                nv.addGraph({
                    generate: function () {
                        var chart = nv.models.multiBarChart()
                            .color(ordinalColors)
                            .showControls(false)
                            .showLegend(true)
                            .stacked(true)
                            .groupSpacing(0.5);

                        chart.xAxis
                            .tickPadding(25)
                            .tickFormat(function (d) {
                                return $scope.getJourneyStageName($scope.currentFunnel.journey_type, d);
                            });
                        chart.yAxis
                            .tickPadding(10)
                            .tickFormat(d3.format('s'));

                        d3.selectAll('.funnel-chart svg > *').remove();

                        d3.select('.funnel-chart svg')
                            .datum(chartData)
                            .transition().duration(600)
                            .call(chart)
                            .each('end', chartDrawFinished);

                        nv.utils.windowResize(chart.update);
                        nv.utils.windowResize(chartDrawFinished);

                        return chart;
                    },
                    callback: function (chart) {
                        function selectStage(stageId) {
                            d3.selectAll('g.nv-x.nv-axis .tick.zero')
                                .classed('selected', function(d) { return d == stageId; });
                            $scope.selectedStageId = stageId;
                            $scope.toggleAnalyticsPanel($scope.selectedStageId !== null);
                            $scope.emitFunnelStatus();
                        }

                        chart.legend.updateState(false);    // Disable legend click interaction

                        chart.tooltip.chartContainer('.funnel-chart');
                        chart.tooltip.offset({left: 300, top: 230});    // DO NOT REMOVE!

                        chart.multibar.dispatch.on("elementClick", function(point) {
                            selectStage(point.data.x);
                        });

                        d3.selectAll('g.nv-x.nv-axis .tick.zero')
                            .on('click', function(x) {
                                if (this.classList.contains('selected')) {
                                    selectStage(null);
                                } else {
                                    selectStage(x);
                                }
                            });

                        chart.tooltip.contentGenerator(function(point) {
                            var stageName = $scope.getJourneyStageName($scope.currentFunnel.journey_type, point.data.x);
                            var status = point.data.key.toLowerCase() || '';
                            var steps = ($scope.currentFunnel)? $scope.currentFunnel.steps: [];
                            var index = steps.indexOf(point.data.x);
                            // var nps = originalData[index]['nps'][status];
                            var count = originalData[index]['count'][status];
                            var color = point.color;

                            stageName += ' (' + status + ')';

                            var template = [
                                '<table>',
                                    '<thead>',
                                        '<tr>',
                                            '<td class="legend-color-guide">',
                                                '<div style="background-color:' + color + '"></div>',
                                            '</td>',
                                            '<td>',
                                                '<strong class="x-value">' + stageName + '</strong>',
                                            '</td>',
                                        '</tr>',
                                    '</thead>',
                                    '<tbody>',
                                        '<tr>',
                                            '<td class="key">Count</td>',
                                            '<td class="value">' + count + '</td>',
                                        '</tr>',
                                        // '<tr>',
                                        //     '<td class="key">Average Bottom-up Score</td>',
                                        //     '<td class="value">' + d3.format(',.2f')(nps) + '</td>',
                                        // '</tr>',
                                    '</tbody>' +
                                '</table>'
                            ].join('');
                            return template;
                        });
                    }
                });
            };

            $scope.$on("ON_JOURNEY_TYPE_CHANGE", function () {
                $scope.funnels = _.filter($scope.allFunnels, 
                    { journey_type: $scope.filters.journey_type.id }
                );

                var isPresent = _.some($scope.funnels, { id: $scope.currentFunnelId });

                if ($scope.funnels && ! isPresent) {
                    $scope.currentFunnelId = $scope.funnels[0].id;
                    $scope.funnelSelected();
                }
            });

            $scope.$on("ON_JOURNEY_FACETS_UPDATE", function() {
                if ($scope.currentFunnel) $scope.searchDetails($scope.getJourneySearchParams());
            });
        }]);

}());

(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysPathAnalysisCtrl', JourneysPathAnalysisCtrl);

  /** @ngInject */
  function JourneysPathAnalysisCtrl($scope, $state, $http, $modal, $q, $timeout,
                                    toaster,
                                    JourneyTypesRest,
                                    MetadataService,
                                    PathAnalysisFactory) {
    var _JourneyTypesRest = new JourneyTypesRest();
    var common_path = {label: 'Common Path', measure: 'max', display_name: 'Most Common Path'};
    var configure_settings = [];
    var paths_settings = [];

    var path_settings_cache;

    var debounce = _.debounce(function () {
      if ($scope.loading) return;
      $scope.paths = [];
      $scope.initPage();
    }, 300);

    var off = [];

    var init = function () {
      angular.element('#analysis').hide();
      $scope.loading = false;

      $scope.flags = {
        isEmpty: false,
        isOverview: false,
        settingUp: false
      };

      $scope.selected = [];
      $scope.limit_list = [
        {limit: 3}, {limit: 5}, {limit: 10}, {limit: 20}, {limit: 50}
      ];

      registerShiftToDrillDownMode();

      off.push($scope.$on("ON_JOURNEY_FACETS_UPDATE", debounce));
      $scope.flags.settingUp = true;
    };

    // initialized on Facetting, State switching...
    $scope.initPage = function () {
      if (!$scope.filters.journey_type || $scope.loading) return;
      $scope.topKpaths = 1;
      paths_settings = $scope.filters.journey_type.mcp_settings || [];

      paths_settings = _.filter(paths_settings, function (p) {
        return ['Common Path', 'most_common_path'].indexOf(p.label) < 0;
      });

      var schema = _.filter($scope.filters.journey_type.journey_attributes_schema, function (s) {
        return ['integer', 'double', 'float'].indexOf(s.type) >= 0;
      });

      if (!paths_settings.length) {
        paths_settings = _.map(schema, function (each) {
          return {label: each.label, measure: 'min'};
        });
        updateJourneyType(paths_settings);
      }

      if (path_settings_cache && path_settings_cache.length) {
        paths_settings = path_settings_cache;
      }
      configure_settings = paths_settings.concat(schema);

      setTabs(paths_settings);
    };

    $scope.$on('$stateChangeSuccess',
      function (event, toState) {
        if ($scope.flags.settingUp) return;  // current state has not been set
        path_settings_cache = PathAnalysisFactory.get_path_settings();
        setTabs(path_settings_cache);
      }
    );

    function registerShiftToDrillDownMode() {
      $timeout(function () {
        $scope.analysisMode = true;
        $scope.drillDownMode = false;
      }, 0);

      d3.select('body').on('keydown', function (e) {
        if (d3.event.keyCode == 16) {
          $timeout(function () {
            $scope.analysisMode = false;
            $scope.drillDownMode = true;
          }, 0);
        }
      });

      d3.select('body').on('keyup', function (e) {
        if (d3.event.keyCode == 16) {
          $timeout(function () {
            $scope.analysisMode = true;
            $scope.drillDownMode = false;
          }, 0);
        }
      });
    }

    $scope.drillDown = function (path, index) {
      if (!$scope.drillDownMode) {
        return;
      }
      var params = {
        stagePaths: path.node_sequence_agr.join('&')
      };
      $state.go('journeys.details.mcp', params)
    };

    $scope.getNodeIcon = function (platform) {
      return MetadataService.getEventTypeIcon(platform.toLowerCase());
    };

    $scope.selectPaths = function (path, index) {
      if ($scope.drillDownMode) {
        return $scope.drillDown(path, index);
      }

      // if ($scope.flags.isOverview) return;
      if ($scope.selected.length === 2) {
        disselect();
      }
      var found = _.findWhere($scope.selected, path);
      if (!found) {
        $scope.selected.push(path);

        if ($scope.selected.length === 2 && _.uniq(_.pluck($scope.selected, 'group_by')).length === 2) {
          toaster.pop('error', 'Can not compare 2 paths with different metrics');
          disselect();
          return;
        }

        $scope.paths[index].selected = true;
      } else {
        disselect();
      }
    };

    function disselect() {
      $scope.selected = [];
      _.each($scope.paths, function (p) {
        p.selected = false;
      });
      angular.element('#analysis').hide();
    }

    $scope.configure = function () {
      var modalScope = $scope.$new();
      var _paths_labels = _.uniq(_.pluck(configure_settings, 'label'));

      modalScope.mcp_settings = _.map(_paths_labels, function (path_label) {
        var founds = _.where(configure_settings, {label: path_label});
        return _.extend({label: path_label}, {
          maxselected: angular.isDefined(_.findWhere(founds, {measure: 'max'})),
          minselected: angular.isDefined(_.findWhere(founds, {measure: 'min'}))
        });
      });

      $modal.open({
        scope: modalScope,
        templateUrl: '/omni/partials/journeys/mcp_settings'
      }).result
        .then(function (settings) {
          var selected_settings = [];
          var edited_configure_settings = [];

          _.each(_paths_labels, function (label) {
            var found = _.find(settings, {label: label});
            var _measures = [];
            if (found.maxselected) {
              _measures.push('max');
            }
            if (found.minselected) {
              _measures.push('min');
            }

            if (!found.minselected && !found.maxselected) {
              edited_configure_settings.push({label: label, measure: ''});
            }

            _.each(_measures, function (m) {
              edited_configure_settings.push({label: label, measure: m});
              selected_settings.push({label: label, measure: m});
            });
          });

          var jt_mcp_settings = _.without(selected_settings, common_path);
          updateJourneyType(jt_mcp_settings);

          configure_settings = edited_configure_settings;
          PathAnalysisFactory.set_path_settings(jt_mcp_settings);
          setTabs(jt_mcp_settings);
        });
    };

    $scope.selectTab = function (tab) {
      _.each($scope.subtabs, function (each) {
        each.active = false;
        if (tab.label === each.label) {
          each.active = true;
          tab.active = true;
        }
      });
      $scope.selectedTab = tab;
      $scope.flags.isOverview = (tab.label === 'Overview');
      $scope.selectK();
    };

    $scope.selectK = function (k) {
      var _settings = paths_settings;

      if ($scope.selectedTab.label !== 'Overview') {
        $scope.topKpaths = k || 5;
        _settings = [_.pick($scope.selectedTab, 'label', 'measure')];
        $scope.flags.isOverview = false;
      } else {
        $scope.topKpaths = 1;
        $scope.flags.isOverview = true;
      }

      getPaths(_settings);
    };

    function setTabs(list) {
      $scope.topKpaths = 1;
      var selectedTab = _.find($scope.subtabs, {active: true});
      paths_settings = list;

      $scope.subtabs = [{label: 'Overview', active: _.isUndefined(selectedTab)}];

      $scope.subtabs = $scope.subtabs.concat(_.map(list, function (p) {
        var active = (angular.isDefined(selectedTab) && selectedTab.label === p.label);
        return _.extend(p, {active: active, measure: p.measure});
      }));
      $scope.subtabs.push(common_path);

      var toSelect = selectedTab ? selectedTab : $scope.subtabs[0];
      $scope.selectTab(toSelect);
    }

    function updateJourneyType(settings) {
      var params = $scope.getJourneySearchParams();
      params.id = $scope.filters.journey_type.id;
      _.extend(params, {mcp_settings: settings});

      _JourneyTypesRest.save(params).success(function () {
        getPaths(settings);
      });
    }

    function getPaths(settings) {
      if ($scope.loading) return;
      $scope.loading = true;

      var promises = [];
      var params = $scope.getJourneySearchParams();
      $scope.paths = [];

      _.each(settings, function (each) {
        var params_copy = _.clone(params);
        _.extend(params_copy, {
          path: each,
          limit: $scope.topKpaths
        });
        promises.push($http.post('/journeys/mcp', params_copy));
      });

      $q.all(promises)
        .then(function (res) {
          var responses = _.map(res, function (r) {
            return r.data.paths.data;
          });

          $scope.paths = _.chain(_.flatten(responses))
            .map(function (each) {
              return _.extend(each, {selected: false})
            })
            .value();

          if (!$scope.paths.length) {
            $scope.loading = false;
            return;
          }

          if ($scope.selectedTab.label === 'Overview') {
            $scope.paths = _.sortBy($scope.paths, function (each) {
              return each.metrics.percentage.value;
            }).reverse();
          } else if ($scope.selectedTab.label === 'Common Path') {
            // need to verify that results are sorted - because they do not come in right queue from server
            $scope.paths = _.sortBy($scope.paths, function (each) {
              return each.metrics.percentage.value;
            });
            if ($scope.selectedTab.measure === 'max') {
              $scope.paths = $scope.paths.reverse();
            }
          } else {
            var group_by = $scope.paths[0].group_by;
            $scope.paths = _.sortBy($scope.paths, function (each) {
              return each.metrics[group_by].value;
            });
            if ($scope.selectedTab.measure === 'max') {
              $scope.paths = $scope.paths.reverse();
            }
          }

          $scope.loading = false;
          $scope.flags.settingUp = false;
        });
    }

    $scope.getGridNumber = function (stagesLength) {
      if (stagesLength === 0) return;
      var n = 12 / stagesLength;
      if (n >= 1 && n <= 3) {
        n = 2;
      }
      return n;
    };

    off.push($scope.$watch('selected', function (n) {
      if (!n) return;
      if (n.length === 2) {
        $scope.$emit("OnPathsSelected", n);
      }
    }, true));

    var destructor = function () {
      off.forEach(function (unbind) {
        unbind();
      });
      off = null;
    };

    init();
    off.push($scope.$on('$destroy', destructor));
  }
  JourneysPathAnalysisCtrl.$inject = ["$scope", "$state", "$http", "$modal", "$q", "$timeout", "toaster", "JourneyTypesRest", "MetadataService", "PathAnalysisFactory"];
})();

(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .filter('getJourneyTagName', function () {
      return function (tag_ids, tagsList) {
        var arr = [];

        _.each(_.uniq(tag_ids), function (id) {
          var found = _.find(tagsList, {id: id});

          if (found) {
            arr.push(found.display_name);
          }
        });

        return arr.join(', ').toString();
      }
    })
})();