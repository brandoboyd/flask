(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EditEventTypeCtrl', EditEventTypeCtrl);
  
    /** @ngInject */
  function EditEventTypeCtrl($scope, $modal, $q, $timeout, $interval, $location, $routeParams, ChannelTypesRest, EventTypesRest, MetadataService, SystemAlert) {

    var _ChannelTypesRest = new ChannelTypesRest();
    var _EventTypesRest = new EventTypesRest();
    var pageRefresher;

    $scope.entityName = null;
    $scope.entity = null;
    $scope.hasError = false;
    $scope.hasSchema = false;
    $scope.channelTypes = [];
    $scope.availableFields = [];
    $scope.schemaFieldTypes = MetadataService.getSchemaFieldTypes();
    $scope.schemaFieldFlags = MetadataService.getEventTypeFieldFlags();

    $scope.onCreateEntity = onCreateEntity;
    $scope.onSaveSchema = onSaveSchema;
    $scope.onApplySchema = onApplySchema;
    $scope.onAcceptSchema = onAcceptSchema;
    $scope.onCancelSchema = onCancelSchema;
    $scope.showUploadDialog = showUploadDialog;
    $scope.onShowErrors = onShowErrors;
    $scope.onSelectTab = onSelectTab;
    $scope.onAddField = onAddField;
    $scope.onRemoveField = onRemoveField;
    $scope.onFieldNameInput = onFieldNameInput;
    $scope.searchExpressions = searchExpressions;
    $scope.getTextRaw = function(item) { return item; };
    $scope.$on('$destroy', function() { stopRefresh() });


    $scope.flags = { search: '', selectedAll: false },
    $scope.table = {
      sort: { predicate: 'is_id', reverse: false }
    },
    $scope.schemaTabs = [
      { name: 'Discovered Fields',  active: false,  templateUrl: 'partials/event-types/schema-discovery' },
      { name: 'Schema',             active: false,  templateUrl: 'partials/event-types/schema-edit' }
    ],

    activateController();

    function activateController() {
      fetchChannelTypes().then(function() {
        loadEntity();
      });

      onSelectTab($scope.schemaTabs[0]);
    }

    function fetchChannelTypes() {
      var deferred = $q.defer();
      _ChannelTypesRest.list().success(function(res) {
        $scope.channelTypes = _.map(res.data, function(type) {
          return _.pick(type, ['id', 'name', 'sync_status']);
        });
        // $scope.channelTypes = _.filter(res.data, { 'sync_status': 'IN_SYNC' });
      }).finally(function() {
        deferred.resolve();
      });
      return deferred.promise;
    }

    function loadEntity() {
      if ($routeParams.name === 'new') {
        $scope.entity = {
          name: "",
          //channel_type_id: null,
          platform : null
        };
        return $q.when();

      } else { 
        $scope.entityName = $routeParams.name;
        return reloadEntity();
      }
    }

    function afterLoadEntity(res) {
      $scope.entity = res.data;
      $scope.entity.status_display = MetadataService.getBeautifiedStatus(res.data);
      $scope.hasSchema = ($scope.entity.schema && $scope.entity.schema.length > 0);

      $scope.originalFields = _.pluck($scope.entity.discovered_schema, 'name');
      resetAvailableFields();

      $scope.rowsLostAfterSync = 0;
      if ($scope.entity.items_synced !== null) {
        $scope.rowsLostAfterSync = $scope.entity.rows - $scope.entity.items_synced;
      }

      if (isPendingEntity(res.data)) {
        startRefresh();
      } else {
        triesCount = 0;
        stopRefresh();
      }
    }

    function onCreateEntity() {
      _EventTypesRest.create($scope.entity).success(function(res) {
        SystemAlert.info('Created successfully!');
        $location.path('/event_types');
      });
    }

    function showUploadDialog() {
      var modalInstance = $modal.open({
        templateUrl: 'partials/event-types/file-upload-modal',
        controller: 'FileUploadCtrl',
        size: 'md',
        resolve: {
          _entityName: function() { return $scope.entityName },
          _uploadFunc: function() { return _EventTypesRest.discoverSchema.bind(_EventTypesRest) },
        }
      });

      modalInstance.result.finally(function() {
        reloadEntity();
      });
    }

    function onAddField(evt) {
      evt.preventDefault();
      $scope.entity.schema.push({
        name: '',
        type: '',
        expression: '',
      });

      // Automatically open the label selector which saves a click.
      $timeout(function() {
        var count = $scope.entity.schema.length;
        var elementClass = '.field-name-' + (count - 1) + ' a';
        angular.element( elementClass ).click();
      });
    }

    function onRemoveField(evt, index) {
      evt.preventDefault();
      $scope.entity.schema.splice(index, 1);

      resetAvailableFields();
    }

    function resetAvailableFields() {
      $scope.availableFields = _.filter($scope.originalFields, function(fieldName) {
        var usedFields = _.pluck($scope.entity.schema, 'name');
        return usedFields.indexOf(fieldName) < 0;
      });
    }
    
    function getFieldTypeByName( fieldName ) {
      var field = _.find( $scope.entity.discovered_schema, { name: fieldName } );
      return( field ? field.type : '' );
    }

    function onFieldNameInput(index) {
      // Pre-populate `type` and `field/expression` fields
      // if a label is selected from the predictor's schema fields
      var fields = $scope.entity.schema;
      if ($scope.availableFields.indexOf(fields[index].name) >= 0) {
        fields[index].type = getFieldTypeByName(fields[index].name);
        delete fields[index].is_expression;
      } else {
        fields[index].is_expression = true;
      }

      resetAvailableFields();
    }

    var searchSuggestions = function(term, suggestionsList, searchResultsList) {
      _.each(suggestionsList, function(item) {
        if (item.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          searchResultsList.push(item);
        }
      });
      return searchResultsList;
    };

    function searchExpressions(term) {
      var list = [];
      $scope._availableFields = searchSuggestions(term, $scope.availableFields, list);
    }

    function onSaveSchema() {
      var missingTypeOrExp = _.some($scope.entity.schema, function(field) {
        return (field.is_expression && !field.expression) || !field.type;
      });

      if (missingTypeOrExp) {
        SystemAlert.error('Some fields have missing type or expression');
        $scope.hasError = true;
        return;
      }

      console.log('Saving event type schema...', $scope.entity.schema);
      $scope.hasError = false;

      _EventTypesRest.updateSchema($scope.entityName, _.pick($scope.entity, 'schema'))
        .success(function(res) {
          SystemAlert.info('Updated schema successfully!');
          afterLoadEntity(res);
        });
    }

    function onApplySchema() {
      _EventTypesRest.applySchema($scope.entityName).success(function() {
        SystemAlert.info('Synchronization started');
        startRefresh();
      });
    }

    function onAcceptSchema() {
      _EventTypesRest.acceptSchema($scope.entityName).success(function() {
        SystemAlert.info('Accepted schema');
        startRefresh();
      });
    }

    function onCancelSchema() {
      _EventTypesRest.cancelSchema($scope.entityName).success(function() {
        SystemAlert.info('Cancelled schema');
        startRefresh();
      });
    }

    function reloadEntity() {
      return _EventTypesRest.getOne($scope.entityName).success(afterLoadEntity);
    }

    function startRefresh() {
      
      
      if ( angular.isDefined(pageRefresher) ) return;
      reloadEntity();
      pageRefresher = $interval(reloadEntity, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    var triesCount = 0;
    function isPendingEntity(entity) {
      triesCount++;
      return (entity.sync_status == 'SYNCING' || entity.sync_status == 'IMPORTING') && triesCount < 10;
    }

    function onShowErrors() {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: $scope.entity.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = "Event type '" + $scope.entityName + "'";

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
      });
    }

    function onSelectTab(tab) {
      if ($scope.currentTab) {
        $scope.currentTab.active = false;
      }
      $scope.currentTab = tab;
      $scope.currentTab.active = true;
    }
  }

})();