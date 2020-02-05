(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('GroupsListCtrl', GroupsListCtrl);

  /** @ngInject */
  function GroupsListCtrl($scope, $location, GroupsRest, DialogService) {
    var Groups = new GroupsRest();
    // Items Selection
    $scope.selected = [];
    $scope.filters = {
      name: ''
    };
    $scope.table = {
      sort: {
        predicate: 'name',
        reverse: false
      }
    };

    $scope.select = function (group) {
      if ($scope.selected.length) {
        var i = $scope.selected.indexOf(group);
        if (i === -1) {
          $scope.selected.push(group);
        } else {
          $scope.selected.splice(i, 1);
        }
      } else {
        $scope.selected.push(group);
      }
    };

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
      var items = findItems($scope.groups, label);
      return _.pluck(items, 'id');
    };


    // CRUD actions
    $scope.load = function () {
      Groups.list().success(function (res) {
        $scope.groups = _.map(res.data, function (item) {
          item.is_selected = false;
          return item;
        });
      });
    };

    $scope.create = function () {
      $scope.edit();
    };

    $scope.edit = function (group) {

      var groupId = group && group.id || '';
      $location.path('/groups/edit/' + groupId);
    };

    $scope.share = function (group) {
      var ids = findItemIds(group);
      if (!ids.length) return;

      DialogService.openDialog({target: 'acl', objectType: 'group', objectIds: ids});
    };

    $scope.delete = function (group) {
      if (!group) {
        var ids = _.pluck($scope.selected, 'id');
        _.each(ids, function (id) {
          removeFromGroups(id);
        });
      } else {
        var id = group.id;
        removeFromGroups(id);
      }
    };

    function removeFromGroups(id) {
      Groups.remove(id).success(function () {
        var i = $scope.groups.indexOf(_.findWhere($scope.groups, {id: id}));
        $scope.groups.splice(i, 1);
      });
    }

    $scope.hasAnyPerm = function () {
      return _.any($scope.groups, function (item) {
        return item.perm != 'r'
      });
    };

    $scope.load();

    //Additional Actions
    $scope.showUsers = function (group) {
      $location.path('/groups/edit/' + group.id + '/users/');
    };


  }
})();