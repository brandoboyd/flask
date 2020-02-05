(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ChannelsListCtrl', ChannelsListCtrl);

  /** @ngInject */
  function ChannelsListCtrl($scope, $resource, $timeout, $location,
                            DialogService, AccountsService, FilterService, ChannelsRest, SystemAlert) {
    var _ChannelsRest = new ChannelsRest();
    $scope.filteredChannels = $scope.channels = [];
    $scope.noChannelsAlert = false;
    $scope.noChannelsShared = false;

    $scope.filterOptions = {
      platform: ["Twitter", "Facebook", "VOC", "Chat", "Web", "FAQ", "Email"]
    };

    $scope.filters = {
      channel: null,
      platform: '',
      status: '',
      title: '',
      limit: 30,
      offset: 0
    };

    $scope.table = {
      sort: {
        predicate: 'title',
        reverse: false
      }
    };
    angular.extend($scope.filters, $scope.table);

    var channelTypes = [];
    _ChannelsRest.getChannelTypes()
        .success(function (res) {
          channelTypes = res.list;
        });

    function filterChannels() {
      var opts = $scope.table.sort,
        filterFn = $scope.filterPredicate,
        channels = $scope.channels;

      var groupedByParent = _.groupBy(channels, function (ch) {
        return ch.parent || ch.id;
      });

      function sortGroup(group) {
        return _.sortBy(group, function (ch) {
          return ch.title;  // expected order: service, inbound, outbound
        });
      }

      function combineStats(group) {
        return _.reduce(group, function (result, item) {
          _.forEach(item.stats, function (val, key) {
            if (result.hasOwnProperty(key)) {
              result[key] += val;
            } else {
              result[key] = val || 0;
            }
          });
          return result;
        });
      }

      var groups = _(groupedByParent).map(function (group, id) {
        group = sortGroup(group);
        return {
          id: id,
          title: group[0].title,
          description: group[0].description,
          created_at: group[0].created_at,
          status: group[0].status,
          platform: group[0].platform,
          stats: combineStats(group),
          list: group
        }
      }).filter(filterFn);
      if (opts.reverse) {
        groups = groups.reverse();
      }


      var result = [];
      groups.forEach(function (item) {
        result.push.apply(result, item.list);
      });

      _.each(result, function (item, i) {
        var text = item.type_name;
        var txt = text.substring(0, text.indexOf("Channel"));
        var type = _.find(channelTypes, function (el) {
          return el.key == txt.toLowerCase()
        });

        if (type) {
          result[i].type_name = type.display;
        } else {
          result[i].type_name = text;
        }
      });


      $scope.filteredChannels = result;
    }

    $scope.$watch('filters', filterChannels, true);

    AccountsService.query({}, function (res, code) {
      $scope.accounts = _.sortBy(_.pluck(res.data, 'name'), function (item) {
        return item.toLowerCase();
      });
    });

    $scope.currentAccount = AccountsService.getCurrent();

    $scope.acctPredicate = function (channel) {
      if (!$scope.search || !$scope.search.account || $scope.search.account == '') return true;
      if ($scope.search.account == '* Null Accounts') return (channel.account == null);
      return (channel.account == $scope.search.account);
    };

    $scope.toggleChannel = function (channel) {
      if (channel.isActive) {
        suspendChannel(channel);
      } else {
        activateChannel(channel);
      }
      $scope.filteredChannels[$scope.filteredChannels.indexOf(channel)].isActive = !channel.isActive;
    };

    var ChannelCommands = $resource('/commands/:action', {}, {
      activate: {method: 'POST', params: {action: "activate_channel"}, isArray: false},
      suspend: {method: 'POST', params: {action: "suspend_channel"}, isArray: false},
      delete: {method: 'POST', params: {action: "delete_channel"}, isArray: false}
    });

    var loadChannels = function () {

      var postData = {
        widget: false,
        stats: true,
        from: $scope.dateRange.from,
        to: $scope.dateRange.to
      };
      //Make the first filters.status to -- All Statuses -- for channels
      //$scope.filters.status = "-- All Statuses --";
      _ChannelsRest.fetchChannels(postData).success(function (res) {
        $scope.channels = _.map(res.list, function(channel) {
          return _.extend(channel, {isActive: channel.status === 'Active'});
        });
        $scope.filterOptions.platform = _($scope.channels).pluck('platform').unique().pick(_.identity).values().value();
        filterChannels();
        //$scope.noChannelsAlert = $scope.channels.length == 0;
        if (res.list.length == 0) {
          $location.path('/new_channel/no-channels');
        }
        $scope.noChannelsShared = _.any(res.list, function (item) {
            if (item.perm == 'rw' || item.perm == 's')
              return true;
            else return false;
          }
        );
      }, function onError() {
        $scope.noChannelsAlert = true;
        $scope.noChannelsShared = true;
      });
    };

    $scope.$on(FilterService.DATE_RANGE_CHANGED, function () {
      $scope.dateRange = FilterService.getDateRange();
      loadChannels();
    });

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
      if ($scope.filters.platform) {
        result = result && tag.platform == $scope.filters.platform;
      }
      return result;
    };

    $scope.loadChannels = function (dates) {
      $scope.dateRange = dates;
      loadChannels();
    };

    function activateChannel(channel) {
      ChannelCommands.activate({"channels": [channel.id]}, function () {
        _.each($scope.filteredChannels, function (ch) {
          if (ch.id == channel.id) {
            ch.status = 'Active';
          }
        });
      });
    }

    function suspendChannel(channel) {
      ChannelCommands.suspend({"channels": [channel.id]}, function () {
        _.each($scope.filteredChannels, function (ch) {
          if (ch.id == channel.id) {
            ch.status = 'Suspended';
          }
        });
      });
    }

    $scope.deleteChannel = function (channel) {
      ChannelCommands.delete({"channels": [channel.id]}, loadChannels);     
    };


    $scope.all_selected = false;

    // Items Selection
    $scope.selectAll = function () {
      _.forEach($scope.channels, function (item) {
        item.is_selected = $scope.all_selected;
      });
    };

    $scope.deselectAll = function () {
      $scope.selectAll();
    };

    var getSelectedItems = function () {
      return _.filter($scope.channels, function (item) {
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
      var items = findItems($scope.channels, label);
      return _.pluck(_.filter(items, function (el) {
        return el.perm == 's' || el.perm == 'rw'
      }), 'id');
    };


    $scope.shareChannel = function (channel) {
      var ids = findItemIds(channel);

      if (!ids.length) return;
      DialogService.openDialog({target: 'acl', objectType: 'channel', objectIds: ids});

      $scope.$on(DialogService.CLOSE, function () {
        $scope.deselectAll();
      });
    }

    $scope.updateChannelAccount = function (channel) {
      channel._loadingState = 'loading';

      var _params = {
        channel_id: channel.id,
        account: channel.account
      };

      _ChannelsRest.updateConfigureChannel(_params)
        .success(function (res) {
          channel._loadingState = 'loaded';
          $timeout(function () {
            channel._loadingState = 'normal';
          }, 1000);
        })
        .error(function () {
        SystemAlert.info("Can not set account");
      });
    }
  }

})();