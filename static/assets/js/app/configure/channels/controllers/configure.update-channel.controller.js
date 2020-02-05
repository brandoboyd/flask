(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UpdateChannelCtrl', UpdateChannelCtrl);

  /** @ngInject */
  function UpdateChannelCtrl($http,
                             $interval,
                             $scope,
                             $routeParams,
                             $location,
                             $modal,
                             $timeout,
                             $window,
                             FilterService,
                             SocialService,
                             AccountsService,
                             ChannelsRest,
                             ChannelTypesRest,
                             EventTypesRest,
                             CompoundChannelService,
                             SystemAlert) {
    var _ChannelsRest = new ChannelsRest();
    var _ChannelTypesRest = new ChannelTypesRest();
    var _EventTypesRest = new EventTypesRest();

    $scope.channel = null;
    $scope.account = null;
    $scope.options = {};
    $scope.channel_id = $routeParams.channel_id;
    $scope.channelTypeSchema = null;
    $scope.eventTypes = [];

    $scope.intentions_filter = FilterService.getIntentions();

    AccountsService.query({}, function (res, code) {
      $scope.accounts = _.sortBy(_.pluck(res.data, 'name'), function (item) {
        return item.toLowerCase();
      });
      $scope.accountsObjs = angular.copy(res.data);

      $scope.$watch('channel', function (newVal, oldVal) {
        if (!newVal)
          return;
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.name == $scope.channel.account;
        });
        setRecoveryDateLimits();
      });
    });

    $scope.outboundChannelConfigured = false;
    $http.get('/get_outbound_channel/' + $scope.channel_id).then(function (data) {
      var channel = data.data.channel;
      if (channel && channel.is_authenticated) {
        $scope.outboundChannelConfigured = true;
      }
    });

    var setRecoveryDateLimits = function () {
      var minDate = new Date().add({days: -$scope.account.recovery_days});
      $scope.recoveryFromOptions = {
        minDate: minDate,
        maxDate: 0
      };
      $scope.recoveryToOptions = {
        minDate: 0,
        maxDate: 0,
        defaultDate: new Date()
      };
    };


    $scope.$on(SocialService.POPUP_CLOSE, function (evt, data) {
      if (data.type == 'twitter') {
        // popup closed - fetch profile
        $scope.getTwitterProfile();
      } else {
        $scope.getFacebookProfile();
      }
    });

    $scope.isChannelTypeValid = function () {
      var isValid = true;
      if ($scope.channel.type === 'FacebookServiceChannel') {
        isValid = ($scope.channel.facebook_page_ids && $scope.channel.facebook_page_ids.length) || ($scope.channel.facebook_event_ids && $scope.channel.facebook_event_ids.length);
      }
      return !!isValid;
    };

    $scope.isHistoryPeriodValid = function (value) {
      return (value !== 'undefined') && (value >= 1800 && value <= 1209600);
    };

    $scope.isRefreshIntervalValid = function (value) {
      return (value !== 'undefined') && (value == 0 || (value >= 5 && value <= 1440) || value == 100000);
    };

    $scope.isAutoRefreshConfigValid = function () {
      if ($scope.channel.type !== 'TwitterServiceChannel') {
        return true;
      }
      if (!$scope.refreshRelations.isOpened) return true;
      //if (!$scope.refreshRelations.isOpened && $scope.isHistoryPeriodValid($scope.channel.history_time_period)) return true;

      return $scope.isRefreshIntervalValid($scope.channel.auto_refresh_followers) && $scope.isRefreshIntervalValid($scope.channel.auto_refresh_friends) && $scope.isHistoryPeriodValid($scope.channel.history_time_period);
    };


    $scope.getTwitterProfile = function () {
      SocialService.twitterGetProfile($scope.channel_id, function (res) {
        $scope.twitter_profile = res.twitter_profile;
        if ($scope.channel != undefined) {
          if (res.twitter_profile != null) {
            $scope.channel.twitter_handle = res.twitter_profile.screen_name;
          }
          else $scope.channel.twitter_handle = null;
        }
      }, function onError() {
        $scope.twitter_profile = null;
        if ($scope.channel != undefined) $scope.channel.twitter_handle = null;
      });
    };

    $scope.getFacebookProfile = function () {
      SocialService.fbGetProfile($scope.channel_id, function (res) {
        $scope.facebook_profile = res.facebook_profile;
      }, function onError() {
        $scope.facebook_profile = null;
      });
    };

    $scope.twitter_request_token = function () {
      SocialService.twitterRequestToken($scope.channel_id);
    };

    $scope.facebook_request_token = function () {
      SocialService.facebookRequestToken($scope.channel_id);
    };

    $scope.twitter_logout = function () {
      SocialService.twitterLogout($scope.channel_id);
    };

    $scope.facebook_logout = function () {
      SocialService.facebookLogout($scope.channel_id);
    };

    $scope.load = function () {
      _ChannelsRest.getOne($scope.channel_id)
        .success(function (res) {
        $scope.channel = res.item;

        if ($scope.channel.is_dynamic) {
          fetchChannelTypeSchema($scope.channel.platform);
          fetchEventTypes($scope.channel.channel_type_id);
          return;
        } else {
            fetchEventTypes($scope.channel.id);
            return;
        }

        if ($scope.channel.type == "EnterpriseTwitterChannel") {
          $scope.getTwitterProfile();
        } else if ($scope.channel.type == "EnterpriseFacebookChannel") {
          $scope.getFacebookProfile();
        } else if ($scope.channel.is_service) {
          if ($scope.channel.type === "FacebookServiceChannel") {
            $http.get('/account_channels/' + $scope.channel_id).then(function (data) {
              $scope.options.dispatch_channels = data.data.data;
              if (!$scope.options.dispatch_channels) {
                SystemAlert.error('Please configure a channel of type "Facebook : Account" first.');
              }
            });
          }
        }

        // init for compound channel
        if ($scope.channel.is_compound || $scope.channel.is_service) {
          //console.log($scope.channel);
          CompoundChannelService.setCompound($scope.channel);
          CompoundChannelService.prepare();
          $scope.$on(CompoundChannelService.CHANGED, function (event, data) {
            _.forEach(data, function (item) {
              $scope.update_params[item.key] = item.value;
            });
          });
        }
      })
        .error(function () {
          SystemAlert.info('No channels availbale');
        });
    }();

    $scope.update_params = {};
    if ($scope.channel_id) {
      $scope.update_params = {channel_id: $scope.channel_id}
    }
    $scope.childScope = null;
    $scope.isAdvancedState = false;

    //need this to get to a child scope, the function is triggered from within ng-switch directive
    $scope.passTheScope = function (scope) {
      $scope.childScope = scope;
    };


    $scope.$watch('channel', function (newVal, oldVal) {
      if (newVal != oldVal) {
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.name == $scope.channel.account
        });

        if ($scope.channel.is_dynamic) {
          var defaultFields = ['title', 'description', 'account'];
          var schemaFields = _.pluck($scope.channelTypeSchema, 'name');
          var fields = defaultFields.concat(schemaFields);
          angular.extend($scope.update_params, _.pick($scope.channel, fields));
          return;
        }
        $scope.update_params = {
          channel_id: $scope.channel_id,
          title: $scope.channel.title,
          description: $scope.channel.description,
          account: $scope.channel.account,
          moderated_intention_threshold: $scope.channel.moderated_intention_threshold,
          auto_reply_intention_threshold: $scope.channel.auto_reply_intention_threshold,
          moderated_relevance_threshold: $scope.channel.moderated_relevance_threshold,
          auto_reply_relevance_threshold: $scope.channel.auto_reply_relevance_threshold,
          adaptive_learning_enabled: $scope.channel.adaptive_learning_enabled,
          review_outbound: $scope.channel.review_outbound,
          history_time_period: $scope.channel.history_time_period,
          skip_retweets: $scope.channel.skip_retweets,
          auto_refresh_friends: $scope.channel.auto_refresh_friends,
          dispatch_channel: $scope.channel.dispatch_channel,
          remove_personal: $scope.channel.remove_personal,
          posts_tracking_enabled: $scope.channel.posts_tracking_enabled,
          grouping_timeout: $scope.channel.grouping_timeout,
          grouping_enabled: $scope.channel.grouping_enabled
//                fb_pull_mode                   : $scope.channel.fb_pull_mode
        };
        if ($scope.childScope) {
          $scope.update_params['twitter_handle'] = $scope.childScope.channel.twitter_handle;
          $scope.update_params['tracking_mode'] = $scope.childScope.channel.tracking_mode;
        }
      }
    }, true);

    var _channelIds = [];
    function isNewService(channel) {
      var id = angular.isString(channel) ? channel : channel.id;
      return _channelIds.indexOf(id) !== -1 && channel.is_service;
    }

    $scope.update = function () {
      return _ChannelsRest.updateConfigureChannel($scope.update_params)
        .success(function(res) {
          if (res.item.is_dynamic) {
            SystemAlert.success("Channel has been updated.", 5000);
            return;
          }
          $scope.currentAccount = AccountsService.getCurrent();
          var selected_app = $scope.currentAccount.selected_app;
          if (isNewService(res.item) && selected_app !== 'GSE') {
            $window.location.href = '/inbound#/?channel=' + res.item.id + '&isNew';
          } else {
            $location.path('/channels');
            SystemAlert.success("Your reply channel has been updated.", 5000, 'account');
          }
      });
    };

    //Add this logic for the Advanced element, so it hides the ActionWords field
    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    }
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-expand-down";
      }
      else {
        return "icon-expand-right";
      }
    }
    $scope.changeStatus = function () {
      $scope.isAdvancedState = !$scope.isAdvancedState;
    };

    $scope.changeStatus();

    $timeout(function () {
      $scope.changeStatus()
    }, 1000);

    var extend = angular.extend;
    var BaseHistorics = {
      list: function (data) {
        if (!data.channel) return;
        return $http.get(this.baseUrl, {params: {channel: data.channel}});
      },
      postParams: ['channel', 'from_date', 'to_date', 'type'],
      start: function (data) {
        var params = _.pick(data, this.postParams);
        if (Object.keys(params).length != this.postParams.length) return;
        return $http.post(this.baseUrl, params);
      }
    };

    var Recovery = extend({}, BaseHistorics, {
      baseUrl: '/api/v2.0/historics',
      stop: function (id) {
        if (!id) return;
        return $http.put(this.baseUrl + '/' + id, {action: 'stop'});
      },
      resume: function (id) {
        if (!id) return;
        return $http.put(this.baseUrl + '/' + id, {action: 'resume'});
      }
    });

    var RelationsRefresh = extend({}, BaseHistorics, {
      baseUrl: '/api/v2.0/refresh_followers_friends',
      postParams: ['channel']
    });

    var Toggle = {
      isOpened: false,
      toggle: function () {
        this.isOpened = !this.isOpened;
        if (this.isOpened && !this.loaded) {
          this.load()
        }
      }
    };
    var Polling = {
      intervalPromise: null,
      startPolling: function () {
        var interval = 5000,
          self = this;

        if (self.intervalPromise !== null) return;
        if (!this.isRunning()) return;
        this.intervalPromise = $interval(function () {
          if (!self.isOpened) return;
          self.load().then(function () {
            if (!self.isRunning()) {
              $interval.cancel(self.intervalPromise);
              self.intervalPromise = null;
            }
          });
        }, interval);
      }
    };

    $scope.refreshRelations = extend({}, Toggle, Polling, {
      progressBars: [],
      current: {},

      load: function () {
        var self = this,
          postData = {channel: $scope.channel.id};

        return RelationsRefresh.list(postData).then(function (res) {
          self.current = res.data.item;
          self.loaded = true;
          self.progressBars = self.getProgressBars();
          self.lastSync = new Date(self.current.status_update * 1000).format('yyyy/mm/dd HH:MM Z');
          if (self.current.sync_status_friends == 'idle' && self.current.sync_status_followers == 'idle') {
            self.syncStatus = 'idle';
          } else {
            self.syncStatus = 'sync';
          }
          self.startPolling();
        });
      },

      canStart: function () {
        var ch = this.current;
        return (!this.isRunning() ||
        (ch.status == 'Active' &&
        ch.followers_synced >= ch.followers_count &&
        ch.friends_synced >= ch.friends_count));
      },

      isRunning: function () {
        return (this.current.status == 'Active' && (this.current.sync_status_friends != 'idle' || this.current.sync_status_followers != 'idle'));
      },

      isFinished: function () {
        return (this.current.sync_status_followers == 'idle' && this.current.sync_status_friends == 'idle');
      },

      start: function () {
        if (!this.canStart()) return;
        var postData = {channel: $scope.channel.id};
        return RelationsRefresh.start(postData).then(function (res) {
          var defaultMsg = 'The followers/friends refresh has been started. Please be patient.',
            message = res.data.message || defaultMsg;
          SystemAlert.success(message, 5000);
        }).then(this.load.bind(this));
      },

      getProgressBars: function () {
        var ch = this.current;
        return [{
          hint: 'followers',
          max: ch.followers_count,
          title: ch.followers_synced + '/' + ch.followers_count,
          value: ch.followers_synced
        },
          {
            hint: 'friends',
            max: ch.friends_count,
            title: ch.friends_synced + '/' + ch.friends_count,
            value: ch.friends_synced
          }];
      }
    });
    var timezoneOffsetMinutes = (new Date()).getTimezoneOffset(),
      tzOffsetHours = timezoneOffsetMinutes / 60,
      formattedOffset = tzOffsetHours > 0 ? "-" + tzOffsetHours : (tzOffsetHours < 0 ? "+" + -tzOffsetHours : "");

    $scope.recovery = extend({}, Toggle, Polling, {
      setDefault: function () {
        return (this.current = {
          channel: $scope.channel && $scope.channel.id,
          from_date: '',
          to_date: '',
          status: false,
          type:''
        });
      },
      label: {
        from: 'From (UTC' + formattedOffset + ')',
        to: 'To (UTC' + formattedOffset + ')'
      },
      current: {
        channel: $scope.channel && $scope.channel.id,
        from_date: '',
        to_date: '',
        type:''
      },

      canStart: function () {
        return !this.isRunning() && this.isFinished() || this.current.status === false;
      },
      isResumable: function () {
        var isResumableStatus = function (status) {
          return ['stopped', 'error'].indexOf(status) > -1;
        };
        return isResumableStatus(this.current.status);
      },
      isFinished: function () {
        return this.current.status == 'finished';
      },
      startNew: function () {
        this.setDefault();
        this.progressBars = this.getProgressBars();
      },
      isRunning: function () {
        return this.current.is_active;
      },
      canStop: function () {
        return this.current.is_stoppable;
      },
      load: function () {
        /* Load previous recovery list for current channel */
        var self = this;
        this.current.channel = $scope.channel.id;
        return Recovery.list(this.current).then(function (res) {
          var data = res.data,
            parseDate = function (d) {
              var dt = new Date(d * 1000 - timezoneOffsetMinutes * 60 * 1000);
              return dt.format('yyyy/mm/dd HH:MM');
            };

          if (data.items.length) {
            self.current = data.items[0];
            self.current.from_date = parseDate(self.current.from_date);
            self.current.to_date = parseDate(self.current.to_date);
          } else {
            self.setDefault();
          }
          self.loaded = true;
          self.progressBars = self.getProgressBars();
          self.startPolling();
        });
      },
      start: function () {
        if (!this.canStart()) return;
        this.loaded = false;
        this.current.channel = $scope.channel.id;
        var postData = extend({}, this.current);
        postData.from_date = (new Date(postData.from_date + ' UTC')).getTime() + timezoneOffsetMinutes * 60 * 1000;
        postData.to_date = (new Date(postData.to_date + ' UTC')).getTime() + timezoneOffsetMinutes * 60 * 1000;
        return Recovery.start(postData).then(function (res) {
          var defaultMsg = 'The recovery process has been started. Please be patient.',
            message = res.data.message || defaultMsg;
          SystemAlert.success(message, 5000);
        }).then(this.load.bind(this));
      },
      resume: function () {
        this.current.channel = $scope.channel.id;
        return Recovery.resume(this.current.id).then(this.load.bind(this));
      },
      stop: function () {
        this.current.channel = $scope.channel.id;
        return Recovery.stop(this.current.id).then(this.load.bind(this));
      },
      progressBars: [],
      getProgressBars: function () {
        if (this.isRunning() || this.isFinished() || this.isResumable()) {
          var p = this.current.progress;

          if (['TwitterHistoricalSubscription', 'TwitterRestHistoricalSubscription'].indexOf(this.current.type) > -1) {
            var pbs = [{
              hint: 'public tweets & direct messages',
              status: p.status,
              title: p.fetchers.progress + '%',
              value: p.fetchers.progress
            }];
            if (p.loader && p.loader.progress > 0) {
              pbs.push({
                hint: 'loading posts',
                status: p.status,
                title: p.loader.progress + '%',
                value: p.loader.progress
              });
            }
            return pbs;
          } else {
            return [{
              hint: '',
              status: this.current.status,
              title: '0%',
              value: 0
            }];
          }
        }
        return [];
      }
    });
  
    function fetchChannelTypeSchema(channel_type_name) {
      _ChannelTypesRest.getOne(channel_type_name).success(function(res) {
        $scope.channelTypeSchema = res.data.schema;
      });
    }

    function fetchEventTypes(channel_type_id) {
      _EventTypesRest.list(channel_type_id).success(function(res) {
        $scope.eventTypes = res.data;
      });
    }

    $scope.showImportDialog = function() {
      var modalInstance = $modal.open({
        templateUrl: 'partials/channels/events-import-modal',
        controller: 'EventsImportModalCtrl',
        size: 'md',
        resolve: {
          _channelId: function() { return $scope.channel.id },
          _eventTypes: function() { return $scope.eventTypes },
          _uploadFunc: function() { return _EventTypesRest.importData.bind(_EventTypesRest) },
        }
      });

      modalInstance.result.finally(function() {
        reloadEntity();
      });
    }
  }
})();
