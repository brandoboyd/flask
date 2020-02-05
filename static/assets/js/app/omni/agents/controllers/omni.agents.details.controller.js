(function () {
  'use strict';

  angular.module('omni.agents')
    .controller('AgentsDetailsCtrl', function($scope, $rootScope, $http, $state) {

      $scope.agents = {};
      $scope.agents.table_header = [];
      $scope.agents.table_data = [];
      $scope.loading = false;

      $scope.$on("ON_AGENT_FACETS_UPDATE", function() {
        $scope.resetPagination();
        $scope.searchDetails($scope.getSearchParams());
      });

      $scope.resetPagination = function() {
        $scope.offset = 0;
        $scope.limit = 10;
        $scope.agents.table_data = [];
        $scope.hasMore = true;
      };

      $scope.loadMore = function() {
        $scope.searchDetails($scope.getSearchParams());
      };

      $scope.$on('$stateChangeSuccess',
        function(event, toState, toParams, fromState, fromParams){

          if(!_.isEmpty(toParams)) {
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

              //var params = _.extend({}, $scope.getSearchParams());
              //params[toParams.filterName] = [decodeURI(toParams.filterValue)];
              //$scope.loading = true;
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

          $http.post("/facet-search/agent/detail", params)
            .success(function(res) {
              $scope.hasMore = res.data.more_data_available || false;

              if(res.data.list.length > 0) {
                $scope.agents.table_header = _.reject(
                  _.keys(res.data.list[0]),
                  function(d) {
                    var rejected_keys = ['linked_profile_ids', 'agent_occupancy', 'agent_status', 'agent_attached_data', 'id', 'native_id', 'agent_industry', 'status', 'agent_phone', 'full_name', 'account_id', 'assigned_labels', 'groups', 'assigned_segments'];
                    return _.indexOf(rejected_keys, d) >= 0
                  }
                )
              }
              $scope.agents.table_data = $scope.agents.table_data.concat(res.data.list);
              $scope.offset = $scope.agents.table_data.length;
            })
            .error(function(data){
              SystemAlert.error('Failed to load agent details');
              console.log(data);
            })
            .finally(function() {
              $scope.loading = false;
            });
        }, 300);

      $scope.searchDetails($scope.getSearchParams());
    });

})();