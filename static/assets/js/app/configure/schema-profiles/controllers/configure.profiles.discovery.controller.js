(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaProfileDiscoveryCtrl', SchemaProfileDiscoveryCtrl);

  /** @ngInject */
  function SchemaProfileDiscoveryCtrl($scope, $modal, $timeout, toaster, SchemaProfilesRest) {
    var self = this;
    var _SchemaProfilesRest = new SchemaProfilesRest();
    _SchemaProfilesRest.setType($scope.entityType);

    self.isRefreshing = false;

    angular.extend($scope, {
      isFetching: false,

      flags: { search: '', selectedAll: false },
      table: {
        sort: { predicate: 'is_id', reverse: false }
      },
      dataTypes: ['boolean', 'integer', 'label', 'list', 'string', 'timestamp'],
      selectedRows: [],

      showDetails       : onShowDetails,
      showData          : onShowData,
      showUploadDialog  : showUploadDialog,
      onAppendData      : onAppendData,
      onSelectRow       : onSelectRow
    });

    activateController();

    function activateController() {
      $scope.$on('LOAD_PROFILE_SUCESS', loadProfileSuccess);
      $scope.$emit('REQUEST_PROFILE');
    }

    function showUploadDialog(isAppending) {
      var modalInstance = $modal.open({
        templateUrl: 'partials/schema-profiles/upload_form',
        controller: 'CreateProfileCtrl',
        size: 'md',
        resolve: {
          _ProfileAccess: function() { return $scope.ProfileAccess },
          isAppending: function() { return isAppending },
        }
      });

      modalInstance.result.finally(function() {
        $timeout(function() {
          self.isRefreshing = true;
          $scope.$emit('START_REFRESH');
        });
      });
    }

    function loadProfileSuccess(evt) {
      if (!$scope.profile) {
        return;
      }

      $scope.isFetching = false;
      $scope.selectedRows = [];

      _.each($scope.profile.discovered_schema, function(each, index) {
        var cardinality = $scope.profile.cardinalities[each.name];
        each.cardinality = cardinality? cardinality.count: 0;
        $scope.profile.discovered_schema[index] = _.extend(each, { selected: false });
      });

      var status = $scope.profile.status;
      var sync_status = $scope.profile.sync_status;

      if (!self.isRefreshing) {
        return;
      }
      // Stop refresh when it finishes first-loading or appending data
      if (status === 'LOADED' && (sync_status === 'OUT_OF_SYNC' || sync_status === 'IN_SYNC') ) {
        self.isRefreshing = false;
        console.log("STOP REFRESH!!!");
        $scope.$emit('STOP_REFRESH');
      }
    }

    function onShowDetails(field, values) {
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

    function onShowData(field) {
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
        _SchemaProfilesRest.fetchFieldData(field, params)
          .then(function (res) {
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

    function onAppendData() {
      var params = {
        'csv_file': $scope.form.selectedFile,
        'type': 'update',
      };
      $scope.ProfileAccess.save(params)
        .then(function(res) {
          toaster.pop('info', 'Appended data successfully.');
          self.isRefreshing = true;
          $scope.$emit('START_REFRESH');
        });
    }

    function onSelectRow(selected) {
      if (!selected) {
        // for all selection
        _.each($scope.profile.discovered_schema, function(each, index) {
          $scope.profile.discovered_schema[index].selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selectedRows = [];
        } else {
          $scope.selectedRows = _.clone($scope.profile.discovered_schema);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;
      } else {
        _.each($scope.profile.discovered_schema, function(each, index) {
          if (selected.name === each.name) {
            var found = _.findWhere($scope.selectedRows, {name: selected.name});
            if (found) {
              _.remove($scope.selectedRows, selected);
            } else {
              $scope.selectedRows.push(selected)
            }
            $scope.profile.discovered_schema[index].selected = !selected.selected;
          }
        });
        $scope.flags.selectedAll = ($scope.selectedRows.length === $scope.profile.discovered_schema.length);
      }
    }

  }
})();
