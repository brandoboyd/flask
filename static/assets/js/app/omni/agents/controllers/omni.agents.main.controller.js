(function () {
  'use strict';

  angular.module('omni.agents')
    .controller('OmniAgentsCtrl', function($scope,
                                           $rootScope,
                                           $q,
                                           FilterService,
                                           DynamicFacetsService,
                                           WidgetService,
                                           AccountsService,
                                           SystemAlert) {


      $scope.has_schema = false;
      $scope.selection = {
        plot_by: null,
      };
      $scope.widget = {};

      (function activateController() {
        $q.when()
          .then(function() {
            return loadDynamicFacets();
          })
          .then(function() {
            return setupWidget();
          })
      })();

      function loadDynamicFacets() {
        var deferred = $q.defer();
        DynamicFacetsService.getFacetsBySection('agent').then(function(res) {
          $scope.has_schema = true;
          $scope.dynamic = res;
          $scope.plot_by_options = $scope.dynamic.group_by;
          $scope.selection.plot_by = $scope.plot_by_options[0];
        }).catch(function(err) {
          SystemAlert.error(err.data.error);
        }).finally(function() {
          deferred.resolve();
        });
        return deferred.promise;
      }

      function setupWidget() {
        $scope.widget = {
          removing: false,
          updating: false,
          item: null,
          getParams: function () {
            return {
              settings: angular.extend($scope.getSearchParams(), {
                metric      : 'count',
                group_by    : $scope.getActiveFilter($scope.plot_by_options)
              }),
              extra_settings: {
                request_url : '/facet-search/agent/distribution',
                source      : '/omni/agents#/distribution?wid=',
                directive   : 'chart',
                target      : 'OMNI_AGENTS',
                chart_type  : 'PIE',
                yAxisFormat : ',.0d',
                account_info: AccountsService.getCompactAccount()
              }
            };
          },
          setup: function (w) {
            var wscope = $scope.widget;
            if (wscope.updating) {
              wscope.updating = false;
            }

            if (!w || _.isEmpty(w)) {
              return;
            }

            loadWidgetSettings(w);
          },
        };
        $scope.widget["remove"] = WidgetService.makeRemove($scope.widget, 'removing');

        $scope.$on(WidgetService.CHANGED, function (evt, data) {
          var w = $scope.widget;
          w.updating = true;
          w.item = data.widget;
        });
        $scope.$watch('widget.item', $scope.widget.setup);
        $scope.$watch('location.search()', locationChanged);
      }

      $scope.$on(FilterService.DATE_RANGE_CHANGED, function() {
        $scope.currentDate = FilterService.getSelectedDateRangeName();
      });
      $scope.currentDate = FilterService.getSelectedDateRangeName();

      $scope.getSearchParams = function (item) {
        var params = {};

        var dynFacetsValues = $scope.getDynamicFacetsValues();
        _.extend(params, dynFacetsValues);

        if ($rootScope.$state.current.name === 'agents.details.distribution') {
          var filterName = $rootScope.$stateParams.filterName;
          var filterValue = $rootScope.$stateParams.filterValue;

          var active_facet;
          if ($scope.dynamic) {
            active_facet = _.find($scope.dynamic.facets, { id: filterName });
          }

          if (!active_facet) {
            if (filterName && filterName.toLowerCase() !== 'all') {
              // FilterService that exists in facets would already be added by above params assignment.
              // We need to add param for filter that doesn't exist in facets
              // eg: plot_by genders/location in agents/customers distribution tab
              params[filterName] = [filterValue];
            }
          }
        }
        return params;
      };

      $scope.getDynamicFacetsValues = function() {
        var facets = {};
        if($scope.dynamic && $scope.dynamic.facets) {
          _.each($scope.dynamic.facets, function(facet) {
            facets[facet.id] = _.pluck(_.where(facet.list, { enabled:true }), 'display_name');
            //Don't pass attributes if 'All' selected
            if (facets[facet.id].length == 0) delete facets[facet.id]
          });

        }
        return facets
      }

      $scope.setFilter = function(groupings, type) {
        _.each(groupings, function(item) {
          item.type === type ? item.active = true : item.active = false
        });
        updateFacets();
      };


      var findActiveFilter = function(groupings) {
        return _.find(groupings, function(item) {
          return item.active === true
        });
      }

      $scope.getActiveFilter = function(groupings) {
        var active = findActiveFilter(groupings);
        return active ? active.value : null
      };

      $scope.getActiveFilterName = function(groupings) {
        var active = findActiveFilter(groupings);
        return active ? active.type : null
      };

      $scope.updateFacets = function(data) {
        updateFacets();
      };

      function updateFacets() {
        $scope.$broadcast("ON_AGENT_FACETS_UPDATE");
      };

      $scope.$on('$stateChangeSuccess',
        function(event, toState, toParams, fromState, fromParams){
          if (toState.name == 'agents.details.distribution' || toState.name == 'agents.details') {
            $scope.currentTab = 'details';
          } else {
            $scope.currentTab = toState.name;
          }
        }
      );

      function loadWidgetSettings (w) {
        var settings = w.settings;

        // Load facet options
        _.each($scope.dynamic.facets, function (facet) {
          if (_.has(settings, facet.id) && settings[facet.id].length) {
            facet.all = false;
            _.each(settings[facet.id], function (label) {
              var v = _.find(facet.list, { display_name: label });
              if (v) { v.enabled = true }
            });
          }
        });

        // Load saved groupBy option
        $scope.selection.plot_by = _.find($scope.plot_by_options, { value: settings.group_by });
      }


      // Widgets
      function locationChanged () {
        var w = $scope.widget;
        if (w.removing) {
          return;
        }
        WidgetService.loadFromLocation();
      }

      $scope.$watch('selection.plot_by', function(nVal) {
        if(nVal) {
          $scope.setFilter($scope.plot_by_options, nVal.type);
        }
      });

    });
})();