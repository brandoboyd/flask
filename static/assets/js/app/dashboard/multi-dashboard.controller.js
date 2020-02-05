(function () {
  'use strict';

  angular.module('dashboard')
    .controller('JourneysMultiDashboardsCtrl',
    function ($scope, $http, $q, $window,
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
    })

      .controller('DashboardDetailsCtrl', function($http, $q, $scope, $modal, $timeout, DashboardStorage, FilterService) {

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

      });
}());
