(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventTypesListCtrl', EventTypesListCtrl);

  /** @ngInject */
  function EventTypesListCtrl($scope, $q, $interval, EventTypesRest, ChannelTypesRest, MetadataService, SystemAlert) {

    var _ChannelTypesRest = new ChannelTypesRest();
    var _EventTypesRest = new EventTypesRest();
    var pageRefresher;

    $scope.channelTypeNamesById = {};

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      fetchEntityList();
      pageRefresher = $interval(fetchEntityList, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    $scope.$on('$destroy', function() {
      stopRefresh();
    });

    $scope.delete = function() {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(deleteEntity(e.name));
      });

      $q.all(promises)
        .then(function() {
          fetchEntityList();
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
          fetchEntityList();
        });
    }


    var triesCount = 0;
    function hasPendingEntities(entities) {
      triesCount++;
      return _.some(entities, function(e) {
        return (e.sync_status == 'SYNCING' || e.sync_status == 'IMPORTING') && triesCount < 10;
      });
    }

    function fetchEntityList() {
      _EventTypesRest.list()
        .success(function(res) {
          $scope.selectedList = [];
          $scope.entityList = res.data;
          _.each($scope.entityList, function(e) {
            e.status_display = MetadataService.getBeautifiedStatus(e);
            e.has_error = !!e.sync_errors;
            e.channel_type_name = $scope.channelTypeNamesById[e.channel_type_id];
          });
          if (!hasPendingEntities(res.data) ) {
            stopRefresh();
            triesCount = 0;
          } else {
            startRefresh();
          }
        });
    }

    function fetchChannelTypes() {
      var deferred = $q.defer();
      _ChannelTypesRest.list().success(function(res) {
        _.each(res.data, function(e) {
          $scope.channelTypeNamesById[e.id] = e.name;
        })
        // $scope.channel_types = _.map(res.data, function(type) {
        //   return _.pick(type, ['id', 'name', 'sync_status']);
        // });
      }).finally(function() {
        deferred.resolve();
      });
      return deferred.promise;
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
      };

      fetchChannelTypes().then(function() {
        startRefresh();  
      });
    }

    function deleteEntity(name) {
      return _EventTypesRest.delete(name)
        .success(function() {
          fetchEntityList();
          SystemAlert.info('Deleted `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to delete `' + entity.name + '`');
        });
    }

    function applySync(name) {
      return _EventTypesRest.applySchema(name)
        .success(function() {
          fetchEntityList();
          SystemAlert.info('Synced `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to synchronize ' + name);
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