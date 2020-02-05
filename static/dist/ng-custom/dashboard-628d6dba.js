'use strict';

angular.module('dashboard', [
  'ngRoute',
  'ark-dashboard',
  'ark-components',
  'ui.slimscroll',
  'ui.bootstrap',
  'slr.components',
  'omni',
  'infinite-scroll',
  'gridster',
  'ng.jsoneditor',
  'bt.jsonValidator'
])
  .config(["$routeProvider", function ($routeProvider) {
    $routeProvider
      .when('/', {
        templateUrl: '/partials/dashboard/view',
        controller: 'JourneysMultiDashboardsCtrl'
      })
      .otherwise({
        redirectTo: '/'
      });
  }])

  .filter('moment', [
    function () {
      return function (date, format) {
        return moment(date).format(format);
      };
    }
  ])

  .factory('RestTimeSeriesDataModel', ["WidgetDataModel", "$http", "FilterService", "Topics", function (WidgetDataModel, $http, FilterService, Topics) {
    function RestTimeSeriesDataModel() {
    }

    RestTimeSeriesDataModel.prototype = Object.create(WidgetDataModel.prototype);

    RestTimeSeriesDataModel.prototype.init = function (callback) {
      WidgetDataModel.prototype.init.call(this);

      var params = this.dataModelOptions ? this.dataModelOptions.params : {};
      var wAttrs = this.widgetScope.widget.attrs;
      var range_alias = wAttrs.extra_settings.range_alias;
      var settings    = _.extend({}, wAttrs.settings);
      var date_range  = FilterService.getDateRangeByAlias(range_alias);

      var old_from = wAttrs.settings.from;
      var old_to   = wAttrs.settings.to;

      //amend settings
      settings.from = date_range ? date_range.from.toString("MM/dd/yyyy") : old_from;
      settings.to   = date_range ? date_range.to.toString("MM/dd/yyyy")   : old_to;

      var get_topic_type = function(el) {
        if (el.hasOwnProperty('term_count')) {
          return (el.term_count === el.topic_count ? "leaf" : "node");
        } else if (el.hasOwnProperty('topic_type')) {
          return el.topic_type;
        }
      };

      var chartModel = this;
      var fetchTrendsData = function(settings) {
        var request_url = settings.request_url || 'trends/json';
        delete settings.request_url;
        $http.post(request_url, settings).success(function(d) {
          var chart = { data      : d.list, settings  : wAttrs.settings, widget_id : wAttrs.id, extra_settings : wAttrs.extra_settings };
          WidgetDataModel.prototype.updateScope.call(chartModel, chart);
          callback();
        }.bind(chartModel))
      }

      if(wAttrs.extra_settings.topics != null) {
        var topicParams = wAttrs.extra_settings.topics;
        var limit = 10;

        topicParams.from = date_range ? date_range.from.toString("MM/dd/yyyy") : old_from;
        topicParams.to   = date_range ? date_range.to.toString("MM/dd/yyyy")   : old_to;

        Topics.fetch(topicParams, limit).then(function(res) {
          if(angular.isArray(res)) {
            var topics = [];
            _.each(res, function(el) {
              topics.push({
                'topic'      : el.topic,
                'topic_type' : get_topic_type(el),
                'parent'     : el.parent,
                'level'      : el.level
              })
            })
            settings.topics = topics;
            fetchTrendsData(settings);
          }
        });
      } else {
        fetchTrendsData(settings);
      }

    };

    return RestTimeSeriesDataModel;
  }])

  .directive('wtPlotter', ["$interval", "$compile", function ($interval, $compile) {
    return {
      replace: true,
      template: '<div style="height:100%;width:100%;"></div>',
      scope : {
        chart   : '='
      },
      link: function (scope, el) {

        scope.$watch('chart', function (chart) {

          if (chart) {
            el.empty();
            if (chart.extra_settings.widget_type && chart.extra_settings.widget_type == 'topics') {
              var topics = $compile("<div widget-topics-cloud settings='chart' widget-id='widget_id' style='height:100%; width:100%'></div>")(scope);
              el.append(topics);

            } else if (['OMNI', 'OMNI_AGENTS', 'OMNI_CUSTOMERS', 'PREDICTORS'].indexOf(chart.extra_settings.target) !== -1) {
              el.html("<journey-chart chart-data='data' widget-id='widget_id' plot-options='plot_options' extra-settings='extra_settings'>");
              $compile(el.contents())(scope);
              scope.extra_settings = chart.extra_settings || null;
            } else {
              var plot = $compile("<div widget-plotter='data' widget-id='widget_id' plot-options='plot_options' style='height:100%; width:100%'></div>")(scope);
              el.append(plot);
            }

            scope.data = chart.data;
            scope.plot_options = chart.settings ? chart.settings : null;
            scope.widget_id = chart.widget_id ? chart.widget_id : null;
          }
        });
      }
    };
  }])

  .directive('widgetTopicsCloud', ["$interval", "$compile", "Topics", function ($interval, $compile, Topics) {
    function fetch(scope, params) {
      var limit = params.plot_type ? 15 : null;
      return Topics.fetch(params, limit).then(function(d) {
        scope.topics = _.defaults(d, {active : ''});
        scope.count_max = _.max(scope.topics, function(topic) { return topic.term_count} )['term_count'];
        scope.count_min = _.min(scope.topics, function(topic) { return topic.term_count} )['term_count'];
      });
    }

    return {
      replace: false,
      scope : {
        settings : '='
      },
      template: '<div class="tagcloud maincloud widget-tagcloud"><ul><li ng-repeat="item in topics | orderBy:\'topic\':reverse"  ng-style="getTopicSize(item.term_count)[\'log\']"><span ng-bind="item.topic"></span></li></ul></div>',
      link: function (scope, el) {
        scope.getTopicSize = function(count) {
          var fontMin = 12,
            fontMax = 40;
          var size = count == scope.count_min ? fontMin
            : (Math.log(count) / Math.log(scope.count_max)) * (fontMax - fontMin) + fontMin;
          var styles = {log : { 'font-size' : size + 'px'}};
          return styles;
        };
        scope.$watch('settings', function(nVal, oldVal) {
          if (nVal) {
            //console.log(nVal.extra_settings.topics_params);
            if (!nVal.extra_settings.topics_params) {
              return;
            }
            fetch(scope, nVal.extra_settings.topics_params);
          }

        })

      }
    };
  }]);


