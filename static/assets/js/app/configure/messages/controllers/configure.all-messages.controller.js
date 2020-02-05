(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AllMessagesCtrl', AllMessagesCtrl);

  /** @ngInject */
  function AllMessagesCtrl($scope, $location, $routeParams, Messages, Message, ChannelsService, DialogService) {
    $scope.messages = [];
    $scope.form_mode = null;
    $scope.filters = {
      'channel': null,
      'status': '',
      'creative': '',
      'limit': 30,
      'offset': 0
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

    $scope.filterPredicate = function (message) {
      var result = true;
      if ($scope.filters.creative) {
        result = result && message.creative.toLowerCase().indexOf($scope.filters.creative.toLowerCase()) != -1;
      }
      if ($scope.filters.status) {
        result = result && message.status == $scope.filters.status;
      }
      if ($scope.filters.channel) {
        result = result && message.channels.indexOf($scope.filters.channel) != -1;
      }
      return result;
    };

    $scope.selectAll = function () {
      $scope.selected = $scope.messages;
    };

    $scope.activate = function () {
      var ids = _.pluck($scope.selected, 'id');
      Message.activate({'ids': ids}, function (res) {
        _.each($scope.selected, function (item) {
          item.status = 'active';
        });
      });
    };

    $scope.deactivate = function () {
      var ids = _.pluck($scope.selected, 'id');
      Message.deactivate({'ids': ids}, function (res) {
        _.each($scope.selected, function (item) {
          item.status = 'inactive';
        });
      });
    };

    $scope.createMessage = function () {
      //$location.path('/messages/edit/');
      $scope.form_mode = 'creation';
      $location.path('/messages/edit/' + $scope.form_mode + '/' + ($routeParams.channel_id || ''));
    };

    $scope.edit = function (message) {
      if (!message) return;
      //$location.path('/messages/edit/').search({message_id: message.id});
      $scope.form_mode = 'edition';
      $location.path('/messages/edit/' + $scope.form_mode + '/' + message.id + '/' + $scope.filters.channel);
    };

    $scope.share = function () {
      var ids = _.pluck($scope.selected, 'id');

      DialogService.openDialog({target: 'acl', objectType: 'matchable', objectIds: ids});

      $scope.$on(DialogService.CLOSE, function () {
        $scope.selectAll();
      });
    };

    $scope.remove = function () {
      var ids = _.pluck($scope.selected, 'id');
      Message.remove({'ids': ids}, function () {
        $scope.messages = _.filter($scope.messages, function (item) {
          return _.indexOf(ids, item.id) == -1;
        });
      });
    };

    $scope.refresh = function (options) {
      if (options && options.redirect) {
        $location.path('/messages/all/' + $scope.filters.channel);
      }
      $scope.loadMessages();
    };

    $scope.loadMessages = function () {
      if ($routeParams.channel_id) {
        $scope.filters.channel = $routeParams.channel_id;
        //$routeParams.channel_id = undefined;
      }
      var params = {
        'offset': $scope.filters.offset,
        'limit': $scope.filters.limit,
        'channel': $scope.filters.channel,
        'status': $scope.filters.status,
        'search_term': $scope.filters.creative
      };

      Messages.list(params, function (res) {
        $scope.messages = res.list;

        $scope.filters.offset = res.offset;
        $scope.filters.limit = res.limit;
        $scope.size = res.size;

        var pages = res.size / res.limit;
        $scope.pages = Math.ceil(pages);
      });
    };

    //Make the first filters.status to be -- All Statuses --
    $scope.filters.status = "";

    ChannelsService.load('inbound', false, true);
    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function (scope, bookmark) {
      $scope.channels = ChannelsService.getList();
      if ($scope.channels.length != 0) {
        $scope.filters.channel = ChannelsService.getSelected() ? ChannelsService.getSelectedId() : $scope.channels[0];
        $scope.loadMessages();
      }
    });


    $scope.filters.currentPage = 0;
    $scope.pages = 0;

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

    $scope.$watch('filters.currentPage', function (nVal, oVal) {
      if (nVal !== oVal) {
        $scope.loadMessages();
      }
    });

    $scope.$watch('filters', function (newVal, oldVal) {
      if (newVal != oldVal)
        $scope.$emit('configure_messages_filters_changed');
    }, true);


  }
})();