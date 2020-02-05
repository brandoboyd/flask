(function () {
  'use strict';

  var dependencies = [
    'omni',
    'ui.router',
  ];
  angular.module('omni.customers', dependencies)
    .run(["$rootScope", "$state", "$stateParams", function ($rootScope, $state, $stateParams) {
      // It's very handy to add references to $state and $stateParams to the $rootScope
      // so that you can access them from any scope within your applications.For example,
      // <li ng-class="{ active: $state.includes('contacts.list') }"> will set the <li>
      // to active whenever 'contacts.list' or one of its decendents is active.
      $rootScope.$state = $state;
      $rootScope.$stateParams = $stateParams;
    }])

    .config(["$stateProvider", "$urlRouterProvider", "$locationProvider", function ($stateProvider, $urlRouterProvider, $locationProvider) {
      $urlRouterProvider.when("", "details");
      $urlRouterProvider.when("/", "details");

      // For any unmatched url, send to /route1
      $urlRouterProvider.otherwise("details");

      $stateProvider
        .state('customers', {
          abstract: true,
          url: '/',
          template: '<ui-view/>'
        })
        .state('customers.details', {
          url: 'details',
          templateUrl: '/omni/partials/customers/details',
          //template: "<p>Details</p>",
          controller: 'CustomersDetailsCtrl'
        })

        .state('customers.details.distribution', {
          url: '/filter/:filterName/:filterValue'
        })

        .state('customers.distribution', {
          url: 'distribution',
          templateUrl: '/omni/partials/customers/distribution',
          controller: 'CustomersDistributionCtrl'
        })
    }]);

})();

