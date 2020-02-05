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
})();
