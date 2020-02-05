(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('JourneyTagListCtrl', JourneyTagListCtrl);

  /** @ngInject */
  function JourneyTagListCtrl($scope, JourneyTagsRest, JourneyTypesRest) {
    var JourneyTags = new JourneyTagsRest();
    var JourneyTypes = new JourneyTypesRest();
    $scope.table = {
      sort: {
        predicate: 'display_name',
        reverse: false
      }
    };

    $scope.filters = {
      display_name: ''
    };
    $scope.selected = [];
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    var resolveCtrl = function () {
      var journey_type_id_maps_title = {};
      JourneyTypes.list().success(function (res) {
        _.each(res.data, function (jt) {
          journey_type_id_maps_title[jt.id] = jt.display_name;
        });

        JourneyTags.list().success(function (tags) {
          $scope.items = _.map(tags.data, function (d) {
            return _.extend(d, {selected: false});
          });
          _.each($scope.items, function (item) {
            item.journey_type = journey_type_id_maps_title[item.journey_type_id];
          });
        });
      });
    };

    $scope.remove = function () {
      _.each($scope.selected, function (item) {
        JourneyTags.remove(item.id).success(function () {
          _.remove($scope.items, {id: item.id});
        });
      });
    };

    resolveCtrl();
  }
})();