(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AllTagsCtrl', AllTagsCtrl);

  /** @ngInject */
  function AllTagsCtrl($scope, $location, FilterService, SmartTags, SmartTag, ChannelsService, DialogService, SharedState) {
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

    $scope.selected = [];
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    var findItemIds = function (label) {
      var items = findItems($scope.tags, label);
      return _.pluck(_.filter(items, function (el) {
        return el.perm == 's' || el.perm == 'rw'
      }), 'id');
    };
    $scope.tags = [];
    //$scope.filters = AppState.store("configure_smart_tags_filters") || {
    $scope.filters = angular.extend(SharedState.filters, {
      channel: null,
      status: '',
      title: '',
      limit: 30,
      offset: 0
    });
    $scope.table = {
      sort: {
        predicate: 'name',
        reverse: false
      }
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
    $scope.edit = function (tag) {
      $location.path('/tags/edit/' + (tag ? tag.id : ''));
    };

    $scope.createSmartTag = function () {
      $scope.edit();
      $scope.mode = 'create';
    };

    $scope.delete = function () {
      _.each($scope.selected, function (tag) {
        var ids = findItemIds(tag);
        SmartTag.delete({ids: ids}, $scope.refresh);
      });
    };

    $scope.activate = function () {
      _.each($scope.selected, function (tag) {
        var ids = findItemIds(tag);
        if (!ids.length) return;

        SmartTag.activate({'ids': ids}, function () {
          $scope.refresh();
        });
      });
    };

    $scope.deactivate = function () {
      _.each($scope.selected, function (tag) {
        var ids = findItemIds(tag);
        if (!ids.length) return;

        SmartTag.deactivate({'ids': ids}, function () {
          $scope.refresh();
        });
      });
    };

    $scope.share = function (item) {
      var ids = findItemIds(item);
      if (!ids.length) return;

      DialogService.openDialog({target: 'acl', objectType: 'SmartTag', objectIds: ids});
    };


    $scope.refresh = function () {
      $scope.filters.offset = 0;
      $scope.loadSmartTags();
    };

    ChannelsService.load('inbound', false, true);
    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function (scope, bookmark) {
      $scope.channels = ChannelsService.getList();
      if ($scope.channels.length != 0) {
        $scope.filters.channel = ChannelsService.getSelected() ? ChannelsService.getSelectedId() : $scope.channels[0];
        $scope.refresh();
      }
    });


    $scope.loadSmartTags = function (dates) {
      if ($scope.filters.channel != null) {
        $scope.dateRange = dates || FilterService.getDateRange();
        var params = {
          offset: $scope.filters.offset,
          limit: $scope.filters.limit,
          channel: $scope.filters.channel,
          from: $scope.dateRange.from,
          to: $scope.dateRange.to
        };
        SmartTags.listAll(params).then(function (res) {
          $scope.tags = res.list;
          $scope.filters.offset = res.offset;
          $scope.filters.limit = res.limit;
          $scope.size = res.size;
          var pages = res.size / res.limit;
          $scope.pages = Math.ceil(pages);
        });
      }
    };

    $scope.filters.currentPage = 0;
    $scope.pages = 0;
    //Make the first filters.status to be Active
    //$scope.filters.status = "Active";

    // like python's range fn
    $scope.range = function (start, end) {
      var ret = [];
      if (!end) {
        end = start;
        start = 0;
      }
      for (var i = start; i < end; i++) {
        ret.push(i);
      }
      return ret;
    };

    $scope.prevPage = function () {
      if ($scope.filters.currentPage > 0) {
        $scope.filters.currentPage--;
        $scope.filters.offset = parseInt($scope.filters.offset) - parseInt($scope.filters.limit);
      }
    };

    $scope.nextPage = function () {
      if ($scope.filters.currentPage < $scope.pages - 1) {
        $scope.filters.currentPage++;
        $scope.filters.offset = parseInt($scope.filters.offset) + parseInt($scope.filters.limit);
      }
    };

    $scope.setPage = function () {
      $scope.filters.currentPage = this.n;
      $scope.filters.offset = (parseInt($scope.filters.limit) * this.n);
    };

    $scope.$watch('filters.currentPage', function (nVal) {
      $scope.loadSmartTags();
    });

    $scope.$watch('filters', function (newVal, oldVal) {
      if (newVal != oldVal)
        $scope.$emit('configure_messages_filters_changed');
    }, true);


  }
})();