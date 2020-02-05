(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditJourneyTagCtrl', CreateEditJourneyTagCtrl);

  /** @ngInject */
  function CreateEditJourneyTagCtrl($routeParams,
                                    $scope,
                                    $http,
                                    JourneyTagsRest,
                                    JourneyTypesRest,
                                    CustomerSegmentsRest) {
    var JourneyTags = new JourneyTagsRest();
    var JourneyTypes = new JourneyTypesRest();
    var CustomerSegments = new CustomerSegmentsRest();

    var id = $routeParams.id;
    $scope.title = id ? 'Update' : 'Create';
    $scope.journey_types = {};
    $scope.journey_stages = {};
    $scope.smart_tags = {
      list: []
    };
    $scope.customer_segments = [];
    $scope.item = {};
    $scope.formState = {};

    var resolveCtrl = function () {
      JourneyTypes.list().success(function (res) {
        $scope.journey_types = res.data;
        $scope.journey_stages = {};
        _.each($scope.journey_types, function (journey_type) {
          JourneyTypes.getStages(journey_type.id).success(function (stages) {
            $scope.journey_stages[journey_type.id] = stages.data.data;
          });
        });
      });

      CustomerSegments.list().success(function (res) {
        $scope.customer_segments = res.data;
      });

      $http.get('/smart_tags/json')
        .success(function (res) {
          $scope.smart_tags.list = _.map(res.list, function (item) {
            return {display_name: item.title, id: item.id, enabled: false}
          })
        })
    };

    $scope.filterSkipTags = function (tag) {
      return !_.contains($scope.item.skip_smart_tags, tag.id);
    };

    $scope.filterKeyTags = function (tag) {
      return !_.contains($scope.item.key_smart_tags, tag.id);
    };

    if (id) {
      JourneyTags.getOne(id).success(function (res) {
        $scope.item = res.data;
      });
    } else {
      $scope.item = newJourneyTag();
    }

    function newJourneyTag() {
      return {
        journey_type_id: null,
        display_name: "",
        description: "",
        tracked_stage_sequences: [],
        tracked_customer_segments: [],
        nps_range: [],
        csat_score_range: [],
        key_smart_tags: [],
        skip_smart_tags: []
      };
    }

    $scope.save = function () {
      $scope.formState.isSaved = false;
      JourneyTags.save($scope.item).success(function (res) {
        $scope.title = 'Update';
        $scope.item = res.data;
        $scope.formState.isSaved = true;
      });
    };

    $scope.openNewForm = function () {
      $scope.item = newJourneyTag();
      $scope.title = 'Create';
      $scope.formState.isSaved = false;
    };

    resolveCtrl();
  }
})();