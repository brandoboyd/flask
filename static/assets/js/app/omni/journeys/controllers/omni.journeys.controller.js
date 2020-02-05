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
})();
