(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ChannelTypesListCtrl', ChannelTypesListCtrl);

  /** @ngInject */

  function ChannelTypesListCtrl($scope, $q, $interval, $modal, ChannelTypesRest, FilterService, MetadataService, SystemAlert) {

    var _ChannelTypesRest = new ChannelTypesRest();
    var pageRefresher;
    var debouncedFetch = _.debounce(fetchChannelTypes, 100);
    
    $scope.$on(FilterService.DATE_RANGE_CHANGED, debouncedFetch);

    $scope.delete = function() {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(deleteEntity(e.name));
      });

      $q.all(promises)
        .then(function() {
          fetchChannelTypes();
        });
    };

    $scope.applySync = function() {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(applySync(e.name));
      });

      $q.all(promises)
        .then(function() {
          fetchChannelTypes();
        });
    }

    //TODO: Why `ark-switch` dispatches action twice?
    $scope.toggleLock = _.debounce(toggleLock, 100);

    $scope.$on('$destroy', function() {
      stopRefresh();
    });

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      fetchChannelTypes();
      pageRefresher = $interval(fetchChannelTypes, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    function hasPendingEntities(entities) {
      return _.some(entities, function(e) {
        return e.status === 'LOADING' || e.sync_status === 'SYNCING';
      });
    }

    function fetchChannelTypes() {
      var dateRange = FilterService.getDateRange({ local: true });

      _ChannelTypesRest.list()
        .success(function(res) {
          $scope.entityList = res.data;
          _.each($scope.entityList, function(e) {
            e.status_display = MetadataService.getBeautifiedStatus(e, 'channel');
            e.has_error = !!e.sync_errors;
          });
          if (!hasPendingEntities(res.data) ) {
            stopRefresh();
          }
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

    function deleteEntity(name) {
      return _ChannelTypesRest.delete(name)
        .success(function() {
          fetchChannelTypes();
          SystemAlert.info('Deleted `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to delete `' + name + '`');
        });
    }

    function applySync(name) {
      return _ChannelTypesRest.applySync(name)
        .success(function() {
          fetchChannelTypes();
          SystemAlert.info('Synced `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to synchronize ' + name);
        });
    }

    function toggleLock(entity) {
      _ChannelTypesRest.update(entity.name, _.pick(entity, ['is_locked']))
        .success(function() {
          if (entity.is_locked) {
            SystemAlert.info('Locked `' + entity.name + '`');
          } else {
            SystemAlert.info('Unlocked `' + entity.name + '`');
          }
        })
        .catch(function() {
          SystemAlert.error('Failed to lock `' + entity.name + '`');
        });
    }

    $scope.onShowErrors = function(entity) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: entity.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = entity.name;

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
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