(function () {
    'use strict';

    angular.module('dashboard')
        .factory('FacetFactory', FacetFactory);

function FacetFactory($http, $q, FilterService) {
    var currentPage = '';
    var pages = ['nps', 'journeys', 'agents', 'customers'];
    var fetchDone = false;
    var facets = {
        channels            : {field: 'id',   pages: ['journeys', 'nps']},
        smart_tags          : {field: 'id',             pages: ['nps']},
        segments            : {field: 'display_name',   pages: ['journeys', 'agents', 'customers']},
        journey_types       : {field: 'id',             pages: ['journeys']},
        journey_stages      : {field: 'display_name',   pages: ['journeys']},
        journey_tags        : {field: 'id',             pages: ['journeys']},
        journey_statuses    : {field: 'display_name',   pages: ['journeys']},
        age_groups          : {field: 'display_name',   pages: ['agents', 'customers']},
        industries          : {field: 'display_name',   pages: ['agents', 'customers']},
        customer_statuses   : {field: 'display_name',   pages: ['customers']},
        nps                 : {field: 'value',          pages: ['journeys']}
        //call_intents        : {id: 'intent',        pages: ['customers']}
    };
    var optionsLoaded = false;

    var mappings = {        // Mapping for dashboard attributes and post params
        'nps': {
            'channels': '',
            'smart_tags': ''
        },
        'journeys': {
            'channels'          : '',
            'smart_tags'        : '',
            'segments'          : 'customer_segments',
            'nps'               : '',
            'journey_tags'      : '',
            'journey_types'     : 'journey_type',
            'journey_stages'    : 'stage',
            'journey_statuses'  : 'status'
        },
        'agents': {
            'segments'  : '',
            'industries': '',
            'age_groups': ''
        },
        'customers': {
            'segments': '',
            'industries': '',
            'age_groups': '',
            'customer_statuses': ''
        }
    };

    var reset = function() {
        _.each(facets, function(facet, key) {
            facets[key].visible = facets[key].pages.indexOf(currentPage) > -1;
            //facets[key].all = true;
            facets[key].list = [];
        });
    };

    var fetchChannels = function() {
        if (facets.channels.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.post('/channels_by_type/json', {type: 'inbound', serviced_only : false, parent_names  : true})
            .success(function(resp) {
                var list = resp.list;
                if (currentPage == 'nps') {
                    list = _.filter(list, {'platform': 'VOC'});
                }
                facets.channels.list = _.map(list, function(item) {
                    return {id: item.id, display_name: item.title, enabled: false};
                });
            });
    };

    var fetchSmartTags = function() {
        if (facets.smart_tags.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/smart_tags/json')
            .success(function(resp) {
                facets.smart_tags.list = _.map(resp.list, function(item) {
                    return {id: item.id, display_name: item.title, enabled: false};
                });
            });
    };

    var fetchJourneyTypes = function() {
        if (facets.journey_types.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/journey_types')
            .success(function(resp) {
                facets.journey_types.list = _.map(resp.data, function(item) {
                    return {id: item.id, display_name: item.display_name, enabled: false};
                });
            });
    };

    var fetchJourneyStages = function(journeyTypeId) {
        if (facets.journey_stages.pages.indexOf(currentPage) == -1 ) return $q.when();
        if(!journeyTypeId) return $q.when();
        return $http.get('/journey_types/{jid}/stages'.replace('{jid}', journeyTypeId))
            .success(function(resp) {
                facets.journey_stages.list.length = 0;
                facets.journey_stages.list = _.map(resp.data, function(item) {
                    return {id: item.id, display_name: item.display_name, enabled: false};
                });
            });
    };

    var fetchJourneyTags = function(journeyTypeId) {
        if (facets.journey_tags.pages.indexOf(currentPage) == -1 ) return $q.when();
        var url = '/journey_tags';
        if (journeyTypeId) url += '?journey_type_id=' + journeyTypeId;
        return $http.get(url)
            .success(function(resp) {
                facets.journey_tags.list.length = 0;
                facets.journey_tags.list = _.map(resp.data, function(item) {
                    return {
                        id : item.id,
                        display_name : item.display_name,
                        enabled : false,
                        jtId : item.journey_type_id
                    };
                });
            });
    };

    var fetchSegments = function() {
        if (facets.segments.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/customer_segments')
            .success(function(resp) {
                var items = resp.list;
                facets.segments.list.length = 0;
                facets.segments.list.push({
                    display_name: 'N/A'
                });
                facets.segments.list = _.map(resp.list, function(item) {
                    return {'display_name': item.display_name, enabled: false};
                });
            });
    };

    var fetchIndustries = function() {
        if (facets.industries.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/customer_industries/json')
            .success(function(resp) {
                facets.industries.list.length = 0;
                _.each(resp.list, function(item) {
                    if (item) facets.industries.list.push({'display_name': item, enabled: false});
                });
            });
    };

    var fetchJourneyStatus = function() {
        if (facets.journey_statuses.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.journey_statuses.list = FilterService.getJourneyStatus();
        return $q.when();
    };

    var fetchNPS = function() {
        if (facets.nps.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.nps.list = FilterService.getNPSOptions();
        return $q.when();
    };

    var fetchAgeGroups = function() {
        if (facets.age_groups.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.age_groups.list = FilterService.getAgeGroups();
        return $q.when();
    };

    var fetchCustomerStatuses = function() {
        if (facets.customer_statuses.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.customer_statuses.list = FilterService.getCustomerStatuses();
        return $q.when();
    };

    var setJourneyType = function(journeyTypeId) {
        return $q.all([
            fetchJourneyTags(journeyTypeId),
            //fetchJourneyStages(journeyTypeId)
        ]).then(function() {
            facets.journey_tags.visible = (journeyTypeId != null || journeyTypeId != undefined);
            //facets.journey_stages.visible = (journeyTypeId != null || journeyTypeId != undefined);
        });
    };

    function fetchFacetOptions(filters) {
        fetchDone = false;
        reset();
        var deferred = $q.defer();

        $q.all([
            fetchChannels(),
            fetchSmartTags(),
            fetchJourneyTypes(),
            fetchJourneyStatus(),
            //fetchJourneyTags(),
            //fetchJourneyStages(),
            fetchIndustries(),
            fetchSegments(),
            fetchNPS(),
            fetchAgeGroups(),
            fetchCustomerStatuses()
        ])
        .then(function(resp) {
            //var facetsToLoad = {'journey_type': null};
            //if (filters.facets) {
            //    facetsToLoad = filters.facets;
            //    if (facetsToLoad.journey_type) {
            //        facets['journey_types'].selected = facetsToLoad.journey_type;
            //    }
            //}
            //$q.all([
            //    fetchJourneyTags(facetsToLoad.journey_type),
            //    fetchJourneyStages(facetsToLoad.journey_type)
            //]).then(function() {
                fetchDone = true;
                deferred.resolve(filters.facets);
            //})
        });

        return deferred.promise;
    }

    function getFacetParams() {
        var mapping = mappings[currentPage];
        var filters = {};
        if (mapping) {
            _.each(mapping, function(output, key) {
                if (output == '') output = key;
                if (key == 'journey_types') {
                    filters[output] = (facets.journey_types.selected)? [facets.journey_types.selected] : [];
                    return;
                }
                var field = facets[key]['field'];
                var params = _.pluck(_.filter(facets[key].list, {'enabled': true}), field);
                filters[output] = params.length? params: [];
            });
        }
        return filters;
    }

    function loadFacets(settings) {

        function load() {
            var mapping = mappings[currentPage];

            _.each(mapping, function(output, key) {
                if (output == '') output = key;
                var field = facets[key].field;
                if (output == 'journey_type') {
                    facets[key].all = true;
                    if (!settings.journey_type) {
                        facets[key].selected = null;
                    } else if (!angular.isArray(settings.journey_type)) {
                        facets[key].selected = settings.journey_type;
                    } else {
                        facets[key].selected = settings.journey_type[0];
                    }
                    return;
                }
                _.each(facets[key].list, function(option, index) {
                    _.each(settings[output], function(item) {
                        if (item == option[field]) {
                            facets[key].all = false;
                            facets[key]['list'][index].enabled = true;
                        }
                    });
                });
            });

            optionsLoaded = true;
            return $q.when();
        }

        if (!fetchDone) {
            fetchFacetOptions()
                .then(load);
        } else {
            load();
        }
    }

    return {
        getPage: function() {
            return currentPage;
        },
        fetchAndLoadFacets: function(page, filters) {
            var deferred = $q.defer();
            optionsLoaded = false;
            if (pages.indexOf(page) == -1) {

            } else {
                currentPage = page;
                fetchFacetOptions(filters)
                    .then(loadFacets)
                    .then(function() {
                        deferred.resolve();
                    });
            }
            return deferred.promise;
        },
        getFacets: function() {
            return facets;
        },
        isOptionsLoaded: function() {
            return optionsLoaded;
        },
        getFacetParams: getFacetParams,
        loadFacets: loadFacets,
        setJourneyType: setJourneyType
    }
}
FacetFactory.$inject = ["$http", "$q", "FilterService"];

}());
(function () {
  'use strict';

  angular.module('dashboard')
    .controller('JourneysMultiDashboardsCtrl',
    ["$scope", "$http", "$q", "$window", "$timeout", "$modal", "SeriesDataModel", "TopicsDataModel", "NPSDataModel", "JourneyDataModel", "DashboardStorage", "FacetFactory", "FilterService", "DashboardState", "LayoutStorage", "AccountsService", "SystemAlert", function ($scope, $http, $q, $window,
              $timeout, $modal, SeriesDataModel, TopicsDataModel, NPSDataModel, JourneyDataModel,
              DashboardStorage, FacetFactory,
              FilterService, DashboardState, LayoutStorage, AccountsService, SystemAlert) {

      var init = function() {
        $http.get('/gallery')
          .success(function(res) {
            $scope.galleries = res.data;
          });

        $scope.getLayouts = function () {
          var layouts = [];

          $q.all([
            $http.get('/dashboards')
          ]).then(function (res) {
            //Iterates dashboards one by one
            $scope.dashboards = res[0].data.data;

            _.each($scope.dashboards, function (dashboard) {

              //Creates layouts for each dashboard
              var obj = {
                id: dashboard.id,
                type_id: dashboard.type_id,
                title: dashboard.title,
                owner: dashboard.owner_name,
                author: dashboard.author_name,
                accountId: dashboard.account_id,
                ownerId: dashboard.owner,
                authorId: dashboard.author,
                filters: dashboard.filters,
                active: false,
                locked: false,
                isTypeDefault: dashboard.type == 'blank',
                dashboardType: dashboard.type,
                defaultWidgets: [],
                widgetDefinitions: [],
                shared_to: dashboard.shared_to
              };
              layouts.push(obj);
            });
            DashboardStorage.updateList(layouts);

            $scope.$broadcast('readyLayouts', layouts);
          });
        };

        var widgetDefinitions = [{
          name: 'chart',
          template: '<chart widget-id="widgetData.widget_id" chart-data="widgetData.data" settings="widgetData.extra_settings" />',
          dataModelType: SeriesDataModel,
          dataModelOptions: {},
          enableVerticalResize: false
        }, {
          name: 'trend-chart',
          template: '<trend-chart widget-id="widgetData.widget_id" chart-data="widgetData.data" post-params="widgetData.settings" extra-info="widgetData.extra_settings" />',
          dataModelType: SeriesDataModel,
          dataModelOptions: {},
          enableVerticalResize: false
        }, {
          name: 'distribution-chart',
          template: '<distribution-chart widget-id="widgetData.widget_id" chart-data="widgetData.data" post-params="widgetData.settings" extra-info="widgetData.extra_settings" />',
          dataModelType: SeriesDataModel,
          dataModelOptions: {},
          enableVerticalResize: false
        }, {
          name: 'topics-cloud',
          template: '<topics-cloud settings="widgetData.extra_settings"/>',
          dataModelType: TopicsDataModel,
          dataModelOptions: {},
          enableVerticalResize: false
        }, {
          name: 'sankey-chart',
          template: '<sankey-chart widget-id="widgetData.widget_id" chart-data="widgetData.data" post-params="widgetData.settings" extra-info="widgetData.extra_settings" />',
          dataModelType: SeriesDataModel,
          dataModelOptions: {},
          enableVerticalResize: false
        }, {
          name: 'funnel-chart',
          template: '<funnel-chart widget-id="widgetData.widget_id" chart-data="widgetData.data" post-params="widgetData.settings" extra-info="widgetData.extra_settings" class="funnel-chart"/>',
          dataModelType: SeriesDataModel,
          dataModelOptions: {},
          enableVerticalResize: false
        }, {
          name: 'add-widget',
          template: '<add-widget settings="widgetData.extra_settings"/>',
          dataModelOptions: {},
          enableVerticalResize: false
        }];

        var templateString = '<{{widget_name}} widget-id="widgetData.widget_id" chart-data="widgetData.data" post-params="widgetData.settings" cross-filter="widgetData.crossFilter"/>';
        var journeyDashWidgets = ['journey-volumes-by-journey-type', 'nps-by-journey-type', 'nps-trends', 'nps-by-journey-tag', 'status-by-journey-type'];
        var npsDashWidgets = ['stacked-bar-chart', 'distrib-bar-chart', 'horizontal-bar-chart', 'pie-chart', 'trend-bar-chart'];

        _.each(npsDashWidgets, function(widget) {
          widgetDefinitions.push({
            name: widget,
            template: templateString.replace('{{widget_name}}', widget),
            dataModelType: NPSDataModel,
            dataModelOptions: {},
            enableVerticalResize: false
          });
        });

        _.each(journeyDashWidgets, function(widget) {
          widgetDefinitions.push({
            name: widget,
            template: templateString.replace('{{widget_name}}', widget),
            dataModelType: JourneyDataModel,
            dataModelOptions: {},
            enableVerticalResize: false
          });
        });

        $scope.layoutOptions = {
          widgetButtons: true,
          widgetDefinitions: widgetDefinitions
        };
        $scope.lastWidget = false;
      };

      $scope.selectedLayout = {};
      $scope.facets = {};

      $scope.selectDashboard = function(dashboard) {

        if ($scope.selectedLayout) $scope.selectedLayout.isDetailView = false;
        //get the contents of the selected dashboard
          $http.get('/dashboards/' + dashboard.id)
            .success(function(res){
              var dashboard = res.data;

              $scope.lastWidget = false;
              $timeout(function() {
                $scope.lastWidget = true;
              }, 300);

              var widgets = dashboard.widgets;
              //Calculates widget definitions for each widget
              widgets = _.map(widgets, function (widget) {
                var settings = widget.settings;
                var extraSettings = widget.extra_settings;
                var style = widget.style || {};
                return {
                  name: extraSettings.directive || settings.directive,
                  title: widget.title,
                  style: style || {},
                  sizeX: style.sizeX || 3,
                  sizeY: style.sizeY || 2,
                  row: style.row,
                  col: style.col,
                  attrs: {
                    id: widget.id,
                    dashboard_id: dashboard.id,
                    description: widget.description,
                    view_url: (extraSettings.source) ? (extraSettings.source + widget.id) : '',
                    settings: settings || {},
                    extra_settings: extraSettings || {}
                  }
                };
              }); //map

              if (dashboard.type !== 'blank') {
                widgets.push({
                  name: 'add-widget',
                  title: '',
                  sizeX: 1, sizeY: 1, maxSizeX: 1, maxSizeY: 1,
                  row: 10000,
                  col: 0,
                  attrs: {
                    id: '', dashboard_id: dashboard.id, description: 'Add a Widget', isAddWidget: true
                  }
                });
              }

              var dashboards = _.values(_.extend({}, DashboardStorage.getDashboardsList()));
              var currentDashboard = _.find(dashboards, function(d) {return d.id == dashboard.id});
              if (widgets.length && currentDashboard.dashboard) {
                currentDashboard.dashboard.loadWidgets(widgets);
              }

              DashboardStorage.updateList(dashboards);

              $scope.selectedLayout = currentDashboard;
              $scope.selectedLayout.isFilterShown = true;

              FacetFactory.fetchAndLoadFacets(dashboard.type, dashboard.filters)
                  .then(function() {
                    $scope.facets = FacetFactory.getFacets();
                    loadDateFilter($scope.selectedLayout);
                  });
            })
            .error(function(res){
              console.log("ERROR GETTING WIDGETS!", res);
            });

      };

      $scope.addNewWidget = function() {
        $modal.open({
          scope: $scope.$new(),
          templateUrl: '/partials/dashboard/new-widget-modal',
          controller: 'NewWidgetCtrl',
          size: 'lg',
          resolve: {
            selectedDashboard: function() {
              var galleryId = _.findWhere($scope.galleries, {dashboard_type: $scope.selectedLayout.type_id}).id;
              return _.extend($scope.selectedLayout, {galleryId: galleryId});
            }
          }
        });
      };

      $scope.shareDashboard = function (dashboard) {
        $modal.open({
          scope: $scope.$new(),
          templateUrl: '/partials/dashboard/share-dashboard-modal',
          controller: 'ShareDashboardCtrl',
          resolve: {
            dashboard: function() {
              return $scope.selectedLayout;
            }
          }
        });
      };

      $scope.updateDashboard = function (dashboard) {
        $http.put('/dashboards/' + dashboard.id, {
          title: dashboard.title
        }).success(function () {
          SystemAlert.success('Dashboard has been renamed.');
        });
      };

      $scope.updateSizeAndPosition = function(dashboardId, widgetData) {
        $http.get('/dashboards/' + dashboardId)
          .success(function(res) {
            var widgets = res.data.widgets;
            _.each(widgets, function(widget) {
              var updateUrl = '/dashboard/' + widget.id + '/update';
              var target = _.find(widgetData, function(w) {
                if (w.attrs.id == widget.id) return true;
              });
              if (target) {
                widget.style = widget.style || {};
                angular.extend(widget.style, _.pick(target, ['row', 'col', 'sizeX', 'sizeY']));
                $http.post(updateUrl, {style: widget.style});
              }
            });
          })
      };

      $scope.removeDashboard = function (dashboard) {
        $http.delete('/dashboards/' + dashboard.id)
          .success(function () {
            DashboardStorage.remove(dashboard.id);
            SystemAlert.success('Dashboard has been removed.');
          });
      };

      $scope.deleteWidget = function (widgetId) {
        return $http.delete('/dashboard/' + widgetId + '/remove');
      };

      $scope.updateWidget = function (widget) {
        var url = '/dashboard/' + widget.attrs.id + '/update';
        $http.post(url, {title: widget.title})
          .success(function () {
            SystemAlert.success('Widget has been renamed.');
          });
      };

      $scope.openWidgetTab = function (widget) {
        // If the widget has account settings, restore that settings otherwise just redirect.
        //var account = (widget.attrs.extra_settings) ? widget.attrs.extra_settings.account_info : null;
        //if (account) {
        //  AccountsService.update(widget.attrs.extra_settings.account_info, function () {
        //    //$window.location = widget.attrs.view_url;
        //    $window.open(widget.attrs.view_url);
        //  });
        //} else if (widget.attrs.view_url) {
        //  $window.open(widget.attrs.view_url);
        //}

        // If the current account doesn't match the account whom created the widget, don't allow expansion.
        // ref: https://jira.genesys.com/browse/TAP-1253
        var widgetAccount = (widget.attrs.extra_settings) ? widget.attrs.extra_settings.account_info : null;
        var currentAccount = AccountsService.getCurrent();
        if (widgetAccount && currentAccount && widgetAccount.selected_app != currentAccount.selected_app) {
          SystemAlert.warn('Cannot expand this widget!');
        } else if (widget.attrs.view_url) {
          $window.open(widget.attrs.view_url);
        }
      };

      $scope.$on('pipeDash', function(e, dash) {
        $scope.$broadcast("dashboardBuilt", dash);
      });

      $scope.$on('WIDGET_ADDED', function(e, dashboardId) {
        $scope.selectDashboard({'id': dashboardId});
        $scope.resetCrossFilter(false);
      });

      $scope.addNewDashboard = function(dash) {
        DashboardStorage.add(dash);
      };

      $scope.buildDashboard = function () {
        $modal.open({
          scope: $scope.$new(),
          templateUrl: '/partials/dashboard/create-dashboard-modal',
          controller: 'NewDashboardCtrl',
          size: 'lg'
        });
      };

      $scope.switchViewMode = function() {
        if (!$scope.selectedLayout) {
          return;
        }

        if ($scope.selectedLayout.isDetailView === true) {
          $scope.selectedLayout.isDetailView = false;
          DashboardStorage.update({ id: $scope.selectedLayout.id });
          // $scope.selectDashboard({ id: $scope.selectedLayout.id });
        } else {
          $scope.selectedLayout.isDetailView = true;
          $scope.$broadcast('UNLOAD_DETAILS_VIEW');
        }
      };

      $scope.toggleFilters = function() {
        if ($scope.selectedLayout) {
          $scope.selectedLayout.isFilterShown = !$scope.selectedLayout.isFilterShown;
        }
      };

      $scope.updateFacets = function(data) {
        updateFacets();
      };

      $scope.$on(FilterService.DATE_RANGE_CHANGED, function() {
        $scope.currentDate = FilterService.getSelectedDateRangeName();
        updateFacets();
      });

      var updateFacets = _.debounce(function () {
        $scope.$broadcast("ON_JOURNEY_FACETS_UPDATE");
      }, 1000);

      $scope.$on("ON_JOURNEY_FACETS_UPDATE", function() {
        if (FacetFactory.isOptionsLoaded()) {
          saveDashboardFilters($scope.selectedLayout).then(function() {
            if ($scope.selectedLayout.isDetailView) {
              $scope.$broadcast('LOAD_DETAILS_VIEW');
            }
          });

          $scope.resetCrossFilter(false);
        }
      });

      $scope.$watch('facets.journey_types.selected', function(nVal, oVal) {
        FacetFactory.setJourneyType(nVal);
      });

      $scope.getCurrentFilters = function() {
        return {
          'facets': FacetFactory.getFacetParams(),
          'period': {
            'alias': FilterService.getSelectedDateRangeAlias()
          }
        }
      };

      function saveDashboardFilters(dashboard) {
        if (!dashboard || dashboard.isTypeDefault) {
          return $q.when();
        }

        var currentFilters = $scope.getCurrentFilters();
        var previousFilters = dashboard.filters || {};

        if (_.isEqual(currentFilters, previousFilters)) {
          return $q.when();
        } else {
          return $http.put('/dashboards/' + dashboard.id, {
            filters: currentFilters
          }).success(function(resp) {
            dashboard.filters = resp.data.filters;
            DashboardStorage.update(dashboard);
            SystemAlert.success('Dashboard settings have been changed.');
          });
        }
      }

      function loadDateFilter(dashboard) {
        if (!dashboard || dashboard.isTypeDefault) return;

        if (dashboard.filters) {
          var filters = dashboard.filters;
          var period = filters['period'];
          if (period && period.alias) {
            FilterService.setDateRangeByAlias(period.alias);
          }

          DashboardStorage.update(dashboard);
        }
      }

      $scope.getJourneyTagName = function(tag_id) {
        var tag = _.find($scope.facets.journey_tags.list, function(t) { return t.id === tag_id});
        return tag ? (tag.display_name) : 'N/A';
      };

      $scope.getJourneyTagFullName = function(tag_id) {
        var tag = _.find($scope.facets.journey_tags.list, function(t) { return t.id === tag_id});
        if (tag) {
          var jtName = $scope.getJourneyTypeName(tag.jtId);
          return jtName + '.' + tag.display_name;
        }
        return 'N/A';
      };

      $scope.getJourneyTypeName = function(type_id) {
        var type = _.find($scope.journey_types_list, function(t) { return t.id === type_id});
        return type ? (type.display_name) : 'N/A';
      };

      $scope.resetCrossFilter = function(refreshWidgets) {
        // refreshWidgets is set to true, when "Clear FilterService" button is clicked
        if ($scope.selectedLayout.id) {
          DashboardStorage.resetCrossFilter($scope.selectedLayout.id, refreshWidgets);
        }
        $scope.showBreadcrumbs = false;
        $scope.breadcrumbs = {
          journey_type: {
            display_name: 'Journey Types',
            list: [ ]
          },
          journey_tags: {
            display_name: 'Journey Tags',
            list: [ ]
          },
          status: {
            display_name: 'Journey Status',
            list: [ ]
          },
          nps: {
            display_name: 'NPS',
            list: [ ]
          },
          date_subrange: {
            display_name: 'Date Range',
            list: [ ]
          }
        };
      };

      $scope.removeCrossFilter = function(key, value)  {
        DashboardStorage.removeCrossFilter($scope.selectedLayout.id, {
          key: key,
          value: value
        });

        var crossFilter = DashboardStorage.getCrossFilter($scope.selectedLayout.id);
        prepareBreadcrumbs($scope.breadcrumbs, crossFilter);
      };

      $scope.$on("CROSSFILTER_CHANGED", function(evt, newFilter) {
        DashboardStorage.setCrossFilter($scope.selectedLayout.id, newFilter);
        var crossFilter = DashboardStorage.getCrossFilter($scope.selectedLayout.id);
        prepareBreadcrumbs($scope.breadcrumbs, crossFilter);
      });

      function prepareBreadcrumbs(breadcrumbs, crossFilter) {
        // Prepare display texts for crossfilter items
        breadcrumbs.journey_type.list = _.map(crossFilter.journey_type, function(journeyTypeId) {
          return {
            value: journeyTypeId,
            display_name: $scope.getJourneyTypeName(journeyTypeId)
          }
        });
        breadcrumbs.journey_tags.list = _.map(crossFilter.journey_tags, function(journeyTagId) {
          return {
            value: journeyTagId,
            display_name: $scope.getJourneyTagFullName(journeyTagId)
          }
        });
        breadcrumbs.status.list = _.map(crossFilter.status, function(status) {
          return {
            value: status,
            display_name: status
          }
        });
        breadcrumbs.nps.list = _.map(crossFilter.nps, function(nps) {
          return {
            value: nps,
            display_name: nps
          }
        });
        if (!_.isEmpty(crossFilter.date_subrange)) {
          breadcrumbs.date_subrange.list = [{
            value: null,
            display_name: crossFilter.date_subrange.fromDate + ' - ' + crossFilter.date_subrange.toDate
          }]
        } else {
          breadcrumbs.date_subrange.list = [ ]
        }

        $scope.showBreadcrumbs =
          (breadcrumbs.journey_type.list.length > 0) ||
          (breadcrumbs.journey_tags.list.length > 0) ||
          (breadcrumbs.status.list.length > 0) ||
          (breadcrumbs.nps.list.length > 0) ||
          (breadcrumbs.date_subrange.list.length > 0);
      }

      init();
    }])

      .controller('DashboardDetailsCtrl', ["$http", "$q", "$scope", "$modal", "$timeout", "DashboardStorage", "FilterService", function($http, $q, $scope, $modal, $timeout, DashboardStorage, FilterService) {

        $scope.reloadData = function() {
          $scope.dashboardType = $scope.selectedLayout.dashboardType;
          $scope.dashboardId = $scope.selectedLayout.id;

          $scope.postParams = DashboardStorage.getBaseFilterParams($scope.dashboardId);
          delete $scope.postParams.range_alias;

          $scope.resetPagination();

          // For journey-type dashboards
          $scope.journeys = [];
          $scope.journeysTable = {
            sort: {
              predicate: 'customer_name',
              reverse: false
            }
          };

          // For NPS-type dashboards
          $scope.tableData = [];

          if ($scope.dashboardType == 'journeys') {
              $scope.searchJourneyDetails();
          } else if ($scope.dashboardType == 'nps') {
              $scope.tableData = DashboardStorage.getStoredData($scope.dashboardId);
              $scope.loading = false;
          }
        };

        $scope.resetPagination = function() {
          $scope.offset = 0;
          $scope.limit = 30;
          $scope.journeys = [];
          $scope.hasMore = true;
          $scope.loading = false;
        };

        $scope.loadMore = function() {
          $scope.searchJourneyDetails();
        };

        $scope.searchJourneyDetails = function() {
          if ( !$scope.hasMore || !$scope.postParams) return;

          $scope.loading = true;
          $scope.params = _.assign(
            {},
            DashboardStorage.getFullFilterParams($scope.dashboardId),
            {
              offset: $scope.offset,
              limit: $scope.limit,
              short_fields: 'true'
            }
          );
          delete $scope.params.range_alias;

          $http.post('/journeys/json', $scope.params).success(function (resp) {
            $scope.hasMore = resp.more_data_available;
            $scope.journeys = $scope.journeys.concat(resp.list);
            $scope.offset += resp.list.length;
            $scope.loading = false;
          }, function(err) {
            $scope.loading = false;
          });
        };

        $scope.getTimelineParams = function (journey) {
          var journeyTags = _.map(journey.journey_tags, function (id) {
            return {
              id: id, title: $scope.getJourneyTagName(id)
            };
          });

          var from = moment($scope.params.subrange_from || $scope.params.from, 'YYYY-MM-DD HH:mm').format('MM/DD/YYYY');
          var to = moment($scope.params.subrange_to || $scope.params.to, 'YYYY-MM-DD HH:mm').format('MM/DD/YYYY');

          return angular.extend({
                from: from,
                to: to
            }, {
              assignedTags: journeyTags,
              customer_id: journey.customer_id
            }
          );
        };

        $scope.reloadData();

        $scope.$on("LOAD_DETAILS_VIEW", function() {
          $scope.reloadData();
        });

        $scope.$on("UNLOAD_DETAILS_VIEW", function() {
          $scope.journeys.length = 0;
          $scope.tableData.length = 0;
        });

      }]);
}());

(function() {
  'use strict';
  angular.module('dashboard')
    .controller('NewDashboardCtrl', ["$scope", "$modalInstance", "$http", "$timeout", function($scope, $modalInstance, $http, $timeout) {

      var init = function() {
        $scope.dashboardTitle = '';
        $scope.flags = {
          isGallery: false,
          isShared: false,
          isFetched: false
        };
      };

      /** From shared dashboards */
      $scope.fromShared = function() {
        $scope.flags.isShared = true;
        $scope.sharedFilters = {
          title: ''
        };
        $http.get('/dashboards/shared_to_me')
          .success(function(res) {
            $scope.flags.isFetched = true;
            $scope.sharedDashboards = _.map(res.data, function(d) {
              return _.extend(d, {selected: false});
            });
          });
      };

      $scope.selectShared = function(shared) {
          $scope.chosenShared = shared;
      };

      $scope.buildFromShared = function(title) {
        var parent_dashboard_id = $scope.chosenShared.id;
        $http.post('/dashboards/' + parent_dashboard_id + '/copy', {
          title: title
        }).success(function (res) {
          $scope.$emit("pipeDash", res.data);
          $modalInstance.close();
        });

      };

      /** From Gallery */
      $scope.fromGallery = function() {
        $scope.flags.isGallery = true;
        $scope.galleryFilters = {
          display_name: ''
        };

        $http.get('/dashboards/type')
          .success(function (res) {
            var blankType = _.filter(res.data, { type: 'blank' });

            $scope.flags.isFetched = true;
            $scope.dashboardTypes = _.map(blankType, function(d) {
              return _.extend(d, {selected: false});
            });
          });
      };

      $scope.selectType = function (selectedType) {
        _.each($scope.dashboardTypes, function (type) {
          type.selected = false;
          if (type.id === selectedType.id) {
            type.selected = true;
            $scope.selectedType = selectedType;
          }
        });
      };

      $scope.buildFromGallery = function(title) {
        build($scope.selectedType.id, title);
      };

      $scope.back = function() {
        init();
      };

      function build(typeId, title) {
        $http.post('/dashboards', {
          type_id: typeId,
          title: title,
          widgets: [],
          filters: {
            'facets': {},
            'period': {
              'alias': 'today'
            }
          }
        }).success(function (res) {
          $scope.$emit("pipeDash", res.data);
          $modalInstance.close();
        });
      }

      $scope.keyPressed = function (e) {
        if (e.which === 13) {
          $modalInstance.close();
        }
      };

      init();
    }]);
}());

(function() {
  'use strict';
  angular.module('dashboard')
    .controller('NewWidgetCtrl', ["$scope", "$http", "$q", "$modalInstance", "$timeout", "$window", "selectedDashboard", "WidgetService", "SystemAlert", "jsonValidator", "jsonSchemaCache", function($scope, $http, $q, $modalInstance, $timeout, $window, selectedDashboard, WidgetService, SystemAlert, jsonValidator, jsonSchemaCache) {

      $scope.isLoading = true;
      var url = '/gallery/' + selectedDashboard.galleryId + '/widget_models';
      var init = function() {
        $scope.dashboard = selectedDashboard;
        if ($scope.dashboard.isTypeDefault) {

        } else {
          $http.get(url)
            .success(function(res) {
              $scope.isLoading = false;
              $scope.widgetModels = res.data;
            });
        }

        $scope.widget = {
          title: '',
          description: '',
          model: {},
          dashboard_id: selectedDashboard.id,
          settings: {},
          extra_settings: {},
          style: {}
        };

        $scope.jsonEditorObject = {
          data: {},
          options: {}
        };

        //$scope.visualizations = [{
        //  name: 'bar',
        //  src: '/static/dist/images/tpl-barchart.png',
        //  descr: 'A bar graph is a chart that uses vertical bars to show comparisons among categories.',
        //  selected: false
        //}, {
        //  name: 'pie',
        //  src: '/static/dist/images/tpl-piechart.png',
        //  descr: 'A pie chart is a circular statistical graphic, which is divided into slices to illustrate numerical proportion.',
        //  selected: false
        //}, {
        //  name: 'row',
        //  src: '/static/dist/images/tpl-rowchart.png',
        //  descr: 'A bar graph is a chart that uses horizontal bars to show comparisons among categories.',
        //  selected: false
        //}, {
        //  name: 'line',
        //  src: '/static/dist/images/tpl-trends.png',
        //  descr: 'A line chart is a type of chart which displays information as a series of data points connected by straight line segments',
        //  selected: false
        //}, {
        //  name: 'flow',
        //  src: '/static/dist/images/tpl-flow.png',
        //  descr: 'A chart that indicates the process at specific Journey\'s type or stage.',
        //  selected: false
        //}, {
        //  name: 'table',
        //  src: '/static/dist/images/tpl-table.png',
        //  descr: 'A general view of listed, sorted data.',
        //  selected: false
        //}];

      };

      $scope.isLastStep = false;
      $scope.hasJSONError = false;

      $scope.selectModel = function(model) {
        $scope.jsonEditorObject = {
          data: {},
        };

        $scope.widget.model = model;
        // Set schema for json-editor
        $scope.jsonEditorObject.options = {
          mode: 'tree',
          schema: model.settings,
        };
        jsonSchemaCache.put('schema.json', model.settings);
        // Set default values for json-editor
        _.each(model.settings.properties, function (item, key) {
          $scope.jsonEditorObject.data[key] = item.default || null;
        });

        $scope.isLastStep = true;
      };

      $scope.create = function() {
        $scope.hasJSONError = false;

        jsonValidator.validateJson($scope.jsonEditorObject.data, 'schema.json')
          .then(function(object) {

            $scope.hasJSONError = false;
            $scope.widget.style = angular.extend($scope.widget.style, _.pick(object, ['sizeX', 'sizeY']));
            $scope.widget.settings = _.omit(object, ['sizeX', 'sizeY']);
            WidgetService.create($scope.widget).then(function(resp) {
              $scope.$emit('WIDGET_ADDED', $scope.dashboard.id);
              SystemAlert.success('Widget has been created.');
              $scope.$close();
            });

          })
          .catch(function(err) {
            $scope.hasJSONError = true;
          });
      };

      $scope.selectVisualization = function(v) { };

      init();
    }]);
}());
(function() {
  'use strict';
  angular.module('dashboard')
    .controller('ShareDashboardCtrl', ["$scope", "$modalInstance", "dashboard", "$http", "AccountsService", function($scope, $modalInstance, dashboard, $http, AccountsService) {

      var init = function() {
        $scope.fetchUsers();
      };

      $scope.filters = {
        searchQuery: ''
      };

      var debouncedFetchUsers = _.debounce(function () {
          $scope.fetchUsers();
      }, 500);

      $scope.$watch('filters.searchQuery', function (n, o) {
          if (!n && !o) {
              return;
          }
          debouncedFetchUsers();
      });

      $scope.chosenUsers = _.clone(dashboard.shared_to);

      $scope.toggled = function (user) {
        if (user.chosen) {
          $scope.chosenUsers.push(user.id);
        } else {
          _.pull($scope.chosenUsers, user.id);
        }
      };

      $scope.fetchUsers = function () {
        var params = {
          offset: $scope.pagination.offset,
          limit: $scope.pagination.limit,
          account: dashboard.accountId
        };

        if ($scope.filters.searchQuery) {
            params.searchQuery = $scope.filters.searchQuery;
        }

        $http.get('/configure/account/userslist', {params: params})
          .success(function (result) {
            $scope.pagination.totalItems = result.total_items;
            $scope.pagination.pages = result.pages;

            _.remove(result.users, {self: true});
            $scope.users = _.map(result.users, function (user) {
              var chosen = $scope.chosenUsers.indexOf(user.id) > -1;
              return _.extend(user, {chosen: chosen});
            });

          });
      };

      $scope.pagination = {
          offset: 0,
          limit: 10,
          currentPage: 1,
          totalItems: 0,
          pages: 0,
          maxSize: 10,
          setPage: setPage
      };

      function setPage() {
          $scope.pagination.offset = parseInt($scope.pagination.limit) * ($scope.pagination.currentPage - 1);
          $scope.fetchUsers();
      }

      $scope.share = function() {
        $http.put('/dashboards/' + dashboard.id,
          {shared_to: $scope.chosenUsers}
        ).success(function (res) {
          $modalInstance.close();
          dashboard.shared_to = $scope.chosenUsers;
        });
      };

      init();
    }]);
}());

(function () {
    'use strict';

    angular.module('dashboard')

        .factory('SeriesDataModel', ["$http", "WidgetDataModel", "FilterService", "WidgetDataParser", function ($http, WidgetDataModel, FilterService, WidgetDataParser) {
            function SeriesDataModel() { }

            SeriesDataModel.prototype = Object.create(WidgetDataModel.prototype);

            SeriesDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);

                //var params = this.dataModelOptions ? this.dataModelOptions.params : {};
                var wAttrs = this.widgetScope.widget.attrs;
                var range_alias = wAttrs.extra_settings.range_alias;
                var params    = _.extend({}, wAttrs.settings);
                var date_range  = FilterService.getDateRangeByAlias(range_alias);

                var old_from = wAttrs.settings.from;
                var old_to   = wAttrs.settings.to;

                //amend settings
                params.from = date_range ? date_range.from.toString("MM/dd/yyyy") : old_from;
                params.to   = date_range ? date_range.to.toString("MM/dd/yyyy")   : old_to;

                $http.post(wAttrs.extra_settings.request_url, params).success(function(d) {
                    var chart = {settings  : wAttrs.settings, widget_id : wAttrs.id, extra_settings : wAttrs.extra_settings };
                    // d.data for new journey endoints
                    chart.data = WidgetDataParser.parse(d.list || d.data, wAttrs.extra_settings);
                    WidgetDataModel.prototype.updateScope.call(chartModel, chart);
                    callback();
                }.bind(chartModel))
            };

            return SeriesDataModel;
        }])

        .factory('TopicsDataModel', ["$http", "WidgetDataModel", "WidgetDataParser", "FilterService", "Topics", function ($http, WidgetDataModel, WidgetDataParser, FilterService, Topics) {
            function TopicsDataModel() {
            }

            TopicsDataModel.prototype = Object.create(WidgetDataModel.prototype);

            TopicsDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);
                var wAttrs = this.widgetScope.widget.attrs;
                WidgetDataModel.prototype.updateScope.call(chartModel, {extra_settings: wAttrs.extra_settings});
                callback();
            };

            return TopicsDataModel;
        }])

        .factory('DashboardStorage', ["$http", "$q", "FilterService", "WidgetDataParser", function($http, $q, FilterService, WidgetDataParser) {
            var dashboardList = [];
            var dashboards = {};

            function updateList(inputDashboards) {
                dashboardList = [];
                dashboardList = inputDashboards;
            }

            function getDashboardsList() {
                return dashboardList;
            }

            function updateDashboard(dashboard) {
                var dashToUpdate = _.find(dashboardList, {'id': dashboard.id});
                if (dashToUpdate) {
                    fetchData(dashToUpdate);
                }
            }

            function addDashboard(dashboard) {
                dashboardList.push(dashboard);
            }

            function removeDashboard(dashboardId) {
                _.remove(dashboardList, {'id': dashboardId});
            }

            function fetchData(dashboard) {
                var dId = dashboard.id;
                if (!(dashboards[dId] && dashboards[dId].beingFetched == false)) return;

                var currentDashboard = dashboards[dId];
                var params = getBaseFilter(dId);
                var url = '';

                var onSuccess = {
                    dataFetched : function (response, widgetType, widgets, postParams) {
                        currentDashboard.allData[widgetType] = WidgetDataParser.parseJourneyDashboardData(response.data[widgetType], widgetType);
                        if (widgets.length) {
                            _.each(widgets, function(widget) {
                                if (widget.callback) {
                                    widget.callback.call(null, currentDashboard.allData, widget.id, crossFilter);
                                }
                            });
                        }
                        if (_.has(response.data, 'is_up_to_date') && response.data.is_up_to_date === false) {
                            postParams['force_recompute'] = true;
                            return $http.post(url, postParams).then(
                              function(resp) {
                                  onSuccess.dataFetched(resp.data, widgetType, widgets, postParams)
                              }
                            );
                        }
                    }
                };

                if (dashboard.dashboardType == 'nps') {
                    url = '/nps/json';
                    currentDashboard.beingFetched = true;
                    delete params.range_alias;

                    $http
                        .post(url, params)
                        .success(function (resp) {
                            currentDashboard.beingFetched = false;
                            var departments = ['Customer Care', 'Services', 'Marketing', 'Sales', 'IT', 'Quality Assurance', 'Licenses', 'Operational'],
                                regions = ['APAC', 'EMEA', 'North America'],
                                drivers = ['Product & Quality', 'Value/ROI', 'Implementation', 'Communication', 'Support', 'Services', 'Price', 'Relationship', 'Contract Negotiation'];

                            var getFakeDimensions = function (dm) {
                                return dm[_.random(0, dm.length - 1)]
                            };
                            var fullDateFormat = d3.time.format("%m/%d/%Y");
                            var journeyData = _.map(resp.list, function (item) {
                                return {
                                    'user_name' : item.user_name,
                                    'text' : item.text,
                                    'csat': item.csat,
                                    'nps': item.nps,
                                    'nps_type': item.response_type == 'Default' ? 'Detractor' : item.response_type,
                                    'effort': item.total_effort,
                                    'end': fullDateFormat(new Date(item.created * 1000)),
                                    'department': getFakeDimensions(departments),
                                    'region': getFakeDimensions(regions),
                                    'key_driver': item.key_drivers
                                }
                            });

                            // Keep crossfilter instance global in dashboards
                            currentDashboard.allData = crossfilter(journeyData);

                            _.each(currentDashboard.widgets, function(widget, type) {
                                widget.callback.call(null, currentDashboard.allData);
                            });
                        });

                } else if (dashboard.dashboardType == 'journeys') {
                    var widgetTypes = _.uniq(['journey_volumes_by_journey_type'].concat(_.map(currentDashboard.widgets, 'type')));
                    var crossFilter = getCrossFilter(dashboard.id);

                    url = '/crossfilter/json';
                    currentDashboard.beingFetched = true;

                    if (params['journey_type'] === null) {
                        params['journey_type'] = [];
                    } else {
                        params['journey_type'] = [params['journey_type']]; //Make it array
                    }

                    var promises = _.map(widgetTypes, function(widgetType) {

                        var widgets = _.filter(currentDashboard.widgets, { 'type': widgetType });

                        if (currentDashboard.refreshStates[widgetType]) {
                            var postParams = getFullFilter(dId);
                            postParams['widgets'] = [widgetType];
                            return $http.post(url, postParams)
                                .then(
                                  function(response) {
                                      onSuccess.dataFetched(response.data, widgetType, widgets, postParams);
                                  }, function(error) {
                                      console.log(error);
                                  }
                                );

                        } else {
                            // Do not update 'NPS Trends' widget if it's crossfiltered itself
                            if (widgetType !== 'nps_trends') {
                                _.each(widgets, function(widget) {
                                    if (widget.callback) {
                                        widget.callback.call(null, currentDashboard.allData, widget.id, crossFilter);
                                    }
                                });
                            }
                            return $q.when();
                        }

                    });

                    $q.all(promises).then(function() {
                        currentDashboard.beingFetched = false;
                    });

                }
            };

            function registerWidget(info, cb) {
                var dId = info.dashboardId;
                var wId = info.widgetId;
                if (!_.has(dashboards, dId)) {
                    dashboards[dId] = {
                        allData : {},
                        widgets : [],
                        refreshStates: {},
                        beingFetched: false
                    };
                }

                dashboards[dId].refreshStates[info.widgetType] = true;

                var widget = _.find(dashboards[dId].widgets, { id: wId });
                if (widget) {
                    widget.callback = cb;
                } else {
                    dashboards[dId].widgets.push({
                        id: wId,
                        type: info.widgetType,
                        callback: cb
                    });
                }
            }

            function setCrossFilter(dashboardId, newFilter) {

                if ( !_.has(dashboards[dashboardId], 'crossFilter') ) {
                    dashboards[dashboardId]['crossFilter'] = {
                        journey_type: [ ],
                        journey_tags: [ ],
                        status: [ ],
                        date_subrange: { },
                        nps: [ ],
                    };
                }

                var currentFilter = dashboards[dashboardId].crossFilter;
                var currentItem = currentFilter[newFilter.key];
                var refreshStates = dashboards[dashboardId].refreshStates;

                // Set whether or not to fetch data again for widgets
                _.each(refreshStates, function(bool, widgetType, states) {
                    states[widgetType] = true;
                });
                if (newFilter.key == 'journey_type') {
                    refreshStates['journey_volumes_by_journey_type'] = false;
                    refreshStates['nps_by_journey_type'] = false;
                    refreshStates['status_by_journey_type'] = false;
                }
                // DO NOT REFRESH ITSELF
                refreshStates[newFilter.source] = false;

                if (newFilter.key == 'date_subrange') {
                    angular.copy(newFilter.value, currentItem);
                } else {
                    var pos = currentItem.indexOf(newFilter.value);
                    if (pos > -1) {
                        currentItem.splice(pos, 1);
                    } else {
                        currentItem.push(newFilter.value);
                    }
                }

                var dashboard = _.find(dashboardList, { id: dashboardId });
                fetchData(dashboard);
            }

            function resetCrossFilter(dashboardId, refreshWidgets) {
                if (_.has(dashboards[dashboardId], 'crossFilter')) {
                    dashboards[dashboardId]['crossFilter'] = {
                        journey_type: [],
                        journey_tags: [],
                        status: [],
                        date_subrange: { },
                        nps: [],
                    };
                }
                if (_.has(dashboards[dashboardId], 'refreshStates')) {
                    _.each(dashboards[dashboardId].refreshStates, function(val, key, states) {
                        states[key] = true;
                    });
                }

                var dashboard = _.find(dashboardList, { id: dashboardId });
                if (refreshWidgets && dashboard) {
                    fetchData(dashboard);
                }
            }

            function removeCrossFilter(dashboardId, item) {
                var currentFilter = dashboards[dashboardId].crossFilter;
                var currentItem = currentFilter[item.key];

                if (item.key == 'date_subrange') {
                    angular.copy({ }, currentItem);
                } else {
                    var pos = currentItem.indexOf(item.value);
                    if (pos > -1) {
                        currentItem.splice(pos, 1);
                    }
                }

                var dashboard = _.find(dashboardList, { id: dashboardId });
                fetchData(dashboard);
            }

            function getCrossFilter(dashboardId) {
                if (dashboards[dashboardId]) {
                    return dashboards[dashboardId].crossFilter;
                } else {
                    return null;
                }
            }

            function getBaseFilter(dashboardId) {
                var dashboard = _.find(dashboardList, { id: dashboardId });
                if (dashboard) {
                    var params = {};
                    var filters = dashboard.filters || null;
                    if (filters) {
                        if (filters.facets) {
                            params = angular.copy(filters.facets);
                        }
                        if (filters.period) {
                            var dateRange = FilterService.getDateRangeByAlias(filters.period.alias);
                            params.range_alias = filters.period.alias;
                            params.from = dateFormat(dateRange.from, "yyyy-mm-dd HH:MM:ss", true);
                            params.to = dateFormat(dateRange.to, "yyyy-mm-dd HH:MM:ss", true);
                        }
                    }
                    return params;
                }
                return null;
            }

            function getFullFilter(dashboardId) {
                var baseParams = getBaseFilter(dashboardId);
                var fullParams;
                if (_.has(dashboards[dashboardId], 'crossFilter')) {
                    var crossFilter = dashboards[dashboardId].crossFilter;
                    fullParams = angular.extend({}, baseParams);

                    _.each(crossFilter, function(values, key) {
                        if (key !== 'date_subrange') {
                            if (!_.has(fullParams, key) || !values.length) {
                                return;
                            }
                        } else {
                            if (!_.isEmpty(values)) {
                                fullParams['subrange_from'] = values.from;
                                fullParams['subrange_to'] = values.to;
                            }
                            return;
                        }
                        if (!!fullParams[key].length) {
                            fullParams[key] = _.intersection(fullParams[key], values);
                        } else {
                            fullParams[key] = values;
                        }
                    });
                    return fullParams;
                } else {
                    return baseParams;
                }
            }

            return {
                updateList: updateList,
                update: updateDashboard,
                add: addDashboard,
                remove: removeDashboard,
                registerWidget: registerWidget,
                getStoredData : function(id) { return data[id]},
                getDashboardsList: getDashboardsList,
                setCrossFilter: setCrossFilter,
                getCrossFilter: getCrossFilter,
                resetCrossFilter: resetCrossFilter,
                removeCrossFilter: removeCrossFilter,
                getBaseFilterParams: getBaseFilter,
                getFullFilterParams: getFullFilter
            };
        }])

        .factory('NPSDataModel', ["WidgetDataModel", "FilterService", "DashboardStorage", function (WidgetDataModel, FilterService, DashboardStorage) {
            function NPSDataModel() {}

            NPSDataModel.prototype = Object.create(WidgetDataModel.prototype);

            NPSDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);

                var wAttrs = this.widgetScope.widget.attrs;
                var info = {
                    dashboardId : wAttrs.dashboard_id,
                    widgetId    : wAttrs.id,
                    directive   : ''
                };

                DashboardStorage.registerWidget(info, function(data) {
                    var chart = {
                        settings    : wAttrs.settings,
                        widget_id   : wAttrs.id,
                        data        : data
                    };
                    WidgetDataModel.prototype.updateScope.call(chartModel, chart);
                    callback();
                });
            };

            return NPSDataModel;
        }])

        .factory('JourneyDataModel', ["WidgetDataModel", "FilterService", "DashboardStorage", function (WidgetDataModel, FilterService, DashboardStorage) {
            function JourneyDataModel() {}

            JourneyDataModel.prototype = Object.create(WidgetDataModel.prototype);

            JourneyDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);

                var wAttrs = this.widgetScope.widget.attrs;
                var directive = (wAttrs.settings.directive)? wAttrs.settings.directive.replace(/-/g, '_'): '';
                var info = {
                    dashboardId : wAttrs.dashboard_id,
                    widgetId    : wAttrs.id,
                    widgetType  : directive
               };

                DashboardStorage.registerWidget(info, function(data, widgetId, crossFilter) {

                    if (wAttrs.id !== widgetId) return;

                    var chart = {
                        settings    : wAttrs.settings,
                        widget_id   : wAttrs.id,
                        data        : data[directive],
                        crossFilter : crossFilter
                    };
                    chart.data.now = new Date().getTime();

                    WidgetDataModel.prototype.updateScope.call(chartModel, chart);
                    callback();
                });
            };

            return JourneyDataModel;
        }])

}());
(function () {
    'use strict';

    angular.module('dashboard')

        // Temporarily used factory to parse data so that they can be drawn properly on various types of charts
        // TODO: Backend changes needed to return data in a unified manner
        .factory('WidgetDataParser', function () {
            return {
                parse: parse,
                parseJourneyDashboardData: parseJourneyDashboardData
            };

            // --------------------------------------------------
            // Parse "Trends" data response for Interactions page
            //
            function parseInteractionTrendsData(response) {
                return _.map(response, function (item) {
                    // WORKAROUND to change 'actual' to 'replied'
                    return {
                        key: (item.label === 'actual')? 'replied': item.label,
                        values: item.data
                    };
                });
            }

            // --------------------------------------------------
            // Parse "Distribution" data response for Interactions page
            //
            function parseInteractionDistData(response) {
                return _.map(response, function(item) {
                    // WORKAROUND to change 'actual' to 'replied'
                    return {
                        label: (item.label === 'actual')? 'replied': item.label,
                        value: item.data[0][1]
                    };
                });
            }

            // -----------------------------------------
            // Parse "Trends" data response for journeys
            //
            function parseJourneyTrendsData(response) {
                var plot_d3_data = _.map(response, function (item) {
                    return {
                        key: item.label,
                        values: item.data
                    }
                });

                // Unify the timestamps for all stacks in case of multiple stacks
                // Add 0 values for missing timestamps
                // Number of data points may vary per stacks which results in d3 error
                if (plot_d3_data.length > 1) {
                    var timestamps = [];
                    _.each(plot_d3_data, function (series) {
                        _.each(series.values, function (point) {
                            timestamps.push(point[0]);
                        })
                    });
                    timestamps = _.chain(timestamps)
                        .uniq()
                        .sortBy(function(n) { return n; })
                        .value();

                    _.each(plot_d3_data, function (series) {
                        var newValues = [];
                        _.each(timestamps, function (time) {
                            var newPoint = _.find(series.values, function(point) {
                                return point[0] == time;
                            });
                            if (!newPoint) newPoint = [time, 0];
                            newValues.push(newPoint);
                        });
                        series.values = newValues;
                    });
                }

                return plot_d3_data;
            }

            // ------------------------------------------
            // Parse "Metrics" data response for Advisors
            //
            function parsePredictorTrendsData(response) {
                return _.map(response, function (item) {
                    return {
                        key: item.label,
                        values: item.data
                    };
                });
            }

            // ----------------------------------------------------------
            // Parse "Distribution" data response for Agents and Customers
            //
            function parseDistributionData(response) {
                return _.map(response, function(item) {
                    return {
                        label: item.label,
                        data: [item.value],
                    };
                });
            }

            // ----------------------------------------------------------
            // Parse "Funnel" data response for journeys
            //
            function parseFunnelData(response, funnel_steps) {

                function isEmpty(data) {
                    return !(_.some(data, function(item) {
                        return item['count']['sum'] > 0;
                    }));
                }

                var statuses = ['converted', 'stuck', 'abandoned'];
                var rawData = response.data;
                var chartData = [];

                if (!isEmpty(rawData)) {
                    chartData = _.map(statuses, function (status) {
                        var obj = {
                            key: status,
                            values: []
                        };

                        obj.values = _.map(funnel_steps, function (step, index) {
                            return {x: step, y: rawData[index]['count'][status] || 0};
                        });
                        return obj;
                    });
                }

                return {
                    formatted: chartData,
                    original: rawData
                };
            }



            function parse(response, widgetInfo) {
                switch (widgetInfo.target) {
                    case 'JOURNEY-TREND':
                        return parseJourneyTrendsData(response);
                    case 'OMNI_AGENTS':
                    case 'OMNI_CUSTOMERS':
                        return parseDistributionData(response);
                    case 'PREDICTOR-TREND':
                        // Will be depreciated, 'chart' directive will also handle data parsing for dashboard widgets.
                        // target is 'PREDICTORS' now.
                        return parsePredictorTrendsData(response);
                    case 'INTERACTION-TREND':
                        return parseInteractionTrendsData(response);
                    case 'NORMAL-TREND':
                        return parsePredictorTrendsData(response);
                    case 'INTERACTION-DISTRIBUTION':
                        return parseInteractionDistData(response);
                    case 'NORMAL-DISTRIBUTION':
                        return parseDistributionData(response);
                    case 'JOURNEY-FUNNEL':
                        return parseFunnelData(response, widgetInfo.funnel_steps);
                    default:
                        return response;
                }
            }

            function parseJourneyDashboardData(response, widgetType) {

                var parsedData = {};

                if (widgetType == 'journey_volumes_by_journey_type') {
                    parsedData.labels = response.labels;
                    parsedData.data = _.map(response.data, function(value, key) {
                        return {
                            key: key,
                            value: value
                        }
                    });
                } else if (widgetType == 'status_by_journey_type') {
                    parsedData.labels = response.labels;
                    parsedData.legends = ['abandoned', 'ongoing', 'finished']; // Re-order for now
                    parsedData.data = _.map(response.data, function(obj, key) {
                        return {
                            key: key,
                            values: _.map(parsedData.legends, function(legend) { return obj[legend]; })
                        };
                    });
                    parsedData.data = normalizeStackedData(parsedData);
                } else if (widgetType == 'nps_by_journey_type') {
                    parsedData.labels = response.labels;
                    parsedData.legends = ['n/a', 'detractor', 'passive', 'promoter'];
                    parsedData.data = _.map(response.data, function(obj, key) {
                        return {
                            key: key,
                            values: _.map(parsedData.legends, function(legend) { return obj[legend]; })
                        };
                    });
                    parsedData.data = normalizeStackedData(parsedData);
                } else if (widgetType == 'nps_by_journey_tag') {
                    parsedData.labels = response.labels;
                    parsedData.legends = ['n/a', 'detractor', 'passive', 'promoter'];
                    parsedData.data = _.map(response.data, function(obj, key) {
                        return {
                            key: key,
                            values: _.map(parsedData.legends, function(legend) { return obj[legend]; })
                        };
                    });
                    parsedData.data = normalizeStackedData(parsedData);
                } else if (widgetType == 'nps_trends') {
                    parsedData.data = [{
                        bar: true,
                        values: [],
                    }];
                    parsedData.data[0].values = _.map(response.data, function(val, key) {
                        return [ 1000 * parseInt(key, 10), val];
                    });
                    parsedData.granularity = response.granularity;

                    // This is for yellow line in 'NPS Trends' widget
                    // parsedData.data = [{
                    //     bar: true,
                    //     values: [],
                    // }, {
                    //     key: '',
                    //     values: []
                    // }];
                    // parsedData.data[0].values = _.map(response.data, function(val, key) {
                    //     return [parseInt(key, 10), val];
                    // });
                    // parsedData.data[1].values = parsedData.data[0].values;
                }

                return parsedData;

                function normalizeStackedData(rawData) {
                    var temp = [];
                    var xAxisKeys = _.pluck(rawData.data, 'key');

                    // Normalize data -> convert to percentage
                    _.each(rawData.data, function(item) {
                        var values = item.values;
                        var total = _.reduce(values, function(total, n) { return total + n }, 0);
                        values = _.map(values, function(d) {
                            if (total <= 0) return 0;
                            return d / total * 100;
                        });
                        item.percents = values;
                    });

                    temp = _.map(rawData.legends, function(legend) {
                        var item = { key: legend };
                        var keyIndex = rawData.legends.indexOf(legend);
                        item.values = _.map(xAxisKeys, function(key) {
                            var d = _.find(rawData.data, {key: key});
                            return {
                                x: key,
                                y: (d)
                                    ? d.percents[keyIndex] || 0
                                    : 0,
                                count: (d)
                                    ? d.values[keyIndex] || 0
                                    : 0
                            };
                        });
                        return item;
                    });
                    return temp;
                }
            }

        })

}());
(function () {
    'use strict';
    angular
        .module('dashboard')
        .directive('journeyVolumesByJourneyType', journeyVolumesByJourneyType)
        .directive('npsTrends', npsTrends)
        .directive('npsByJourneyType', npsByJourneyType)
        .directive('npsByJourneyTag', npsByJourneyTag)
        .directive('statusByJourneyType', statusByJourneyType);

    /** Directives for Journey Dashboard Widgets */
    function journeyVolumesByJourneyType(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}"></svg>',
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);
            
            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'value');

                if (_.every(values, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.pieChart()
                        .duration(250)
                        .x(function(d) { return labels[d.key] || 'N/A' })
                        .y(function(d) { return d.value })
                        .color(uxSettings.ordinalColors)
                        .growOnHover(false)
                        .showLegend(true)
                        // .labelsOutside(true)
                        .labelType('value')
                        .noData('No Data Available')
                        .valueFormat(d3.format(',.0d'))

                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .call(chart);

                    return chart;
                }
                function callback(chart) {
                    chart.pie.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'journey_volumes_by_journey_type',
                            key: 'journey_type',
                            value: point.data.key
                        };
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // Apply grey color based on crossfilter selection
                    if (! (scope.crossFilter && scope.crossFilter.journey_type)) { return }

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var filter = scope.crossFilter.journey_type;

                    d3.selectAll(svgId + '.nv-slice')
                        .classed('deselected clickable', function(d) {
                            return ( filter.length && (filter.indexOf(d.data.key) < 0) );
                        })
                        .classed('selected', function(d) {
                            return ( filter.length && (filter.indexOf(d.data.key) >= 0) );
                        });
                }
            }
        }
    }
    journeyVolumesByJourneyType.$inject = ["uxSettings"];

    function npsTrends(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                crossFilter: '=',
            },
            template: [
                '<div class="nps-trends-box">',
                    '<p style="margin-bottom:0">NPS</p>',
                    '<span class="number-display"></span>',
                '</div>',
                '<svg id="w_{{widgetId}}" style="width:calc(100% - 50px)"></svg>'].join(''),
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var avgDOM = angular.element(element).children('div')[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var container = angular.element(element)[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var width = $(container.parentElement).width();
                var height = $(container.parentElement).height();
                var data = scope.chartData.data;
                var granularity = scope.chartData.granularity;
                var values = _.pluck(data, 'values');

                if (_.every(values, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.linePlusBarChart()
                        .duration(0)
                        .x(function(d) { return d[0] })
                        .y(function(d) { return d[1] })
                        .width(width)
                        .height(height)
                        .margin({right: 100})
                        .color(['#1F77B4', '#F8A740'])
                        .showLegend(false)
                        .noData('No Data Available')
                        .focusHeight(60);

                    chart.xAxis.tickFormat(function(d) {
                        return formatLabel(d, granularity);
                    });
                    // Focus View Finder
                    chart.x2Axis.tickFormat((function(d) {
                        return d3.time.format('%x')(new Date(d));
                    }));
                    chart.bars.forceY([0]).padData(false);
                    chart.y1Axis.tickFormat(d3.format('d'));

                    d3.select(avgDOM).selectAll('text').remove();
                    d3.select(svgDOM).selectAll('*').remove();

                    d3.select(svgDOM)
                        .datum(data)
                        .call(chart);

                    return chart;
                }

                function formatLabel(d, level) {
                    if (level == 'week') {
                        return 'Week ' + d3.time.format('%U')(new Date(d));
                    } else {
                        return d3.time.format('%x')(new Date(d));
                    }
                }

                function callback(chart) {
                    var svgId = '#w_' + scope.widgetId + ' ';
                    var drawnBars = d3.selectAll(svgId + '.nv-bar')[0];
                    if (!drawnBars.length) return;

                    var values = data[0].values;

                    // Show view finder with full range by default
                    var len = values.length;
                    var start = values[0][0];
                    var end = values[len - 1][0];
                    chart.brushExtent([start, end]).update();

                    var debouncedBrushUpdate = _.debounce(brushUpdate, 500);
                    function brushUpdate(data) {
                        var newFilter = {
                            source: 'nps_trends',
                            key: 'date_subrange',
                            value: {
                                from: moment.utc(parseInt(data.extent[0])).format('YYYY-MM-DD HH:mm:ss'),
                                to: moment.utc(parseInt(data.extent[1])).format('YYYY-MM-DD HH:mm:ss'),
                                fromDate: moment.utc(parseInt(data.extent[0])).format('MMM DD, YYYY'),
                                toDate: moment.utc(parseInt(data.extent[1])).format('MMM DD, YYYY'),
                            }
                        };

                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    }
                    chart.dispatch.on('brush', debouncedBrushUpdate);

                    // Draw average nps value
                    var total = _.reduce(values, function(total, n) {
                        return total + n[1];
                    }, 0);
                    d3.select(avgDOM)
                        .append('text')
                        .attr('text-anchor', 'middle')
                        .attr('class', 'need-to-refresh')
                        .text(parseInt(total / values.length, 10));
                }
            }
        }
    }
    npsTrends.$inject = ["uxSettings"];

    function npsByJourneyTag(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                widgetId: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}"></svg>',
            link: linkFn
        };
        return directive;
        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var width = $(container.parentElement).width();
                var height = $(container.parentElement).height();
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'value');

                if (_.every(values, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.multiBarChart()
                        .color(uxSettings.fourColors)
                        .duration(0)
                        .yDomain([0, 100])
                        .showControls(false)
                        .width(width)
                        .height(height + 30)
                        .stacked(true)
                        .rotateLabels(-15)
                        .reduceXTicks(true)
                        .noData('No Data Available')
                        .groupSpacing(0.5);

                    chart.showXAxis(false);
                    chart.xAxis
                        .tickFormat(function (d) {
                            return labels[d];
                        });
                    chart.yAxis
                        .tickPadding(10)
                        .tickFormat(function (d) {
                            return d3.format('p')(d / 100);
                        });
                    chart.tooltip.enabled(true);
                    chart.tooltip.valueFormatter(function (d) { return '' +d3.format(',.2f')(d) + '%'; })
                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .transition().duration(0)
                        .call(chart)
                        .each('end', drawFinished);

                    return chart;
                }
                function drawFinished() {
                    drawValueOnStackedBarChart(scope.widgetId, true);
                }
                function callback(chart) {
                    clearTooltip();
                    chart.multibar.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'nps_by_journey_tag',
                            key: 'journey_tags',
                            value: point.data.x
                        }
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // Apply grey color based on crossfilter selection
                    if ( !(scope.crossFilter && scope.crossFilter.journey_tags) ) { return }

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var filter = scope.crossFilter.journey_tags;

                    d3.selectAll(svgId + '.nv-bar')
                        .classed('deselected clickable', function(d) {
                            return ( filter.length && (filter.indexOf(d.x) < 0) );
                        });
                }
            }
        }
    }
    npsByJourneyTag.$inject = ["uxSettings"];

    function npsByJourneyType(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                widgetId: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}" class="stacked-bar-chart clickable-x-axis"></svg>',
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'values');
                var npsValues = _.pluck(_.flatten(values), 'y');

                if (_.every(npsValues, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.multiBarChart()
                        .color(uxSettings.fourColors)
                        .duration(0)
                        .yDomain([0, 100])
                        .y(function(d) { return d.y })
                        .showControls(false)
                        // .showLegend(false)
                        .stacked(true)
                        .noData('No Data Available')
                        .groupSpacing(0.4);

                    chart.xAxis
                        .tickPadding(25)
                        .tickFormat(function (d) {
                            return labels[d];
                        });
                    chart.yAxis
                        .tickPadding(10)
                        .tickFormat(function (d) {
                            return d3.format('p')(d / 100);
                        });
                    chart.tooltip.enabled(false);
                    // chart.tooltip.valueFormatter(function (d) { return '' +d3.format(',.2f')(d) + '%'; })
                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .transition().duration(0)
                        .call(chart)
                        .each('end', drawFinished);

                    return chart;
                }
                function drawFinished() {
                    drawValueOnStackedBarChart(scope.widgetId);

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var xAxisTicks = d3.selectAll(svgId + '.nv-x .tick.zero text')[0];
                    drawRectOnXAxisTicks(xAxisTicks);
                }
                function callback(chart) {
                    chart.multibar.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'nps_by_journey_type',
                            key: 'nps',
                            value: point.data.key
                        };
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // X-Axis click handler
                    var svgId = '#w_' + scope.widgetId + ' ';
                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .on('click', function(jtId) {
                            var newFilter = {
                                source: 'journey_volumes_by_journey_type',
                                key: 'journey_type',
                                value: jtId
                            };
                            scope.$emit('CROSSFILTER_CHANGED', newFilter);
                        });

                    // Apply grey color based on crossfilter selection
                    if (!scope.crossFilter) { return }
                    var filter = scope.crossFilter;

                    d3.selectAll(svgId + '.nv-bar')
                        .classed('deselected', function(d) {
                            return (
                                (filter.journey_type.length && filter.journey_type.indexOf(d.x) < 0) ||
                                (filter.nps.length && filter.nps.indexOf(d.key) < 0)
                            );
                        });
                    d3.selectAll(svgId + '.nv-bar')
                        .classed('clickable', function(d) {
                            return filter.journey_type.length && (filter.journey_type.indexOf(d.x) >= 0);
                        });

                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .classed('selected', function(jtId) {
                            return (filter.journey_type.length && filter.journey_type.indexOf(jtId) >= 0);
                        })
                }
            }
        }
    }
    npsByJourneyType.$inject = ["uxSettings"];

    function statusByJourneyType(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}" class="stacked-bar-chart clickable-x-axis"></svg>',
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render(resolution, data) {
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'values');
                var npsValues = _.pluck(_.flatten(values), 'y');

                if (_.every(npsValues, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.multiBarChart()
                        .color(uxSettings.threeColors)
                        .duration(0)
                        .y(function(d) { return d3.round(d.y, 2) })
                        .yDomain([0, 100])
                        .showControls(false)
                        // .showLegend(false)
                        .noData('No Data Available')
                        .stacked(true)
                        .groupSpacing(0.4);

                    chart.xAxis
                        .tickPadding(25)
                        .tickFormat(function (d) {
                            return labels[d] || 'N/A';
                        });
                    chart.yAxis
                        .tickPadding(10)
                        .tickFormat(function (d) {
                            return d3.format('p')(d / 100);
                        });
                    chart.tooltip.enabled(false);
                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .transition().duration(0)
                        .call(chart)
                        .each('end', drawFinished);

                    return chart;
                }
                function drawFinished() {
                    drawValueOnStackedBarChart(scope.widgetId);

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var xAxisTicks = d3.selectAll(svgId + '.nv-x .tick.zero text')[0];
                    drawRectOnXAxisTicks(xAxisTicks);
                }
                function callback(chart) {
                    chart.multibar.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'status_by_journey_type',
                            key: 'status',
                            value: point.data.key
                        }
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // X-Axis click handler
                    var svgId = '#w_' + scope.widgetId + ' ';
                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .on('click', function(jtId) {
                            var newFilter = {
                                source: 'journey_volumes_by_journey_type',
                                key: 'journey_type',
                                value: jtId
                            };
                            scope.$emit('CROSSFILTER_CHANGED', newFilter);
                        });

                    // Apply grey color based on crossfilter selection
                    if (! (scope.crossFilter)) { return }

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var filter = scope.crossFilter;

                    d3.selectAll(svgId + '.nv-bar')
                        .classed('deselected', function(d) {
                            return (
                                (filter.journey_type.length && filter.journey_type.indexOf(d.x) < 0) ||
                                (filter.status.length && filter.status.indexOf(d.key) < 0)
                            );
                        });
                    d3.selectAll(svgId + '.nv-bar')
                        .classed('clickable', function(d) {
                            return filter.journey_type.length && (filter.journey_type.indexOf(d.x) >= 0);
                        });

                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .classed('selected', function(jtId) {
                            return (filter.journey_type.length && filter.journey_type.indexOf(jtId) >= 0);
                        })    
                }
            }
        }
    }
    statusByJourneyType.$inject = ["uxSettings"];

    function drawValueOnStackedBarChart(widgetId, showCount) {
        var svgId = '#w_' + widgetId + ' ';
        d3.select(svgId + 'g.labels').remove();
        var allBars = d3.selectAll(svgId + '.nv-bar')[0];
        var gValues = d3.select(svgId + '.nv-wrap g').append('g').classed('labels', true);

        _.each(allBars, function(bar) {
            var w = +bar.getAttribute('width');
            var h = +bar.getAttribute('height');
            var x = +bar.getAttribute('x');
            var y = +bar.getAttribute('y');
            var value = (!showCount)
                ? d3.format('.1f')(bar.__data__.y) + '%'
                : d3.format(',')(bar.__data__.count);

            if (h < 20 || value == 0) return;
            gValues.append('text')
                .attr('text-anchor', 'middle')
                .attr('x', x + w/2)
                .attr('y', y + h/2 + 5)
                // .attr('series', bar.__data__.series)
                // .attr('stage', bar.__data__.x)
                .attr('transform', bar.getAttribute('transform'))
                .text(value)
        });
    }

    function drawRectOnXAxisTicks(xAxisTicks) {
        _.each(xAxisTicks, function(tick) {
            var rect = tick.getBBox();
            var tickContainer = tick.parentElement;
            if (!rect || !tickContainer) { return }

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
                .attr('x', x - 15)
                .attr('y', y - (25 - h) / 2)
                .attr('rx', 4)
                .attr('ry', 4)
                .attr('width', w + 30)
                .attr('height', 25);
        });
    }

    function clearTooltip() {
        d3.selectAll('.nvtooltip').remove();
    }

})();
(function () {
    'use strict';
    angular
        .module('dashboard')
        .factory('uxSettings', uxSettings)
        .directive('trendChart', trendChart)
        .directive('distributionChart', distributionChart)
        .directive('funnelChart', funnelChart)
        .directive('topicsCloud', topicsCloud)
        .directive('stackedBarChart', stackedBarChart)
        .directive('distribBarChart', distribBarChart)
        .directive('horizontalBarChart', horizontalBarChart)
        .directive('pieChart', pieChart)
        .directive('trendBarChart', trendBarChart)
        .directive('tableDataChart', dataTableChart)
        .directive('addWidget', addWidget);

    function uxSettings() {
        return {
            'ordinalColors': getOrdinalColors(),
            'threeColors': getThreeColors(),
            'fourColors': getFourColors(),
        };

        function getGenesysColors() {
            return ["#2E69DB", "#5E99FF", "#9BBCE0", "#5A6B8C", "#0F6A51", "#569180", "#14819C",
                "#7EC0C2", "#AFD6D2", "#584FB3", "#7272E0", "#B9B9F0", "#575746", "#827C75", "#C9C4B7", "#8C6542",
                "#8A4D67", "#C48C88", "#EBC8BE", "#724787", "#B07EC2", "#D1B4D9"];
        }
        function getOrdinalColors() {
            return ['#4AC764', '#F8A740', '#EA4F6B', '#203B73'].concat(getGenesysColors());
        }
        function getThreeColors() {
            return ['#EA4F6B', '#F8A740', '#4AC764'].concat(getGenesysColors());
        }
        function getFourColors() {
            return ['#203B73', '#EA4F6B', '#F8A740', '#4AC764'].concat(getGenesysColors());
        }
    }

    function trendChart($rootScope, uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                postParams: '=',
                extraInfo: '='
            },
            template: '<svg ng-show="chartData" style="width:100%; height:100%"></svg>' +
                '<h3  ng-hide="chartData" style="position: absolute;top: 20%;left: 45%">No Data Available</h3>',
            link: function (scope, element) {
                // -------------------
                // Draw "Trends" chart
                //
                function drawStackedChart() {
                    if (!scope.chartData) {
                        return;
                    }
                    nv.addGraph(function () {

                        var chart = nv.models.stackedAreaChart()
                            .useInteractiveGuideline(true)    //Tooltips which show all data points. Very nice!
                            .margin({right: 50})
                            .x(function (d) {
                                return d[0]
                            })   //We can modify the data accessor functions...
                            .y(function (d) {
                                return d[1]
                            })   //...in case your data is formatted differently.
                            .showXAxis(true)
                            .showYAxis(true)
                            .clipEdge(false)
                            .color(uxSettings.ordinalColors);

                        //Format x-axis labels with custom function.

                        if (scope.chartData.length === 1) { // does not make sense when there's 1 legend
                            chart.showLegend(false);
                        }

                        chart.xAxis
                            .showMaxMin(false)
                            .tickFormat(function(d) {
                                if(scope.postParams.level !== 'hour') {
                                    return d3.time.format('%d %b')(new Date(d));
                                } else {
                                    return d3.time.format('%I%p')(new Date(d)).toLowerCase().replace(/^0+/, '');
                                }
                            });
                        chart.xScale(d3.time.scale.utc());  // Align x-axis ticks exactly with actual data points

                        var yAxisFormat = scope.extraInfo.yAxisFormat || ',.2f';
                        chart.yAxis
                            .axisLabel(scope.extraInfo.yAxisLabel)
                            .tickFormat(d3.format(yAxisFormat));

                        d3.select(svgDOM).selectAll('*').remove();
                        d3.select(container).selectAll('.nvtooltip').remove();

                        d3.select(svgDOM)
                            .datum(scope.chartData)
                            .transition().duration(350)
                            .call(chart);

                        nv.utils.windowResize(chart.update);


                        return chart;
                    });
                }

                var container = angular.element(element)[0];
                var svgDOM = angular.element(element).children('svg')[0];

                var debouncedRender = _.debounce(drawStackedChart, 500);
                $(container.parentElement).resize(debouncedRender);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRender();
                });
            }
        }
    }
    trendChart.$inject = ["$rootScope", "uxSettings"];

    function distributionChart($rootScope, uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                postParams: '=',
                extraInfo: '='
            },
            template: '<svg ng-show="chartData" style="width:100%; height:100%"></svg>' +
            '<h3  ng-hide="chartData" style="position: absolute;top: 20%;left: 45%">No Data Available</h3>',
            link: function (scope, element) {
                // -------------------------
                // Draw "Distribution" chart
                //
                function drawPieChart() {
                    if (!scope.chartData) {
                        return;
                    }

                    var activeFilter = scope.extraInfo.active_filter;
                    var yAxisFormat = scope.extraInfo.yAxisFormat || ',.2f';

                    nv.addGraph(function () {
                        var chart = nv.models.pieChart()
                            .x(function (d) { return d.label.toLowerCase() })
                            .y(function (d) { return d.value })
                            .valueFormat(d3.format(yAxisFormat))
                            .showLabels(true)     //Display pie labels
                            .labelsOutside(true)
                            .labelThreshold(.05)  //Configure the minimum slice size for labels to show up
                            .labelType("percent") //Configure what type of data to show in the label. Can be "key", "value" or "percent"
                            //.donut(true)          //Turn on Donut mode. Makes pie chart look tasty!
                            .donutRatio(0.88)     //Configure how big you want the donut hole size to be.
                            .color(uxSettings.ordinalColors)
                            .legendPosition("right");

                        if (scope.chartData.length > 10) {
                            chart.showLegend(false); // TODO: ENCAPSULATE THEM IN SEPARATE POPOVER
                        }

                        d3.select(svgDOM)
                          .datum(scope.chartData)
                          .transition().duration(350)
                          .call(chart);

                        chart.pie.dispatch.on("elementClick", function (e) {
                            var params = {filterName: activeFilter, filterValue: e.label};
                              if (typeof nv.tooltip.cleanup == 'function') {
                                nv.tooltip.cleanup();
                              }
                              d3.selectAll('.nvtooltip').remove(); // workaround for now to cleanup tooltips
                            //$state.go('journeys.details.distribution', params)
                            $rootScope.$emit('journeys.details.distribution', params);
                        });

                        // Disable grow on hover of a slice
                        // @ https://github.com/novus/nvd3/issues/884
                        chart.growOnHover(false);

                        nv.utils.windowResize(chart.update);

                        return chart;
                    });
                }

                var container = angular.element(element)[0];
                var svgDOM = angular.element(element).children('svg')[0];

                var debouncedRender = _.debounce(drawPieChart, 500);
                $(container.parentElement).resize(debouncedRender);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRender();
                });
            }
        }
    }
    distributionChart.$inject = ["$rootScope", "uxSettings"];

    function funnelChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                postParams: '=',
                extraInfo: '='
            },
            template: '<svg id="funnel_{{widgetId}}" ng-show="chartData" style="width:100%; height:100%" class="stacked-bar-chart clickable-x-axis"></svg>' +
            '<h3  ng-hide="chartData" style="position: absolute;top: 20%;left: 45%">No Data Available</h3>',
            link: function (scope, element) {
                // -------------------
                // Draw "Funnel" chart
                //
                function drawFunnelChart() {
                    if (!scope.formattedData) {
                        return;
                    }
                    var domID = '#funnel_' + scope.widgetId + ' ';

                    var getJourneyStageName = function(stageId) {
                        if (scope.extraInfo && scope.extraInfo.journey_stages) {
                            return _.result(_.find(scope.extraInfo.journey_stages, {'id': stageId}), 'display_name');
                        }
                        return 'N/A';
                    };
                    var isLastStep = function(stepId) {
                        var temp = angular.copy(scope.extraInfo.funnel_steps);
                        return stepId == temp.pop();
                    };
                    var getTransitionPercent = function(stepId) {
                        var sum = 0;
                        var converted = 0;
                        var percent = 0;

                        _.each(scope.formattedData, function(seriesData) {
                            var value = _.result(_.find(seriesData.values, {'x': stepId}),'y');
                            if (seriesData.key == 'converted') converted = value;
                            sum += value;
                        });

                        if (converted > 0 && sum > 0) {
                            percent = converted / sum;
                        }
                        return percent;
                    };

                    var chartDrawFinished = function() {
                        // Show count of journeys on each bar snippet
                        d3.select(domID + 'g.labels').remove();
                        var allBars = d3.selectAll(domID + '.nv-bar')[0];
                        var gValues = d3.select(domID + '.nv-wrap g').append('g').classed('labels', true);

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
                        d3.select(domID + 'g.arrows').remove();
                        var transBars = d3.selectAll(domID + '.nv-series-0 .nv-bar')[0];
                        var gArrows = d3.select(domID + '.nv-wrap g').append('g').classed('arrows', true);

                        _.each(transBars, function(bar) {
                            var barWidth = +bar.getAttribute('width');
                            var barHeight = +bar.getAttribute('height');
                            var x = barWidth * 2 - barWidth / 6;
                            var y = +bar.getAttribute('y') + barHeight / 2;
                            var w = barWidth * 2 / 3;
                            var h = 30;

                            var stepId = bar.__data__.x;
                            if (isLastStep(stepId)) return;
                            var percent = getTransitionPercent(stepId);

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
                        d3.select(domID + 'g.labels-total').remove();
                        var totalBars = d3.selectAll(domID + '.nv-series-2 .nv-bar')[0];
                        var gTotalValues = d3.select(domID + '.nv-wrap g').append('g').classed('labels-total', true);

                        _.each(totalBars, function(bar) {
                            var w = +bar.getAttribute('width');
                            var x = +bar.getAttribute('x');
                            var y = +bar.getAttribute('y');
                            if (!isLastStep(bar.__data__.x)) return;

                            gTotalValues.append('text')
                                .attr('text-anchor', 'middle')
                                .attr('fill', 'black')
                                .attr('x', x + w/2)
                                .attr('y', y - 10)
                                .attr('transform', bar.getAttribute('transform'))
                                .text('END')
                        });

                        // Remove bars with zero value which are drawn as simple line
                        d3.selectAll(domID + '.nv-bar')
                            .attr('style', function(d) {
                                if (d.y == 0) return 'display:none';
                            });


                        // Draw buttons for x-axis ticks (steps)
                        var xAxisTicks = d3.selectAll(domID + '.nv-x .tick.zero text')[0];

                        _.each(xAxisTicks, function(tick) {
                            var rect = tick.getBBox();
                            var tickContainer = tick.parentElement;
                            if (!rect || !tickContainer) { return }
                                
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

                    nv.addGraph({
                        generate: function () {
                            var chart = nv.models.multiBarChart()
                                .showControls(false)
                                .showLegend(true)
                                .stacked(true)
                                .color(uxSettings.ordinalColors)
                                .groupSpacing(0.5);

                            chart.xAxis
                                .tickPadding(25)
                                .tickFormat(function (d) {
                                    return getJourneyStageName(d);
                                });

                            chart.yAxis
                                .tickPadding(10)
                                .tickFormat(d3.format('s'));

                            d3.selectAll(domID + '> *').remove();

                            d3.select(svgDOM)
                                .datum(scope.formattedData)
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
                            }

                            chart.multibar.dispatch.on("elementClick", function(point) {
                                selectStage(point.data.x);
                            });

                            chart.legend.updateState(false);    // Disable legend click interaction

                            d3.selectAll('g.nv-x.nv-axis .tick.zero')
                                .on('click', function(x) {
                                    if (this.classList.contains('selected')) {
                                        selectStage(null);
                                    } else {
                                        selectStage(x);
                                    }
                                });

                            chart.tooltip.contentGenerator(function(point) {
                                var stageName = getJourneyStageName(point.data.x);
                                var status = point.data.key.toLowerCase() || '';
                                var steps = scope.extraInfo.funnel_steps || [];
                                var index = steps.indexOf(point.data.x);
                                var nps = scope.originalData[index]['nps'][status];
                                var count = scope.originalData[index]['count'][status];
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
                                            '<tr>',
                                                '<td class="key">Average Bottom-up Score</td>',
                                                '<td class="value">' + d3.format(',.2f')(nps) + '</td>',
                                            '</tr>',
                                        '</tbody>' +
                                    '</table>'
                                ].join('');
                                return template;
                            });
                        }
                    });
                }

                var container = angular.element(element)[0];
                var svgDOM = angular.element(element).children('svg')[0];

                var debouncedRender = _.debounce(drawFunnelChart, 500);
                $(container.parentElement).resize(debouncedRender);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    scope.originalData = scope.chartData.original;
                    scope.formattedData = scope.chartData.formatted;
                    debouncedRender();
                });
            }
        }
    }
    funnelChart.$inject = ["uxSettings"];

    function topicsCloud(Topics) {
        function fetch(scope, params) {
            var limit = params.plot_type ? 15 : null;
            return Topics.fetch(params, limit).then(function(d) {
                scope.topics = _.defaults(d, {active : ''});
                scope.count_max = _.max(scope.topics, function(topic) { return topic.term_count} )['term_count'];
                scope.count_min = _.min(scope.topics, function(topic) { return topic.term_count} )['term_count'];
            });
        }

        return {
            restrict: 'E',
            replace: false,
            scope : {
                settings : '='
            },
            template: '<div class="tagcloud maincloud widget-tagcloud"><ul><li ng-repeat="item in topics | orderBy:\'topic\':reverse"  ng-style="getTopicSize(item.term_count)[\'log\']"><span ng-bind="item.topic"></span></li></ul></div>',
            link: function (scope) {
                scope.getTopicSize = function(count) {
                    var fontMin = 12,
                        fontMax = 40;
                    var size = count == scope.count_min ? fontMin
                        : (Math.log(count) / Math.log(scope.count_max)) * (fontMax - fontMin) + fontMin;
                    var styles = {log : { 'font-size' : size + 'px'}};
                    return styles;
                };
                scope.$watch('settings', function(nVal) {
                    if (nVal && nVal.topics_params) {
                        fetch(scope, nVal.topics_params);
                    }
                });
            }
        };
    }
    topicsCloud.$inject = ["Topics"];

    /** New Charts */
    function stackedBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var keyDriversBarChart = dc.barChart(dom);

                    var driversDim = ndx.dimension(function (d) {return d.key_driver});

                    var npsByKeyDrivers = driversDim.group().reduce(
                      function(p, d) {
                          p.nps_total++;
                          p.nps_types[d.nps_type]['count']++;
                          p.nps_types[d.nps_type]['percentage'] = (p.nps_types[d.nps_type]['count']/p.nps_total)*100;
                          return p;
                      },
                      function (p, d) {
                          p.nps_total--;
                          p.nps_types[d.nps_type]['count']--;
                          p.nps_types[d.nps_type]['percentage'] = (p.nps_types[d.nps_type]['count']/p.nps_total)*100;
                          return p;
                      },
                      //init
                      function () {
                          return {
                              nps_total: 0,
                              nps_types: {
                                  Passive   : {count : 0, percentage : 0},
                                  Detractor : {count : 0, percentage : 0},
                                  Promoter  : {count : 0, percentage : 0}
                              }
                          };
                      }
                    );

                    keyDriversBarChart
                      .width(Math.floor(resolution.width))
                      .height(Math.floor(resolution.height))
                      .x(d3.scale.ordinal())
                      .xUnits(dc.units.ordinal)
                      .margins({left: 50, top: 10, right: 10, bottom: 150})
                      .brushOn(false)
                      .clipPadding(10)
                      .gap(5)
                      .yAxisLabel("NPS Distribution")
                      .round(dc.round.floor)
                      .y(d3.scale.linear().domain([0, 100]))
                      .group(npsByKeyDrivers, "Passive")
                      .dimension(driversDim)
                      .stack(npsByKeyDrivers, "Detractor", function(d){
                          var npsObj = d.value.nps_types['Detractor'];
                          return npsObj.count / d.value.nps_total * 100;
                      })
                      .stack(npsByKeyDrivers, "Promoter", function(d){
                          var npsObj = d.value.nps_types['Promoter'];
                          return npsObj.count / d.value.nps_total * 100;
                      })
                      .valueAccessor(function (d) {
                          var npsObj = d.value.nps_types['Passive'];
                          return npsObj.count / d.value.nps_total * 100;
                      })
                      //.legend(dc.legend().x(Math.floor(resolution.width) - 75).y(10))
                      .elasticY(false)
                      .ordinalColors(uxSettings.threeColors)
                      .on('renderlet', function(chart){

                        /*
                         Place the count labels on stacked bars
                         */
                        //Check if labels exist
                        var gLabels = chart.select(".labels");
                        if (gLabels.empty()){
                            gLabels = chart.select(".chart-body").append('g').classed('labels', true);
                        }

                        var gLabelsData = gLabels.selectAll("text").data(chart.selectAll(".bar")[0]);

                        gLabelsData.exit().remove(); //Remove unused elements

                        gLabelsData.enter().append("text") //Add new elements

                        gLabelsData
                          .attr('text-anchor', 'middle')
                          .attr('fill', 'white')
                          .text(function(d){
                              var labelObj = d3.select(d).data()[0].data.value;
                              var layerKey = d3.select(d).data()[0].layer;
                              return labelObj.nps_types[layerKey].count;
                          })
                          .attr('x', function(d){
                              return +d.getAttribute('x') + (d.getAttribute('width')/2);
                          })
                          .attr('y', function(d){ return +d.getAttribute('y') + 15; })
                          .attr('style', function(d){
                              if (+d.getAttribute('height') < 18) return "display:none";
                          });


                          chart.selectAll("rect.bar").attr("fill", function (d) {


                              if (d.layer == "Passive") {
                                  return '#F8A740';
                              } else if (d.layer == "Detractor") {
                                  return '#EA4F6B';
                              } else {
                                  //Promoter
                                  return '#4AC764';
                              }
                          });

                        /*
                         rotate the x-ticks labels and style them accordingly
                         */
                        chart.selectAll("g.x text")
                          .style("text-anchor", "end")
                          .attr("dx", "-.8em")
                          .attr("dy", ".15em")
                          .attr("font-size", "12px")
                          .attr("transform", "rotate(-30)");
                    });

                    keyDriversBarChart.yAxis().tickFormat(function(v) { return v + "%"; });

                    keyDriversBarChart.render();
                }
            }
        }
    }
    stackedBarChart.$inject = ["uxSettings"];

    function distribBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var npsDistributionBarChart = dc.barChart(dom);

                    var npsDim = ndx.dimension(function (d) {
                        return d.nps
                    });
                    var npsByCount = npsDim.group();

                    npsDistributionBarChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .margins({left: 50, top: 10, right: 10, bottom: 60})
                        //.x(d3.scale.linear().domain([0,10]))
                        .x(d3.scale.ordinal())
                        .xUnits(dc.units.ordinal)
                        //.centerBar(true)
                        .gap(10)
                        .yAxisLabel("NPS Score")
                        .group(npsByCount)
                        .dimension(npsDim)
                        .elasticY(true)
                        .on('renderlet', function (chart) {
                            chart.selectAll("rect.bar").attr("fill", function (d) {
                                var nps_score = parseInt(d.data.key);
                                if (nps_score >= 9) {
                                    return '#4AC764';
                                } else if (nps_score >= 7 && nps_score < 9) {
                                    return '#F8A740';
                                } else if (nps_score < 7) {
                                    return '#EA4F6B';
                                } else {
                                    return '#203B73';
                                }
                            });
                        });

                    npsDistributionBarChart.render();
                }
            }
        }

    }
    distribBarChart.$inject = ["uxSettings"];

    function horizontalBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var regionsRowChart = dc.rowChart(dom);

                    var regionsDim = ndx.dimension(function (d) {return d.region});
                    var npsByRegions = regionsDim.group().reduce(
                        function(p, d) {
                            p.nps_total++;
                            return p;
                        },
                        function (p, d) {
                            p.nps_total--;
                            return p;
                        },
                        //init
                        function () {
                            return {
                                nps_total: 0
                            };
                        }
                    );

                    regionsRowChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .margins({top: 20, left: 10, right: 10, bottom: 20})
                        .group(npsByRegions)
                        .dimension(regionsDim)
                        .valueAccessor(function (d) {
                            return d.value.nps_total
                        })
                        .ordinalColors(uxSettings.genesysColors)
                        .elasticX(true);

                    regionsRowChart.render();
                }
            }
        }
    }
    horizontalBarChart.$inject = ["uxSettings"];

    function pieChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var npsPieChart = dc.pieChart(dom);

                    var npsTypeDim = ndx.dimension(function (d) {return d.nps_type});
                    var npsByType = npsTypeDim.group();

                    npsPieChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .dimension(npsTypeDim)
                        .group(npsByType)
                        .label(function(d) {
                            return d.key + ' ' + d.value;
                        })
                        .ordinalColors(uxSettings.threeColors)
                        .innerRadius(50);

                    var colorScale = d3.scale.ordinal().domain(["Detractor", "Passive", "Promoter"])
                      .range(["#EA4F6B", "#F8A740", "#4AC764"]);

                    npsPieChart.colors(function(d){
                        return colorScale(d);
                    });

                    npsPieChart.render();
                }
            }
        }
    }
    pieChart.$inject = ["uxSettings"];


    function dataTableChart(uxSettings) {
        return {
            restrict: 'AE',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                console.log("INIT DATA TABLE WIDGET!!!");

                scope.$watch('chartData', function (newData, oldData) {

                    if (!newData) return;
                    render(newData)
                });

                function render(ndx) {
                    var dataTable = dc.dataTable(dom);

                    var allDim    = ndx.dimension(function(d) {return d;});
                    dataTable
                      .dimension(allDim)
                      .group(function (d) { return 'dc.js insists on putting a row here so I remove it using JS'; })
                      .size(1000)
                      .columns([
                          function (d) { return d.user_name },
                          function (d) { return d.text },
                          function (d) { return d.nps_type + "-" +d.nps },
                          function (d) { return d.csat; },
                          function (d) { return d.department; },
                          function (d) { return d.region; },
                          function (d) { return d.key_driver; }
                      ])
                      .sortBy(dc.pluck('nps'))
                      .order(d3.descending)

                      .on('renderlet', function (table) {
                          // each time table is rendered remove nasty extra row dc.js insists on adding
                          table.select('tr.dc-table-group').remove();
                      });

                    dataTable.render();

                }
            }
        }
    }
    dataTableChart.$inject = ["uxSettings"];

    function trendBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template:
                '<div style="float:left;width:60px;height:48px;text-align:center;font-weight:bold;font-size:14px;border:1px solid gray;margin-bottom:10px;">' +
                    '<p style="margin-bottom:0">NPS</p>' +
                    '<span class="number-display"></span>' +
                '</div>' +
                '<svg style="width:100%;height:100%"></svg>',
            link: function (scope, element) {
                var avgDOM = angular.element(element).children('div')[0];
                var chartDOM = angular.element(element).children('svg')[0];
                var container = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(container.parentElement).width()),
                        height: Math.abs($(container.parentElement).height()) - 60
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(container.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var npsAvgText = dc.numberDisplay(avgDOM);
                    var npsByTimeBarChart = dc.barChart(chartDOM);

                    var npsDim = ndx.dimension(function (d) {return d.nps});
                    var timeDim        = ndx.dimension(function (d) {return d.end});
                    var npsTotalByTime = timeDim.group().reduce(
                        function(p, d) { p.tot += d.nps; p.n++; return p; },
                        function(p, d) { p.tot -= d.nps; p.n--; return p; },
                        function() {return {tot: 0, n: 0}; }
                    );
                    var npsAverage = function(d) {
                        return (d.value.n)? Math.round((d.value.tot / d.value.n) * 10): 0;
                    };
                    var npsAverage1 = function(d) {
                        return (d.n)? Math.round((d.tot / d.n) * 10): 0;
                    };

                    var npsTotal = ndx.groupAll().reduce(
                        function(p, d) { p.tot += d.nps; p.n++; return p;},
                        function(p, d) { p.tot -= d.nps; p.n--; return p; },
                        function() {return {tot: 0, n: 0}; }
                    );

                    npsAvgText
                        .formatNumber(d3.format("02d"))
                        .group(npsTotal)
                        .valueAccessor(npsAverage1);
                    npsAvgText.render();

                    npsByTimeBarChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .margins({left: 50, top: 10, right: 10, bottom: 60})
                        .x(d3.scale.ordinal())
                        .xUnits(dc.units.ordinal)
                        .gap(5)
                        .yAxisLabel("NPS Score")
                        .group(npsTotalByTime)
                        .dimension(npsDim)
                        .valueAccessor(npsAverage)
                        .elasticY(true)
                        .on('renderlet', function(chart) {
                            /**
                             * output values on each bar
                             */
                            var drawnBars = chart.selectAll(".bar")[0];
                            var gLabels = chart.select(".labels");
                            if (gLabels.empty()){
                                gLabels = chart.select(".chart-body").append('g').classed('labels', true);
                            }

                            var gLabelsData = gLabels.selectAll("text").data(drawnBars);
                            gLabelsData.exit().remove(); //Remove unused elements
                            gLabelsData.enter().append("text"); //Add new elements

                            gLabelsData
                                .attr('text-anchor', 'middle')
                                .attr('fill', function(d) {
                                    return (+d.getAttribute('width') < 15)? 'black': 'white';
                                })
                                .text(function(d){
                                    return npsAverage(d3.select(d).data()[0].data);
                                })
                                .attr('x', function(d){ return +d.getAttribute('x') + (d.getAttribute('width')/2); })
                                .attr('y', function(d){ return +d.getAttribute('y') + 15; })
                                .attr('style', function(d){
                                    if (+d.getAttribute('height') < 18) return "display:none";
                                });

                            /**
                             * draw regression line between the first and last bar
                             */
                            if (drawnBars.length > 1) {
                                var firstBar = drawnBars[0];
                                var lastBar = drawnBars[drawnBars.length - 1];
                                var lineData = [{
                                    x: +firstBar.getAttribute('x') + (firstBar.getAttribute('width') / 2),
                                    y: +firstBar.getAttribute('y')
                                }, {
                                    x: +lastBar.getAttribute('x') + (lastBar.getAttribute('width') / 2),
                                    y: +lastBar.getAttribute('y')
                                }];
                                var line = d3.svg.line()
                                    .x(function (d) {
                                        return d.x;
                                    })
                                    .y(function (d) {
                                        return d.y;
                                    })
                                    .interpolate('linear');
                                var path = chart.select('g.chart-body').selectAll('path.extra').data([lineData]);
                                path.enter().append('path').attr('class', 'extra').attr('stroke', '#ff9900').attr('stroke-width', "3");
                                path.attr('d', line);
                            }

                            /**
                             * rotate the x-ticks labels and style them accordingly
                             */
                            chart.selectAll("g.x text")
                                .style("text-anchor", "end")
                                .attr("dx", "-.8em")
                                .attr("dy", ".15em")
                                .attr("font-size", "12px")
                                .attr("transform", "rotate(-45)");
                        });


                    npsByTimeBarChart.render();
                }
            }
        }
    }
    trendBarChart.$inject = ["uxSettings"];



    function addWidget() {
        return {
            restrict: 'E',
            template: '<span class="fonticon icon-add add-widget" ng-click="add()"></span>',
            link: function(scope, element, attrs) {
                $(element).parents('.widget-content').prev('.widget-title').find('.widget-title-text').remove();
                scope.add = function() {
                    scope.addNewWidget();
                }
            }
        }
    }
})();
