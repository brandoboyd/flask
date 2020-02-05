(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditJourneyStageCtrl', CreateEditJourneyStageCtrl);

  /** @ngInject */
  function CreateEditJourneyStageCtrl($location,
                                      $routeParams,
                                      $scope,
                                      JourneyFacetConfig,
                                      SystemAlert,
                                      JourneyTypesRest) {
    var JourneyTypes = new JourneyTypesRest();
    var jtId = $routeParams.jtId,
      id = $routeParams.id;

    $scope.title = id ? 'Update' : 'Create';
    $scope.item = {};
    $scope.eventTypeItems = [];

    JourneyFacetConfig.getOptions(function (opts) {
      $scope.options = {stageStatuses: opts.journey_type.stageStatuses};
    });

    JourneyFacetConfig.getEventTypes(function (opts) {

      console.log("GET EVENT TYPES", opts);

      $scope.options = _.extend($scope.options, {eventTypes: opts.eventTypes});
    });

    function setJourneyType(item) {
      item = item || $scope.item;
      item.jtId = jtId;
      $scope.loadEventTypeItems();
    }

    function load() {
      if (!id) return;
      return JourneyTypes.getOneStage(jtId, id).success(function(res) {
        $scope.item = res.data;
        setJourneyType($scope.item);
      });
    }

    _.extend($scope,
      {
        redirectAll: function () {
          $location.path('/journey_types/edit/' + jtId);
        }
      },
      {
        "save": function () {
          $scope.item.event_types = [];
          $scope.item.must_have_rules = [];
          $scope.item.must_not_have_rules = [];
          _.each($scope.eventTypeItems, function (type) {
            if (type.id) {
              $scope.item.event_types.push(type.id);
              var obj1 = {}, obj2 = {};
              obj1[type.id] = type.must_have_rules;
              obj2[type.id] = type.must_not_have_rules;
              $scope.item.must_have_rules.push(obj1);
              $scope.item.must_not_have_rules.push(obj2);
            }
          });
          var params = {
            data: $scope.item,
            id: jtId
          };
          if (id) {
            _.extend(params, {stageId: id});
          }

          return JourneyTypes.saveStage(params).success(function () {
            SystemAlert.success('Journey Stage saved', 5000);
            $scope.redirectAll();
          });
        }
      });

    $scope.loadEventTypeItems = function () {
      if ($scope.item) {
        $scope.eventTypeItems.length = 0;
        _.each($scope.item.event_types, function (typeId) {
          var must_have_rules = _.find($scope.item.must_have_rules, function (obj) {
            return obj.hasOwnProperty(typeId)
          });
          var must_not_have_rules = _.find($scope.item.must_not_have_rules, function (obj) {
            return obj.hasOwnProperty(typeId)
          });
          $scope.eventTypeItems.push({
            'id': typeId,
            'must_have_rules': must_have_rules[typeId],
            'must_not_have_rules': must_not_have_rules[typeId]
          });
        });
      }
    };

    $scope.addEventTypeItem = function () {
      $scope.eventTypeItems.push({'id': null, 'must_have_rules': [], 'must_not_have_rules': []});
    };

    $scope.removeEventTypeItem = function (index) {
      $scope.eventTypeItems.splice(index, 1);
    };

    setJourneyType();
    load();
  }
})();