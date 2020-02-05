(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EditChannelTypeCtrl', EditChannelTypeCtrl)

  /** @ngInject */
  function EditChannelTypeCtrl($scope, $routeParams, $q, $timeout, $location, ChannelTypesRest, MetadataService, toaster) {

    var _ChannelTypesRest = new ChannelTypesRest();

    $scope.entityName = null;
    $scope.entity = null;
    $scope.hasError = false;

    $scope.attributeTypes = MetadataService.getSchemaFieldTypes();

    $scope.onSaveEntity = onSaveEntity;
    $scope.onAddAttribute = onAddAttribute;
    $scope.onRemoveAttribute = onRemoveAttribute;

    activateController();

    function onSaveEntity() {
      // Validate channel type
      var hasMissingField =
        _.some($scope.entity.schema, function (e) {
          return (!e.type || (e.type && !e.name));
        })

      if (hasMissingField) {
        toaster.pop('error', 'Some attributes have missing name or type');
        $scope.hasError = true;
        return;
      }

      $scope.hasError = false;

      // SnakeCase or CamelCase field names so that they can be bound to models.
      // _.each($scope.entity.schema, function(field) {
      //   field.key = field.name.replace(/(?!^)([A-Z])/g, ' $1')
      //       .replace(/[_\s]+(?=[a-zA-Z])/g, '_').toLowerCase();
      // });

      var saveFn;
      if ($scope.entityName) {
        saveFn = _ChannelTypesRest.update($scope.entityName, _.pick($scope.entity, ['name', 'description', 'schema']));
      } else {
        saveFn = _ChannelTypesRest.create($scope.entity);
      }

      saveFn.success(function(res) {
        toaster.pop('info', 'Saved successfully!');

        if(!$scope.entityName) {
          $location.path('/channel_types');
        }

      }).catch(function(err) {
        console.log(err);
        // toaster.pop('error', 'Failed to save!');
      })
    }

    function onAddAttribute(evt) {
      evt.preventDefault();

      $scope.entity.schema.push({
        name: '',
        type: '',
      });
    }

    function onRemoveAttribute(evt, index) {
      evt.preventDefault();

      $scope.entity.schema.splice(index, 1);
    }

    function loadEntity() {
      if ($routeParams.name === 'new') {
        $scope.entity = {
          name: '',
          description: '',
          schema: [],
        };
        return $q.when();
      } else {
        $scope.entityName = $routeParams.name;
        return _ChannelTypesRest.getOne($scope.entityName)
          .success(function(res) {
            $scope.entity = res.data;
          });
      }
    }

    function activateController() {
      loadEntity();
    }
  }
})();
