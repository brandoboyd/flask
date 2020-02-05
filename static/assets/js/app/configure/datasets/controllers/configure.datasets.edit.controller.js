(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EditDatasetsCtrl', EditDatasetsCtrl);

  /** @ngInject */
  function EditDatasetsCtrl($scope, $routeParams, $modal, $interval, DatasetsRest, MetadataService, toaster) {
    var _DatasetsRest = new DatasetsRest();
    var datasetName = encodeURIComponent($routeParams.name);
    var createdAtFieldType = 'timestamp';
    var pageRefresher;

    $scope.types = MetadataService.getSchemaFieldTypes();
    $scope.isFetched = false;

    $scope.showData = function (field) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        title: "All values in '" + field + "' column",
        field: field
      };

      var pagination = {
        offset: 0,
        limit: 20,
        currentPage: 1,
        totalItems: 0,
        pages: 0,
        maxSize: 10,
        setPage: function () {
          pagination.offset = parseInt(pagination.limit) * (pagination.currentPage - 1);
          fetchData();
        }
      };

      dialogScope.pagination = pagination;

      var fetchData = function () {
        var params = {skip: pagination.offset, limit: pagination.limit};
        _DatasetsRest.fetchFieldData(datasetName, field, params)
          .success(function (res) {
            dialogScope.data.values = res.data.list;
            pagination.totalItems = res.data.total_items;
            pagination.pages = Math.ceil(pagination.totalItems/pagination.limit);
          });
      };

      fetchData();

      var modalInstance = $modal.open({
        scope: dialogScope,
        size: 'lg',
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.column-values.html'
      });
    };

    $scope.showDetails = function (field, values) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        title: "Unique values in '" + field + "' column",
        field: field,
        values: values
      };

      var modalInstance = $modal.open({
        scope: dialogScope,
        size: 'lg',
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.column-values.html'
      });
    };

    $scope.onShowErrors = function() {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: $scope.dataset.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = $scope.dataset.name;

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
      });
    }

    $scope.select = function (selected) {
      if (!selected) {
        // for all selection
        _.each($scope.dataset.schema, function(each, index) {
          $scope.dataset.schema[index].selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selected = [];
        } else {
          $scope.selected = _.clone($scope.dataset.schema);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;
      } else {
        _.each($scope.dataset.schema, function(each, index) {
          if (selected.name === each.name) {
            var found = _.findWhere($scope.selected, {name: selected.name});
            if (found) {
              _.remove($scope.selected, selected);
            } else {
              $scope.selected.push(selected)
            }
            $scope.dataset.schema[index].selected = !selected.selected;
          }
        });
        $scope.flags.selectedAll = ($scope.selected.length === $scope.dataset.schema.length);
      }
    };

    $scope.changeDescription = function(field, $event) {
      $event.currentTarget.lastElementChild.blur();
    };

    $scope.onEditStart = function() {
      $scope.isSchemaChanged = true;
    };

    $scope.setAsCreatedTime = function() {
        if ($scope.selected.length !== 1) { return }

        var selected = $scope.selected[0];

        if (selected.type !== createdAtFieldType) {
          toaster.pop('warning', 'You need to select a field of timestamp type.');
          return;
        }

        _.each($scope.dataset.schema, function(field, index) {
          if (field.name === selected.name) {
            field.created_time = true;
          } else {
            delete field.created_time;
          }
        });
        $scope.isSchemaChanged = true;
    };

    $scope.saveSchema = function() {
      _.each($scope.dataset.schema, function(field) {
        delete field.selected;
      });
      _DatasetsRest.updateSchema(datasetName, _.pick($scope.dataset, 'schema'))
        .success(function(res) {
          toaster.pop('info', 'Updated schema successfully.');
          reloadDataset();
        });
    };

    $scope.applySchema = function() {
      _DatasetsRest.applySchema(datasetName)
        .success(function(res) {
          toaster.pop('info', 'Synchronization started.');
          startRefresh();
        });
    };

    $scope.acceptSchema = function() {
      _DatasetsRest.acceptSchema(datasetName)
        .success(function(res) {
          toaster.pop('info', 'Accepted schema successfully.');
          reloadDataset();
        });
    };

    $scope.cancelSchema = function() {
      _DatasetsRest.cancelSchema(datasetName)
        .success(function(res) {
          toaster.pop('info', 'Cancelled schema successfully.');
          reloadDataset();
        });
    };

    $scope.appendData = function(files) {
      var modalInstance = $modal.open({
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.create.html',
        controller: 'CreateDatasetCtrl',
        size: 'md',
        resolve: {
          _saveFunc: function() { return _DatasetsRest.save.bind(_DatasetsRest) },
          isAppending: function() { return true },
          datasetName: function() { return $routeParams.name },
        }
      });

      modalInstance.result.then(function() {
        startRefresh();
      });
    };

    activateController();

    function activateController() {
      $scope.selected = [];
      $scope.flags = {
        search: '',
        selectedAll: false
      };
      $scope.table = {
        sort: {
          predicate: 'type',
          reverse: true
        }
      };
      $scope.hasTimetampField = false;

      reloadDataset();
    }

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      reloadDataset();
      pageRefresher = $interval(reloadDataset, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    function reloadDataset() {
      _DatasetsRest.getOne(datasetName)
        .success(onLoadDataset);
    }

    function onLoadDataset(res) {
      $scope.isFetched = true;
      $scope.dataset = res.data;
      $scope.dataset.status_display = MetadataService.getBeautifiedStatus(res.data);
      if ($scope.dataset.cardinalities) {
        $scope.dataset.schema.forEach(function (field) {
          field.cardinality = $scope.dataset.cardinalities[field.name].count || 0;
        });
      }
      $scope.selected = [];
      $scope.isSchemaChanged = false;
      _.each($scope.dataset.schema, function(each, index) {
        $scope.dataset.schema[index] = _.extend(each, { selected: false });
      });

      $scope.hasTimetampField = _.some($scope.dataset.schema, { created_time: true });

      // Stop refresh when it finishes applying schema
      if ( $scope.dataset.sync_status === 'SYNCED' ) {
        $scope.rowsLost = $scope.dataset.rows - $scope.dataset.items_synced;
        stopRefresh();
      }
      // Stop refresh when it finishes appending data
      if ($scope.dataset.sync_status === 'IN_SYNC' && $scope.dataset.status === 'LOADED') {
        stopRefresh();
      }
    }
  }
})();
