(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ContactLabelsCtrl', ContactLabelsCtrl);

  /** @ngInject */
  function ContactLabelsCtrl($scope, ContactLabelsRest, ContactLabel, DialogService) {
    var ContactLabels = new ContactLabelsRest();
    var getSelectedItems = function (list) {
      return _.filter(list, function (item) {
        return item['is_selected'];
      });
    };


    var findItems = function (list, item) {
      var items = [];
      if (item) {
        items = [item];
      } else {
        items = getSelectedItems(list);
      }
      return items;
    };

    var findItemIds = function (label) {
      var items = findItems($scope.labels, label);
      return _.pluck(_.filter(items, function (el) {
        return el.perm == 's' || el.perm == 'rw'
      }), 'id');
    };

    $scope.labels = [];
    $scope.noLabelsAlert = false;

    $scope.filters = {
      'status': '',
      'title': ''
    };

    $scope.filterPredicate = function (tag) {
      var result = true;
      if ($scope.filters.title) {
        var title = tag.title || '';
        var description = tag.description || '';
        result = result && (title.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1 ||
          description.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1);
      }
      if ($scope.filters.status) {
        result = result && tag.status == $scope.filters.status;
      }
      return result;
    };

    var loadLabels = function () {
      ContactLabels.list().success(
        function (d) {
          $scope.labels = d.list;
          $scope.noLabelsAlert = $scope.labels.length == 0;
        }
      ).error(function () {
        $scope.noLabelsAlert = true;
      });
    };
    loadLabels();

    $scope.loadLabels = function (dates) {
      loadLabels();
    };

    $scope.deleteLabel = function (items) {
      ContactLabel.delete({"labels": items}, loadLabels);
    };

    $scope.share = function (item) {
      var ids = findItemIds(item);
      if (!ids.length) return;

      DialogService.openDialog({target: 'acl', objectType: 'ContactLabel', objectIds: ids});

      $scope.$on(DialogService.CLOSE, function () {
        $scope.deselectAll();
      });
    };

    $scope.activateLabel = function (items) {
      ContactLabel.activate({"labels": items}, loadLabels);
    };

    $scope.suspendLabel = function (items) {
      ContactLabel.deactivate({"labels": items}, loadLabels);
    };
    // Items Selection
    $scope.selectAll = function () {
      _.forEach($scope.labels, function (item) {
        item.is_selected = $scope.all_selected;
      });
    };

    $scope.deselectAll = function () {
      $scope.all_selected = false;
      $scope.selectAll();
    };

  }
})();