(function () {
  'use strict';

  angular.module('omni.customers')
    .controller('CustomersDetailsCtrl', ["$scope", "$http", "SystemAlert", function ($scope, $http, SystemAlert) {

      $scope.customers = {};
      $scope.customers.table_header = [];
      $scope.customers.table_data = [];
      $scope.loading = false;

      $scope.$on("ON_CUSTOMER_FACETS_UPDATE", function () {
        $scope.resetPagination();
        $scope.searchDetails($scope.getSearchParams());
      });

      $scope.resetPagination = function() {
        $scope.offset = 0;
        $scope.limit = 10;
        $scope.customers.table_data = [];
        $scope.hasMore = true;
      };

      $scope.loadMore = function() {
        $scope.searchDetails($scope.getSearchParams());
      };

      $scope.$on('$stateChangeSuccess',
        function (event, toState, toParams, fromState, fromParams) {

          if (!_.isEmpty(toParams)) {
            var active_facet;
            if ($scope.dynamic) {
              active_facet = _.find($scope.dynamic.facets, {id: toParams.filterName});
            }
            if (active_facet) {
              var v = _.find(active_facet.list,
                { display_name: decodeURI(toParams.filterValue) }
              );

              active_facet.all = false;
              if (toParams.filterName == 'type') {
                // $scope.facets.journey_types.selected = v.id;
              } else {
                _.each(active_facet.list, function (f) {
                  f.enabled = false;
                });
                v.enabled = true;
              }
            } else {
              // This $scope.searchDetails never gets called because other searchDetails are getting debounced
              // Further, in a single state (url being the same eg: /details/filter/genders/F), filter specified in
              // the url should not be ignored when changing facets in the same state/url.
              // So filters are added to params in `getSearchParams` definition.

              //var basePoint = moment.unix(toParams.timestamp / 1000);
              //var params = _.extend({}, $scope.getSearchParams());

              //params[toParams.filterName] = [decodeURI(toParams.filterValue)];
              //$scope.searchDetails(params);
            }
          }
        });

      $scope.searchDetails =
        _.debounce(function (params) {
          if (!$scope.hasMore) return;
          $scope.loading = true;

          var page_params = {
            offset : $scope.offset,
            limit  : $scope.limit
          };
          _.extend(params, page_params);

          $http.post("/facet-search/customer/detail", params)
            .success(function (res) {
              $scope.hasMore = res.data.more_data_available || false;

              if(res.data.list.length > 0) {
                $scope.customers.table_header = _.reject(
                  _.keys(res.data.list[0]),
                  function(d) {
                    var rejected_keys = ['id', 'linked_profile_ids', 'full_name', 'account_id', 'customer_assigned_labels', 'groups', 'customer_outstanding_balance','customer_assigned_segments', 'customer_num_transfers'];
                    return _.indexOf(rejected_keys, d) >= 0
                  }
                )
              }
              $scope.customers.table_data = $scope.customers.table_data.concat(res.data.list);
              $scope.offset = $scope.customers.table_data.length;
            })
            .error(function(data){
              SystemAlert.error('Failed to load customer details');
              console.log(data);
            })
            .finally(function() {
              $scope.loading = false;
            });
        }, 300);

      $scope.searchDetails($scope.getSearchParams());
    }]);

})();
(function () {
  'use strict';

  angular.module('omni.customers')
    .controller('CustomersDistributionCtrl', ["$scope", "$rootScope", "$http", "$state", function ($scope, $rootScope, $http, $state) {
      $scope.$on("ON_CUSTOMER_FACETS_UPDATE", function () {
        $scope.buildPlot();
      });

      $scope.$on('customers.details.distribution', function(e, params) {
        $state.go('customers.details.distribution', params, {inherit: false})
      });

      $scope.buildPlot = _.debounce(function () {
        var data = $scope.getSearchParams();
        if ($scope.has_schema) {
          buildDistributionPlot(data);
        }
      }, 300);

      var buildDistributionPlot = function (data) {
        data.group_by = $scope.getActiveFilter($scope.plot_by_options);
        data.metric = 'count';

        $http.post('/facet-search/customer/distribution', data)
          .success(function (res) {
            $scope.extra_settings = {
              active_filter : $scope.getActiveFilterName($scope.plot_by_options),
              valueFormat   : ',.0d',
              target        : 'OMNI_CUSTOMERS',
              chart_type    : 'PIE',
              drilldownEnabled: true
            };
            $scope.chartData = _.map(res.data, function(item) {
              return {
                data: [item.value],
                label: item.label
              }
            });
          });
      };

      $scope.buildPlot();
    }]);

})();
(function () {
  'use strict';

  angular.module('omni.customers')
    .controller('OmniCustomersCtrl', ["$scope", "$rootScope", "$q", "FilterService", "DynamicFacetsService", "WidgetService", "AccountsService", "SystemAlert", function ($scope,
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
        DynamicFacetsService.getFacetsBySection('customer')
          .then(function(res) {
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
                request_url : '/facet-search/customer/distribution',
                source      : '/omni/customers#/distribution?wid=',
                directive   : 'chart',
                target      : 'OMNI_CUSTOMERS',
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

      $scope.$on(FilterService.DATE_RANGE_CHANGED, function () {
        $scope.currentDate = FilterService.getSelectedDateRangeName();
      });
      $scope.currentDate = FilterService.getSelectedDateRangeName();

      $scope.getSearchParams = function (item) {
        var params = {};

        var dynFacetsValues = $scope.getDynamicFacetsValues();

        _.extend(params, dynFacetsValues);

        if ($rootScope.$state.current.name === 'customers.details.distribution') {
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

      $scope.setFilter = function (groupings, type) {
        _.each(groupings, function (item) {
          item.type === type ? item.active = true : item.active = false
        });
        updateFacets();
      };

      var findActiveFilter = function (groupings) {
        return _.find(groupings, function (item) {
          return item.active === true
        });
      }

      $scope.getActiveFilter = function (groupings) {
        var active = findActiveFilter(groupings);
        return active ? active.value : null
      };

      $scope.getActiveFilterName = function (groupings) {
        var active = findActiveFilter(groupings);
        return active ? active.type : null
      };


      $scope.updateFacets = function (data) {
        updateFacets();
      }

      function updateFacets() {
        $scope.$broadcast("ON_CUSTOMER_FACETS_UPDATE");
      };

      $scope.$on('$stateChangeSuccess',
        function (event, toState, toParams, fromState, fromParams) {
          if (toState.name == 'customers.details.distribution' || toState.name == 'customers.details') {
            $scope.currentTab = 'details';
          } else {
            $scope.currentTab = toState.name;
          }
        }
      );

      function loadWidgetSettings(w) {
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

      function locationChanged() {
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
    }]);

})();