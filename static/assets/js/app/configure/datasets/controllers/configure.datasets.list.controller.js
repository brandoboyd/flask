(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('DatasetsListCtrl', DatasetsListCtrl);

  /** @ngInject */

  function DatasetsListCtrl($scope, $modal, $q, $interval, $timeout, DatasetsRest, MetadataService, FilterService, SystemAlert) {
    var _DatasetsRest = new DatasetsRest();
    var pageRefresher;

    $scope.delete = function (dataset) {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(deleteEntity(e.name));
      });

      $q.all(promises).then(function() {
        $timeout(function() {
          activateController();
        });
      });
    };

    $scope.openDatasetModal = function() {
      var modalInstance = $modal.open({
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.create.html',
        controller: 'CreateDatasetCtrl',
        size: 'md',
        resolve: {
          _saveFunc: function() { return _DatasetsRest.save.bind(_DatasetsRest) },
          datasetName: null,
          isAppending: null,
        }
      });

      modalInstance.result.finally(function() {
        startRefresh();
      });
    };

    $scope.$on('$destroy', function() {
      stopRefresh();
    });

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      fetch();
      pageRefresher = $interval(fetch, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    function hasPendingDatasets(datasets) {
      return _.some(datasets, function(dataset) {
        return ['IMPORTING', 'SYNCING'].indexOf(dataset.sync_status) > -1;
      });
    }

    activateController();

    function activateController() {
      $scope.table = {
        sort: {
          predicate: 'created_at',
          reverse: false,
        }
      };
      $scope.selectedList = [];
      $scope.flags = {
        searchTerm: '',
        selectedAll: false,
      }
      startRefresh();
    }

    function fetch() {
      _DatasetsRest.list().success(function(res) {
        $scope.entityList = res.data;
        _.each($scope.entityList, function(dataset) {
          dataset.status_display = MetadataService.getBeautifiedStatus(dataset);
          dataset.encoded_name = encodeURIComponent(dataset.name);
        });

        if ( !hasPendingDatasets(res.data) ) {
          stopRefresh();
        }
      });
    }

    function deleteEntity(name) {
      return _DatasetsRest.delete(name).success(function() {
        startRefresh();
        SystemAlert.info('Deleted `' + name + '`');
      })
      .catch(function() {
        // SystemAlert.error('Failed to delete `' + entity.name + '`');
      });
    }

    $scope.select = function (entity) {
      if (!entity) { // global selection
        _.each($scope.entityList, function(e) {
          e.selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selectedList = [];
        } else {
          $scope.selectedList = _.clone($scope.entityList);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;

      } else {
        _.each($scope.entityList, function(item) {
          if (entity.id === item.id) {
            if (_.findWhere($scope.selectedList, { id: entity.id })) {
              _.remove($scope.selectedList, entity);
            } else {
              $scope.selectedList.push(entity)
            }
            item.selected = !entity.selected;
          }
        });

        $scope.flags.selectedAll = ($scope.selectedList.length === $scope.entityList.length);
      }
    };
  }
})();
