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
})();