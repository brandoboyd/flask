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
})();
