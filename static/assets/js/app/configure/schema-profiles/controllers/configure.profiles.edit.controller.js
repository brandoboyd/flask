(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaProfileEditCtrl', SchemaProfileEditCtrl);

  /** @ngInject */
  function SchemaProfileEditCtrl($scope, $modal, $timeout, toaster, MetadataService) {

    var schemaKey = 'schema';
    var isRefreshing = false;

    angular.extend($scope, {
      fieldTypes: MetadataService.getSchemaFieldTypes(),
      availableFields: [],
      hasSchema: false,
      hasErorr: false,
      wrapper: {
        id_field: null,
      },

      onSaveSchema: onSaveSchema,
      onApplySchema : onApplySchema,
      onAcceptSchema: onAcceptSchema,
      onCancelSchema: onCancelSchema,
      onAddField: onAddField,
      onRemoveField: onRemoveField,
      onFieldNameInput: onFieldNameInput,
      onShowErrors: onShowErrors,

      getTextRaw: function(item) { return item },
      searchExpressions: searchExpressions,
    });

    // $scope.$on('ON_UPDATE_PROFILE', onReceiveProfile);

    activateController(); 

    function activateController() {
      $scope.$on('LOAD_PROFILE_SUCESS', loadProfileSuccess);
      $scope.$emit('REQUEST_PROFILE');
    }

    function onSaveSchema() {
      // Validate profile
      var hasMissingExpr = _.some($scope.profile[schemaKey], function (field) {
        return (field.is_expression && !field.expression);
      });

      var hasMissingType = _.some($scope.profile[schemaKey], function (field) {
        return !field.type;
      });

      if (hasMissingExpr || hasMissingType) {
        toaster.pop('error', 'Some fields have missing type or expression.');
        $scope.hasError = true;
        return;
      }

      console.log('Saving profile schema... ', $scope.profile[schemaKey]);
      $scope.hasError = false;

      $scope.ProfileAccess
        .updateSchema(_.pick($scope.profile, 'schema'))
        .then(function(res) {
          toaster.pop('info', 'Updated schema successfully.');
          $timeout(
            refreshNotify,
            500
          )
        })
    }

    function onAddField(evt) {
      evt.preventDefault();
      $scope.profile[schemaKey].push({
        name: '',
        type: '',
        expression: '',
      });

      // Automatically open the label selector which saves a click.
      $timeout(function() {
        var count = $scope.profile.schema.length;
        var elementClass = '.field-' + (count - 1) + ' a';
        angular.element(elementClass).click();
      });
    }

    function onRemoveField(evt, index) {
      evt.preventDefault();
      if ($scope.profile[schemaKey][index].name === $scope.wrapper.id_field) {
        $scope.wrapper.id_field = null;
      }
      $scope.profile[schemaKey].splice(index, 1);

      resetAvailableFields();
    }

    function onFieldNameInput(index) {
      // Pre-populate `type` and `field/expression` fields
      // if a label is selected from the predictor's schema fields
      var fields = $scope.profile[schemaKey];
      if ($scope.availableFields.indexOf(fields[index].name) >= 0) {
        fields[index].type = getFieldTypeByLabel(fields[index].name);
        delete fields[index].is_expression;
      } else {
        fields[index].is_expression = true;
      }

      resetAvailableFields();
    }

    function resetAvailableFields() {
      $scope.availableFields = _.filter($scope.originalFields, function(fieldName) {
        var usedFields = _.pluck($scope.profile[schemaKey], 'name');
        return usedFields.indexOf(fieldName) < 0;
      });
    }
    
    function getFieldTypeByLabel(fieldName) {
      /* istanbul ignore if  */
      if (!$scope.profile) {
        return;
      }
      var field = _.find($scope.profile.discovered_schema, { name: fieldName });
      return field? field.type: null;
    }

    function searchSuggestions(term, suggestionsList, searchResultsList) {
      _.each(suggestionsList, function(item) {
        if (item.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          searchResultsList.push(item);
        }
      });
      return searchResultsList;
    };

    function searchExpressions(term) {
      var list = [];
      $scope._availableFields = searchSuggestions(term, $scope.originalFields, list);
    }

    $scope.$watch('wrapper.id_field', function(item) {
      if($scope.profile) {
        _.each($scope.profile[schemaKey], function(field) {
          if (field.name === $scope.wrapper.id_field) {
            field.is_id = true;
          } else {
            delete field.is_id;
          }
        });
      }
    });

    function loadProfileSuccess(evt) {
      if (!$scope.profile) {
        return;
      }

      $scope.isFetching = false;
      $scope.originalFields = _.pluck($scope.profile.discovered_schema, 'name');
      resetAvailableFields();

      $scope.wrapper.id_field = null;
      _.each($scope.profile[schemaKey], function(field) {
        if (!!field.expression) {
          field.is_expression = true;
        }
        if (field.is_id) {
          $scope.wrapper.id_field = field.name;
        }
      });

      $scope.rowsLost = 0;
      if ($scope.profile.items_synced !== null) {
        $scope.rowsLost = $scope.profile.rows - $scope.profile.items_synced;
      }

      /*
      if (!isRefreshing) {
        return;
      }
      */
      // Stop refresh when it finishes applying schema
      // Stop refresh when it finishes appending data

      /*
      if ($scope.profile.sync_status === 'SYNCED' || 
         ($scope.profile.sync_status === 'IN_SYNC') ||
         ($scope.profile.sync_status === 'OUT_OF_SYNC')
      ) {
      */
      if (_.indexOf(['SYNCING','IMPORTING'], $scope.profile.sync_status) == -1)
      {
        console.log("STOP REFRESH", $scope.profile.sync_status);
        isRefreshing = false;
        $scope.$emit('STOP_REFRESH');
      } else {
        console.log("KEEP SYNCING", $scope.profile.sync_status);
      }

      $scope.hasSchema = ($scope.profile.schema && $scope.profile.schema.length > 0);
    }

    function onApplySchema() {
      $scope.ProfileAccess.applySchema();
      $scope.profile.sync_status = 'SYNCING';
      toaster.pop('info', 'Synchronization started.');
      isRefreshing = true;
      console.log("wait before refreshing...");
      $timeout(
        refreshNotify,
        500
      );
    }

    function refreshNotify() {
      //console.log("NOTIFY REFRESH");
      $scope.$emit('START_REFRESH')
    }

    function onAcceptSchema() {
      $scope.ProfileAccess.acceptSchema()
        .then(function() {
          toaster.pop('info', 'Accepted schema successfully.');
          $scope.$emit('LOAD_PROFILE');
        });
    }

    function onCancelSchema() {
      $scope.ProfileAccess.cancelSchema()
        .then(function() {
          toaster.pop('info', 'Cancelled schema successfully.');
          $scope.$emit('LOAD_PROFILE');
        });
    }

    function onShowErrors() {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: $scope.profile.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = $scope.entityType + " profile schema";

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: false,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
      });
    }
  }
})();
