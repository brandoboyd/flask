angular.module('app_state_listen', ['slr.components', 'listen'])
  .factory('AppState', ['$rootScope', 'ChannelsService', 'FilterService', 'Posts', 'AppStore',
    function ($rootScope, ChannelsService, FilterService, Posts, AppStore) {


      $rootScope.section_settings = '';
      $rootScope.settings = {};

      $rootScope.$watch('global_section', function (section) {
        $rootScope.section_settings = 'settings' + section;
        $rootScope.settings = AppStore.read($rootScope.section_settings) ?
          AppStore.read($rootScope.section_settings) : {};
      });

      $rootScope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
        $rootScope.settings.channel = ChannelsService.getSelected();
        AppStore.store($rootScope.section_settings, $rootScope.settings);
      });

      return {
        read: AppStore.read
      }

    }
  ])
  .value('uiJqConfig', {

    // The Tooltip namespace
    tooltip: {
      animation: false,
      placement: 'bottom',
      container: 'body'
    }

  });

angular.module('listen', ['ui.select2',
    'ui.jq',
    'ui.scrollfix',
    'ngResource',
    'ngRoute',
    'ngSanitize',

    'slr.components',
  
    'app_state_listen',
    'infinite-scroll'])

  .factory('LocationHelper', function LocationHelper($location, $log, $rootScope, $sce, ChannelsService, SmartTags, FilterService) {
    var $scope;
    var setChannelFromLocation = function () {
      var routeParams = $location.search(),
        channels = ChannelsService.getList(),
        channel = null;

      $log.debug(channels);
      if (routeParams.isNew && routeParams.channel) {
        channel = findById(channels, routeParams.channel, 'parent_id') || findById(channels, routeParams.channel);
        if (channel) {
          $log.debug('set channel from location', channel);
          ChannelsService.setSelected(channel);
          $scope && $scope.changeChannel(channel);
        }
      }

      if (routeParams.tag && routeParams.channel) {
        var channel_id = routeParams.channel;
        var tag_id = routeParams.tag;
        if ($scope !== undefined) {
          $scope.switchTab('details');
          FilterService.setDateRange('This Month');
          channel = findById(channels, routeParams.channel, 'parent_id') || findById(channels, routeParams.channel);
          if (channel) {
            ChannelsService.setSelected(channel);
            $scope && $scope.changeChannel(channel);
          }
          SmartTags.fetch(channel_id).then(function (d) {
            $scope.smart_tags = d;
            var selected = _.indexOf(_.pluck(d, 'id'), tag_id);
            $scope.smart_tag.selected = $scope.smart_tags[selected];
            $scope.selected_smart_tags = [$scope.smart_tag.selected];
          });
        }
      }


      return channel;
    };

    $rootScope.$on('$locationChangeStart', setChannelFromLocation);

    var findById = function (list, id, idParam) {
      idParam = idParam || 'id';
      return _.find(list, function (item) {
        return item[idParam] === id;
      });
    };

    var isNewChannel = function () {
      var channel = ChannelsService.getSelected(),
        routeParams = $location.search();
      if (!channel) {
        return false;
      }
      return [channel.id, channel.parent_id].indexOf(routeParams.channel) !== -1 && routeParams.isNew;
    };

    return {
      setScope: function (scope) {
        $scope = scope;
        return this;
      },

      isNewChannel: isNewChannel,

      noDataMessageHeader: function () {
        var channel = ChannelsService.getSelected();
        if (isNewChannel()) {
          return $sce.trustAsHtml(" No data in the channel yet")
        } else {
          return null
        }
      },
      noDataMessage: function () {
        var channel = ChannelsService.getSelected();
        if (isNewChannel()) {
          var tpl = "Your channel '<channel name>' has been created, " +
              "it has started collecting new posts and comments. " +
              "It may take some time before users submit new posts related to you channel. " +
              "Please come back later and check, but in the meantime, please check out these short <training videos>. ",
            url = "https://docs.genesys.com/Documentation/TXT/Current/SocialAnalytics/Welcome",
            link = '<a href="<url>" target="_blank">training videos</a>'.replace('<url>', url);
          return $sce.trustAsHtml(tpl.replace('<channel name>', channel.title).replace('<training videos>', link));
        } else {
          return null; // default
        }
      },

      findChannel: function (stored_channel, service_channel) {
        //check if the stored channel exists in the list of available channels
        var channels = ChannelsService.getList(),
          valid_channel = service_channel ? findById(channels, service_channel.parent_id, 'parent_id') :
            stored_channel ? findById(channels, stored_channel.id) : null,
          channel;

        // check if redirected from channel create view
        channel = setChannelFromLocation();
        if (channel !== null) {
          return channel;
        }

        //check if we are came from widget

        if ($scope.widget) {
          channel = findById(channels, $scope.widget.extra_settings.channel_id);
        } else {
          channel = valid_channel ? valid_channel : ChannelsService.getSelected();
        }
        return channel;
      }
    };

  })

  .controller('ChannelsBookmarksCtrl',

    function ChannelsBookmarksCtrl($location,
                                   $log,
                                   $rootScope,
                                   $scope,
                                   AppState,
                                   ChannelsService,
                                   LocationHelper) {
      $scope.init = function (type, section) {
        //set section (comes from the template): inbound or outbound
        $rootScope.global_section = section;
        //pass channel_type, serviced_only, parent_names
        if (section != null) {
          ChannelsService.load(type, false, true);
        }

      };
      $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function (scope, bookmark) {
        var section_settings = 'settings' + $rootScope.global_section;
        var stored_channel = AppState.read(section_settings) ? AppState.read(section_settings)['channel'] : null;
        var service_channel = AppState.read("service_channel");

        $scope.channels = _.filter(ChannelsService.getList(), function(channel) {
          return channel.type == $rootScope.global_section;
        });
        $scope.channel = LocationHelper.setScope($scope).findChannel(stored_channel, service_channel);
      });

      $scope.$on('channel_event', function (e, data) {
        //channel created from tag
        if (data.event == 'created') {
          //Channels.load();
        }
      });

      $scope.changeChannel = function (ch) {
        $scope.channel = ch;
      };
      /* watchers */
      $scope.$watch('widget', function (nVal) {
        if (nVal) {
          $scope.channel = _.find($scope.channels, function (item) {
            return item.id == nVal.extra_settings.channel_id
          });
        }
      })
      $scope.$watch('channel', function (newVal, oldVal) {
        if (newVal !== oldVal) {
          ChannelsService.setSelected($scope.channel);
        }
      });

    })

  .controller('AnalyticsCtrl',
    function AnalyticsCtrl($anchorScroll,
                           $interval,
                           $location,
                           $log,
                           $modal,
                           $resource,
                           $rootScope,
                           $routeParams,
                           $sce,
                           $scope,
                           $timeout,
                           $window,
                           $http,
                           AgentsService,
                           ChannelsService,
                           FilterService,
                           LocationHelper,
                           MyTopics,
                           PlotTypes,
                           Posts,
                           PostsExport,
                           PostFilter,
                           Response,
                           SmartTag,
                           SmartTags,
                           SystemAlert,
                           TopicCloudMixin,
                           TrackingChannel,
                           TopicsCloud,
                           Topics,
                           Utils,
                           WidgetService,
                           AccountsService) {
      //DebugUtils.logWatches($scope);
      $scope.setButton = function (type) {
        if (type != 'topics') {
          PlotTypes.setType(type);
        }
        Posts.setSearchState(false);
      };


      $scope._ = _; //to use underscore in ng expressions;

      $scope.section = {
        is_search: Posts.getSearchState(),
        is_topics: false,
        is_details: false
      };
      $scope.isActive = function (type) {
        if ($scope.section.is_search || $scope.section.is_topics) {
          return false
        } else {
          return type == PlotTypes.getActiveType();
        }
      };

      var tabs = [
        {label: 'Details', name: 'details'},
        {label: 'Trends', name: 'time'},
        {label: 'Distribution', name: 'share'},
        {label: 'Topics Cloud', name: 'topics'}
      ];

      $scope.switchTab = function (type) {

        $scope.chartData = "LOADING...";

        if ($scope.section.is_topics && type != 'topics') {
          // update hot topics list when switching from topic cloud view
          $scope.section.is_topics = false;
          $scope.loadTopics();
        }

        $scope.tabName = _.findWhere(tabs, {name: type}).label;

        if (type == 'details') {
          $scope.searchByTab();
          $scope.section.is_topics = false;
          $scope.section.is_details = true;
          $scope.tabName = 'Details';

          if (!$scope.posts.length) { // not to load any data when we have already posts
            Posts.setSearchState(true);
          }
        } else if (type == 'topics') {
          $scope.section.is_topics = true;
          $scope.section.is_details = false;
          $scope.punks = [];
          $scope.loadTopics();
          $scope.setButton(type);
          Posts.setSearchState(false);
        } else {
          $scope.setButton(type);
          Posts.setSearchState(false);
          $scope.section.is_topics = false;
          $scope.section.is_details = false;
          //FilterService.setDateRange('This Month');
        }
      };
      $scope.switchTab('time'); // initial tab

      $scope.getTopicSize = function (count, type) {
        return TopicsCloud.getTopicSize(count);
      }

      $scope.getSelectedClass = function (item) {
        var selected = _.find($scope.myTopics, function (t) {
          return item.topic == t.topic
        })
        return selected ? 'selected' : '';
      }

      $scope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
        if ($scope.locationParams && $scope.locationParams.start) {
          $scope.switchTab('details');
          $scope.open();
        }
      });

      $scope.open = function () {
        $modal.open({
          templateUrl: '/partials/new_account/modal',
          controller: function ($scope) {
            var channel = ChannelsService.getSelected();
            $location.url($location.path() + '?' + $.param({channel: channel.id, isNew: 'yes'}));
            $scope.close = $scope.$close;
          }
        });
      };


        $scope.is_facet_disabled = false;
      $rootScope.$on('onJsonBeingFetched', function () {
        $scope.is_facet_disabled = true;
      });
      $rootScope.$on('onJsonFetched', function () {
        $scope.is_facet_disabled = false;
      });
      $rootScope.$watch('global_section', function (newVal, oldVal) {
        var page = $rootScope.global_section;
        PlotTypes.setPage(page);
        $scope.plot_filters = PlotTypes.getFilters();

        //check if we are came from widget
        if (!$scope.widget) {
          $scope.setFilter('topic');
        } else {
          $scope.setFilter($scope.widget.settings.group_by);
        }


        SmartTag.lru_tag = null;
      });

      //$scope.show_plot_filter = false;
      $scope.data = [];
      $scope.isPlotByVisible = true;
      $scope.options = {
        currentPlotBy: null,
        cloud_type: 'none',
      };

      $scope.setFilter = function (type) {
        $scope.options.currentPlotBy = _.find($scope.plot_filters, { type: type });
      };
      
      var TermStats = $resource('/trends/json', {}, {
        getGraphData: {method: 'POST', isArray: false}
      });

      $scope.lru_smart_tag = null;

      $rootScope.$on(SmartTag.LRU_TAG_CHANGED, function () {
        $scope.lru_smart_tag = SmartTag.lru_tag;
      });

      $scope.$watch('options.currentPlotBy', function(nVal, oVal) {
        if (nVal) {
          PlotTypes.setFilter(nVal.type);
        }
      });

      $scope.$watch('options.cloud_type', function(nVal, oVal) {
        if (nVal) {
          $scope.changeCloudView(nVal);
        }
      });

      $scope.shouldShowModerated = function (post) {
        return ($scope.smart_tag.selected_moderation &&
        (_.pluck(post.smart_tags, 'id').indexOf($scope.smart_tag.selected_moderation.id) < 0));
      };

      $scope.shouldShowLRU = function (post) {
        return ($scope.lru_smart_tag &&
        (_.pluck(post.smart_tags, 'id').indexOf($scope.lru_smart_tag.id) < 0) && !$scope.smart_tag.selected_moderation);
      };

      $scope.addModeratedTag = function (post) {
        SmartTags.addPostTags(ChannelsService.getSelectedId(), post.id_str,
          [$scope.smart_tag.selected_moderation.id]).then(function () {
          //scope.appliedTags.push(added_tag[0]);
          post.smart_tags.push($scope.smart_tag.selected_moderation);
        });
      };

      $scope.addLRUTag = function (post) {
        SmartTags.addPostTags(ChannelsService.getSelectedId(), post.id_str,
          [$scope.lru_smart_tag.id]).then(function () {
          //scope.appliedTags.push(added_tag[0]);
          post.smart_tags.push($scope.lru_smart_tag);
        });
      };

      $scope.getChannelId = function () {
        return $scope.smart_tag.selected ? $scope.smart_tag.selected.id
          : ChannelsService.getSelectedId();
      };


      var trendParams = null;
      $scope.getTrendParams = function () {
        $scope.dateRange = FilterService.getDateRange();
        return {
          agents: $scope.global_section == 'outbound' ? AgentsService.getParams() : null,
          channel_id: $scope.getChannelId(),
          level: FilterService.getSelectedGraphLevel(),
          statuses: $scope.global_section == 'outbound' ? [] : FilterService.getPostStatusesParams(),
          intentions: FilterService.getIntentionsParams(), //FilterService.getSelectedIntentions(),
          topics: MyTopics.getSelected(),
          plot_by: (PlotTypes.getActiveType() == 'share') ? 'distribution' : 'time',
          group_by: PlotTypes.getActiveFilter(),
          from: $scope.dateRange.from,
          to: $scope.dateRange.to,
          languages: FilterService.getLanguagesParams(),
          noDataMessage: LocationHelper.noDataMessage,
          noDataMessageHeader: LocationHelper.noDataMessageHeader
        }
      };

      var plot_by_to_filter_mappings = {
        topic: MyTopics.setTopics,
        intention: FilterService.setIntentions,
        status: FilterService.setStatuses
      };

      $scope.$on('analytics.details.trends', function(event, params) {
        plot_by_to_filter_mappings[params.filterName]([params.filterValue]);

        var level = FilterService.getSelectedGraphLevel();
        var from_date = moment.utc(params.timestamp);
        var to_date = moment.utc(params.timestamp).add(1, level);

        // set dateRange in utc format
        $scope.dateRange = {
          from: from_date.format('MM/DD/YYYY HH:mm:ss'),
          to: to_date.format('MM/DD/YYYY HH:mm:ss')
        };

        $scope.switchTab('details');
      });

      $scope.$on('analytics.details.distribution', function(event, params) {
        plot_by_to_filter_mappings[params.filterName]([params.filterValue]);

        $scope.switchTab('details');
      });

      $scope.noDataMessageHtml = function () {
        return $sce.trustAsHtml(Utils.noDataMessageHtml({
            noDataMessageHeader: LocationHelper.noDataMessageHeader,
            noDataMessage: LocationHelper.noDataMessage
          }
        ));
      };

      $scope.getStoredTrendParams = function () {
        var directive, target;
        if (!$scope.section.is_topics) {
          if (PlotTypes.getActiveType() == 'time') {
            directive = 'trend-chart';
            target = 'INTERACTION-TREND';
          } else {
            directive = 'distribution-chart';
            target = 'INTERACTION-DISTRIBUTION';
          }
        } else {
          directive = 'topics-cloud';
          target = 'INTERACTION-TOPICS';
        }

        var extra_settings = {
          request_url   : '/trends/json',
          source        : '/inbound#/?wid=',
          directive     : directive,
          target        : target,
          range_type    : FilterService.getSelectedDateRangeType(),
          range_alias   : FilterService.getSelectedDateRangeAlias(),
          channel_id    : ChannelsService.getSelectedId(),
          tag_id        : $scope.smart_tag.selected ? $scope.smart_tag.selected.id : null,
          widget_type   : $scope.section.is_topics ? 'topics' : 'chart',
          topics_params : getTopicParams(),
          yAxisFormat   : ',.0d',
          account_info  : AccountsService.getCompactAccount()
        };
        return {settings: trendParams, extra_settings: extra_settings};
      };

      $scope.buildingChart = false;

      $scope.loadGraph = function (type) {
        trendParams = $scope.getTrendParams();
        if (ChannelsService.getSelected()) {
          $scope.buildingChart = true;
          TermStats.getGraphData({}, trendParams,
            function (res) {
              $scope.isTrends = false;
              $scope.extra_settings = {
                target: 'ANALYTICS',
                drilldownEnabled: true,
                active_filter: PlotTypes.getActiveFilter()
              };
              if (type === 'time') {
                $scope.isTrends = true;
                $scope.chartData = parseTrendsData(res.list);
                angular.extend($scope.extra_settings, {
                  level: res.list.length ? res.list[0].level || 'day' : 'day',
                  yAxisLabel: 'Posts',
                  yAxisFormat: ',.0d',
                  chart_type: 'STACKED'
                });
              } else {
                $scope.isTrends = false;
                $scope.chartData = parsePieData(res.list);
                $scope.extra_settings.chart_type = 'PIE';
                $scope.extra_settings.valueFormat = ',.0d';
              }

              // Add display name in order to render readable format
              // For an instance, convert "junk" into "other", "problem" to "problems"
              _.each($scope.chartData, function(series) {
                var intention = _.find($scope.intentions_filter, {'label': series.label});
                if (intention) {
                  series._internalLabel = intention.label;
                  series.label = intention.display;
                }
              });
              $scope.buildingChart = false;
              Posts.setLevel(res.level);
            }, function onError() {
              //use it empty data for now
              $scope.buildPlotByType([], type);
            });
        } else {
          angular.noop();
        }

      };

      function parseTrendsData(list) {
        var parsedData = list;
        _.each(parsedData, function(series) {
          if (series.label === 'actual') {
            series.label = 'replied';
            series._internalLabel = 'actual';
          }
        });
        return parsedData;
      }

      function parsePieData(data) {
        return _.map(data, function (d) {
          var _internalLabel = d.label;
          if (d.label === 'actual') {
            d.label = 'replied';
          }
          return {
            label: d.label,
            _internalLabel: _internalLabel,
            value: d.data[0][1]
          };
        });
      }

        $scope.getPlotterURL = function() {
            if(!$scope.section.is_topics) {
                if (PlotTypes.getActiveType() == 'time') {
                    return "/partials/plot/time_plot"
                } else {
                    return "/partials/plot/share_plot"
                }
            } else {
                return "/partials/topics/cloud"
            }
        };


        $scope.$on(PlotTypes.ON_PLOT_TYPE_CHANGE, function() {
            $scope.loadGraph(PlotTypes.getActiveType());
            $scope.plot_filters = PlotTypes.getFilters();
        });

      $scope.$on(PlotTypes.ON_PLOT_FILTER_CHANGE, function () {
        $scope.loadGraph(PlotTypes.getActiveType());
      });

      $scope.buildPlotByType = function (plot_data) {
        $scope.data = plot_data;
      };

      $scope.hotTopics = [];
      $scope.topics = [];
      $scope.punks = [];
      $scope.isPunk = false;
      $scope.posts = [];
      $scope.user_tabs = [];
      $scope.default_profile_url = "/static/assets/img/default_profile2.png";
      $scope.myTopics = MyTopics.getSelected();
      $scope.post_search = '';
      $scope.selected_items = [];
      $scope.selected_items_ids = {};
      $scope.master = {checked: false};

      $scope.params = {
        thresholds: {
          intention: 0,
          influence: 0,
          receptivity: 0
        },
        terms: [],
        skip_creative: [],
        sort_by: 'time'
      };

      $scope.filterStatuses = ['rejected', 'discarded', 'starred', 'highlighted'];
      $scope.postFilterStatuses = {};
      _.forEach($scope.filterStatuses, function (status) {
        $scope.postFilterStatuses[status] = false;
      });
      $scope.postFilterStatuses.unfiltered = true;


      var UserProfile = $resource('/user_profile/json', {}, {
        fetch: {method: 'GET', isArray: false}
      });

      $scope.sortByOptions = {date: 'time', intention: 'confidence'};
      $scope.sort_by = 'date';
      $scope.sortBy = function (what) {
        $scope.params.sort_by = $scope.sortByOptions[what || 'date'];
        $scope.sort_by = what;
      };


      /*
       $scope.toggleAllSelected = function(items) {
       if ($scope.selected_items.length == items.length) {
       $scope.selected_items = [];
       } else {
       $scope.selected_items = items;
       }
       };
       */

      $scope.$watchCollection('selected_items_ids', function (nVal) {
        $scope.selected_items = [];
        angular.forEach($scope.selected_items_ids, function (v, k) {
          if (v) {
            $scope.selected_items.push(_.find($scope.posts, function (post) {
              return post.id_str == k
            }));
          } else {
            $scope.master.checked = false;
          }
        });
        if (_.isEmpty($scope.selected_items_ids)) {
          $scope.master.checked = false;
        }
      })

      $scope.toggleAll = function (check) {
        if (check) {
          var sel = _.map($scope.posts, function (num, key) {
            return [num.id_str, true]
          })
          $scope.selected_items_ids = _.object(sel);
        } else {
          $scope.selected_items_ids = {};
        }
      }


      $scope.showSearchResults = function (tab) {
        //Posts.setSearchState(true);
        $scope.post_search = '';
        //$scope.initIntentionsFilter(tab);
      };

      $scope.showHotTopics = function () {
        Posts.setSearchState(false);
      };


      var formatDate = function (date) {
        return dateFormat(date, "yyyy-mm-dd HH:MM:ss", false);
      };

     var getSearchParams = function (label) {
        var group_by = PlotTypes.getActiveFilter();
        var plot_by = PlotTypes.getActiveType();

        // Make check more specific to when an agent was deleted
        var agents = AgentsService.getParams();
        var intentions = label && group_by == 'intention' ? [label]
          : FilterService.getIntentionsParams();
        var topics = label && group_by == 'topic' ? MyTopics.getSelected()['length'] > 0 ? [{
          topic: label,
          topic_type: label
        }] : []
          : MyTopics.getSelected();
        var statuses = label && group_by == 'status' ? [label.series.label]
          : FilterService.getPostStatusesParams();
        var level = plot_by == 'time' ? (label ? label.series.level : FilterService.getSelectedGraphLevel())
            : FilterService.getSelectedTopicLevel();

        var from = formatDate($scope.dateRange.from);
        var to = formatDate($scope.dateRange.to);

        return {
          agents: $scope.global_section == 'outbound' ? agents : null,
          channel_id: $scope.getChannelId(),
          intentions: intentions,
          topics: topics,
          statuses: $scope.global_section == 'outbound' ? null : statuses,
          sort_by: $scope.params.sort_by,
          thresholds: $scope.params.thresholds,
          from: from,
          to: to,
          level: level,
          languages: FilterService.getLanguagesParams()
        }
      };

      var debounced_search_by_tab = _.debounce(Posts.searchByTab, 500);
      var debounced_search_by_grapgh = _.debounce(Posts.searchByGraph, 500);

      $scope.searchByTab = function () {
        Posts.resetPaging();
        $scope.graphItem = null;
        $scope.posts = [];
        $scope.showLoader = true;
        debounced_search_by_tab(getSearchParams());
      };

      $scope.exportPosts = function () {
        return PostsExport.exportPosts(angular.extend(
          getSearchParams(), {smartTag: $scope.smart_tag.selected}));
      };

      $scope.isBusy = false;
      $scope.graphItem = null;

      $scope.loadMore = function () {
        if ($scope.graphItem) {
            debounced_search_by_grapgh($scope.graphItem, getSearchParams($scope.graphItem));
        } else {
            debounced_search_by_tab(getSearchParams());
        }
      };

      $scope.searchByGraph = function (item) {

        Posts.resetPaging();
        $scope.graphItem = item;
        $scope.posts = [];
        $scope.showLoader = true;
        debounced_search_by_grapgh(item, getSearchParams(item));
      };

      $scope.reload = function () {
        updateViews(true);
      };

      $scope.channel_title = "";

      //TOPICS RELATED
      angular.extend($scope, TopicCloudMixin);

      var getTopicParams = function (term) {
        $scope.dateRange = FilterService.getDateRange();
        var params = {
          "channel_id": $scope.getChannelId(),
          "agents": $scope.global_section == 'outbound' ? AgentsService.getParams() : null,
          "statuses": $scope.global_section == 'outbound' ? [] : FilterService.getPostStatusesParams(),
          "parent_topic": term ? term.topic : null,
          "from": $scope.dateRange.from,
          "to": $scope.dateRange.to,
          "intentions": FilterService.getIntentionsParams(), //FilterService.getSelectedIntentions(),
          "level": FilterService.getSelectedTopicLevel(),
          "languages": FilterService.getLanguagesParams()

        };
        if ($scope.section.is_topics) {
          params.cloud_type = $scope.options.cloud_type;
        }
        return params;
      };
      $scope.getPunks = function (term) {
        if (term.topic_count != term.term_count) {
          Topics.search(term, getTopicParams(term)).then(function (d) {
            $scope.punks = d;
          });
        } else {
          if ($scope.section.is_topics) {
            $scope.punks = [];
          }
        }
      };


      $scope.loadTopics = function () {
        if (ChannelsService.getSelected()) {
          Topics.fetch(getTopicParams()).then(function (d) {
            $scope.hotTopics = _.defaults(d, {active: ''});
            $scope.punks = [];
          });
        }
      };

      $scope.backToHotTopics = function () {
        $scope.loadTopics();
      };

      $scope.clearSubCloud = function () {
        //$scope.punks  = [];
        $scope.isPunk = false;
      };

      $scope.add = function (el) {
        MyTopics.add(el);
      };
      $scope.remove = function (el) {
        MyTopics.remove(el);
        var topic = MyTopics.findTopic(el, $scope.hotTopics);
        if (topic) {
          topic.enabled = false;
          if (topic.active) {
            delete topic.active;
            $scope.punks = [];
          }
        }
      };

      $scope.activate = function (el, isSubCloud) {
        //deactivate first
        if (!isSubCloud) {
          $scope.deactivateTopics();
        }
        var selected = _.find($scope.myTopics, function (topic) {
            return topic.topic == el.topic
          }
        )
        if (!selected) {
          MyTopics.add(el);
        }

        el.active = 'active';
      }

      $scope.toggle = function (el) {
        if (el.enabled) {
          MyTopics.remove(el);
        } else {
          MyTopics.add(el);
        }
      };

      //USER PROFILE
      $scope.visitUserProfile = function (post) {
        var user = post.user.screen_name;
        var profile_url = post.user.profile_url;

        if (user && user !== 'anonymous') {
          //$window.location.href=profileBase + user;
          $window.open(profile_url)
        } else {
          SystemAlert.info("There is no profile for the user");
        }

      };
      $scope.user_profile = {};
      $scope.user_profile.posts = [];
      $scope.getUserProfile = function (post) {
        $scope.user_profile.posts = [];
        $scope.user_profile.user = post.user.screen_name;
        UserProfile.fetch(
          {
            channel_id: ChannelsService.getSelectedId(),
            user_name: $scope.user_profile.user
          }, function (res) {
            $scope.user_profile.posts = res.list;
          });
        $('#userProfileModal').modal('show');
      };

      var toggleStatus = function (post, status) {
        if (post.filter_status != 'actual') {
          $timeout(function () {
            post.filter_status = status
          }, 100);
        }
      };

      // Post actions
      var postStatusChanged = function (selection, status) {
        if (_.isArray(selection)) {
          _.each(selection, function (selected) {
            var post = _.find($scope.selected_items, function (item) {
              return selected == item.id_str
            });
            toggleStatus(post, status);
            updateViews(false);
          })
        } else {
          toggleStatus(selection, status);
        }
      };
      $scope.rejectPost = PostFilter.command('reject', postStatusChanged);
      $scope.starPost = PostFilter.command('star', postStatusChanged);

      $scope.addtagItems = function () {
        //check if the post has already such tag
        angular.forEach($scope.selected_items, function (post) {
          var same_tag = _.find(post.smart_tags, function (p) {
            return p.id == $scope.smart_tag.selected_moderation.id;
          })
          if (!same_tag) {
            post.smart_tags.push($scope.smart_tag.selected_moderation);
          }
        });
        SmartTags.addTagMultiPost($scope.getChannelId(), _.pluck($scope.selected_items, 'id_str'),
          $scope.smart_tag.selected_moderation.id).then(function () {
          updateViews(false);
        })
      };

      $scope.removetagItems = function () {
        angular.forEach($scope.selected_items, function (post) {
          post.smart_tags = _.filter(post.smart_tags, function (el) {
            return el.id !== $scope.smart_tag.selected.id;
          });
        });
        SmartTags.removeTagMultiPost($scope.getChannelId(), _.pluck($scope.selected_items, 'id_str'),
          $scope.smart_tag.selected.id).then(function () {
          updateViews(true);
        });
      };

      $scope.actionableItems = function () {
        PostFilter.command('star', postStatusChanged)(_.pluck($scope.selected_items, 'id_str'));
      };

      $scope.rejectItems = function () {
        PostFilter.command('reject', postStatusChanged)(_.pluck($scope.selected_items, 'id_str'));
      };

      $scope.$on(SmartTags.ON_POST_TAGS_REMOVED, function (event, response_id, post_id, tag_removed, is_conv) {
        var post = _.find($scope.posts, function (p) {
          return p.id_str == post_id
        });
        if (is_conv) {
          event.preventDefault()
        }
        var removed_tag = tag_removed || event.targetScope.tag;
        if ($scope.smart_tag.selected && $scope.smart_tag.selected.id == removed_tag.id) {
          post.tag_filter_status = "tag_rejected";
        }
      });

      /*
       $scope.onTagRemoved = function(elem) {
       if (elem.removeUIElement) {
       elem.targetElement.tag_filter_status = "tag_rejected";
       }
       };
       */
      /** AGENTS RELATED **/
      $scope.agents = [];

      $scope.setAllAgents = function (all) {
        AgentsService.setAll(all);
      };

      $scope.$watch('agents', function (newVal, oldVal) {
        if (newVal != oldVal) {
          AgentsService.setChanged(newVal);
        }
      }, true);


      // global listeners

      $scope.$on(AgentsService.ON_AGENTS_LOADED, function () {
        $scope.agents = AgentsService.getAll();
      });

      $scope.arePostsDisabled = false;
      $scope.$on(Posts.ON_POSTS_FETCHED, function (tab) {
        $timeout(function () {
          $scope.showLoader = false;
        }, 10)
        $scope.posts = Posts.getPosts();
        $scope.arePostsDisabled = false;

      });

      $scope.$on(Posts.ON_NO_MORE_POSTS, function (tab) {
        $timeout(function () {
          $scope.showLoader = false;
        }, 10)
      });

      $scope.$on(Posts.ON_POSTS_BEING_FETCHED, function (tab) {
        $timeout(function () {
          $scope.showLoader = true;
        }, 10)
        $scope.arePostsDisabled = true;
      });

      $scope.$on(Posts.ON_POSTS_FAILED, function (tab) {
        $scope.showLoader = false;
      });

      $scope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
        var channel = ChannelsService.getSelected();
        $scope.topics = [];
        $scope.channel_title = channel.channel_title;
        $scope.smart_tag.selected_moderation = null;
        if (ChannelsService.getSelected()) {
          if ($scope.global_section == 'outbound')
            AgentsService.fetchAgents();
          updateViews(true);
        }
      });

      $scope.$on(Posts.ON_SEARCH_PARAMS_UPDATED, function () {
        $scope.reload();
      });

      $scope.$on(Posts.ON_SEARCH_TAB_SELECTED, function () {
        $scope.section.is_search = Posts.getSearchState();
      });

      // listeners
      $scope.$watch('punks', function (newVal, oldVal) {
        if (newVal !== oldVal) {
          $scope.topics = $scope.punks;
          $scope.isPunk = true;
        }
      });

      $scope.$watch('hotTopics', function (newVal, oldVal) {
        if (newVal !== oldVal) {
          $scope.topics = $scope.hotTopics;
          $scope.isPunk = false;
          //updateViews(true);
        }
      });

      $scope.$watch("params", function (newVal, oldVal) {
        if (newVal != oldVal) {
          $scope.searchByTab();
        }
      }, true);

      /* NEW FACETS */
      $scope.filters = {
        smart_tags: {visible: false}
      }
      $scope.toggleFilter = function (fName) {
        var filter = $scope.filters[fName];
        return filter.visible ? filter.visible = false : filter.visible = true;
      };

      $scope.facets = {
        agents: {visible: false, all: true},
        intentions: {visible: false, all: true},
        topics: {visible: false, all: true},
        statuses: {visible: false, all: true},
        languages: {visible: false, all: true}
      };


      $scope.toggleFacet = function (facetName) {
        var facet = $scope.facets[facetName];
        return facet.visible ? facet.visible = false : facet.visible = true;
      };

      //$scope.statuses_filter = FilterService.setAllPostStatuses(true);
      $scope.statuses_filter = FilterService.getPostStatuses();

      /********* LANGUAGES **********/

      $scope.languages = [];
      $scope.updateLanguages = function () {
        FilterService.updateLanguages();
      }

      /********* INTENTIONS *********/

      $scope.intentions_filter = FilterService.getIntentions();

      $scope.updateIntentions = function () {
        FilterService.updateIntentions();
      };
      /*********END OF INTENTIONS **********/
      $scope.updatePostStatuses = function () {
        FilterService.updatePostStatuses();
      };

      $scope.resetAll = function () {
        $scope.facets.intentions.all = true;
        $scope.facets.agents.all = true;
        $scope.facets.topics.all = true;
        $scope.facets.statuses.all = true;
        $scope.facets.languages.all = true;
        $scope.deactivateTopics();
        $scope.smart_tag.selected = null;
        $scope.selected_smart_tags = [];
      };

      $scope.deactivateTopics = function () {
        _.each($scope.hotTopics, function (topic) {
          topic.active = ''
        });
        $scope.myTopics = [];
      };

      $scope.removeLanguage = function (item) {
        FilterService.removeLanguage(item)
      };

      $scope.removeIntention = function (item) {
        FilterService.removeIntention(item);
      };

      $scope.removeAgent = function (id) {
        AgentsService.removeAgent(id);
      };

      $scope.removeSmartTag = function (tag) {
        // remove from left panel facet
        if ($scope.smart_tag.selected === tag) {
          $scope.smart_tag.selected = null;
        }
        // remove selected facets from breadcrumbs area
        var idx = $scope.selected_smart_tags.indexOf(tag);
        if (idx !== -1) {
          $scope.selected_smart_tags.splice(idx, 1);
        }
      };

      $scope.removeStatus = function (item) {
        FilterService.removeStatus(item);
      };

      $scope.$watch('facets.languages.all', function (newVal) {
        FilterService.setIsAllLanguages(newVal);
        if (newVal) {
          FilterService.setLanguages([]);
        }
      });
      $scope.$watch('facets.intentions.all', function (newVal) {
        FilterService.setIsAllIntentions(newVal);
        if (newVal) {
          FilterService.setIntentions([]);
        }
      });
      $scope.$watch('facets.agents.all', function (newVal) {
        AgentsService.setIsAllSelected(newVal);
        if (newVal) {
          AgentsService.setAll(false);
        }
      });
      $scope.$watch('facets.topics.all', function (newVal) {
        $scope.facets['topics'];
        if (newVal) {
          MyTopics.purge();
        }
      });

      $scope.$watch('facets.topics.visible', function (newVal) {
        if (newVal == true) {
          $scope.loadTopics();
        }
      })

      $scope.$watch('facets.statuses.all', function (newVal) {
        FilterService.setIsAllStatuses(newVal);
        if (newVal) {
          FilterService.setStatuses([]);
        }
      });

      var updateViews = function (reload) {
        if (ChannelsService.getSelectedId() != null) {
          if ($scope.section.is_search) {
            if (reload) {
              $scope.searchByTab();
            }
            $timeout(function () {
              $scope.selected_items_ids = {};
              //clear cached tag!
              $scope.lru_smart_tag = null;
            }, 100)
          } else {
            $scope.loadGraph(PlotTypes.getActiveType());
          }
        }
      };
      var updateFacets = function () {
        if (ChannelsService.getSelectedId() != null) {
          updateViews(true);
          if ($scope.facets.topics.visible || $scope.section.is_topics) {
            $scope.loadTopics();
          }
        }
      };

      $scope.$on(FilterService.DATE_RANGE_CHANGED, function () {
        $scope.currentDate = FilterService.getSelectedDateRangeName();
        $scope.dateRange = FilterService.getDateRange();
        updateFacets();
      });

      $scope.$on(FilterService.LANGUAGES_CHANGED, function () {
        var selected = FilterService.getSelectedLanguages();
        if (selected.length > 0) {
          FilterService.setIsAllLanguages(false);
          $scope.selectedLanguages = selected;
          $scope.facets.languages.all = false;
        } else {
          $scope.selectedLanguages = [];
          $scope.facets.languages.all = true;
        }
        updateFacets();
      });

      $scope.$on(FilterService.INTENTIONS_CHANGED, function () {
        var selected = FilterService.getSelectedIntentions();
        if (selected.length > 0) {
          FilterService.setIsAllIntentions(false);
          $scope.selectedIntentions = selected;
          $scope.facets.intentions.all = false;
        } else {
          $scope.selectedIntentions = [];
          $scope.facets.intentions.all = true;
        }
        updateFacets();
      });

      $scope.$on(AgentsService.ON_AGENTS_CHANGED, function () {
        //$scope.agents = AgentsService.getAll();
        var selected = AgentsService.getSelectedTags();

        if (selected.length > 0) {
          AgentsService.setIsAllSelected(false);
          $scope.selectedAgents = selected;
          $scope.facets.agents.all = false;
        } else {
          $scope.selectedAgents = [];
          $scope.facets.agents.all = true;
        }
        updateFacets();
      });

      $scope.$on(FilterService.POST_STATUSES_CHANGED, function () {
        var selected = FilterService.getSelectedPostStatuses(true);
        if (selected.length > 0) {
          FilterService.setIsAllStatuses(false);
          $scope.selectedStatuses = selected;
          $scope.facets.statuses.all = false;
        } else {
          $scope.selectedStatuses = [];
          $scope.facets.statuses.all = true;
        }
        updateFacets();
      });

      $scope.$on(MyTopics.ON_TOPICS_CHANGE, function () {
        var selected = MyTopics.getSelected();
        if (selected.length > 0) {
          $scope.facets.topics.all = false;

        } else {
          $scope.facets.topics.all = true;
        }
        $scope.topics = MyTopics.testSelection($scope.topics);
        $scope.myTopics = MyTopics.getSelected();
        updateViews(true);
      });


      /* smart tags */
      $scope.smart_tags = [];
      $scope.smart_tag = {
        selected: null
      };

      var loadSmartTags = function (channel_id) {
        SmartTags.fetch(channel_id).then(function (d) {
          $scope.smart_tags = _.filter(d, function (tag) {
            return tag.direction === $scope.global_section || tag.direction == 'any'
          });
          if ($scope.smart_tag.selected != null) {
            var selected = _.indexOf(_.pluck(d, 'id'), $scope.smart_tag.selected.id);
            $scope.smart_tag.selected = $scope.smart_tags[selected];
          }
        });
      };

      $scope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
        var channel = ChannelsService.getSelected();
        loadSmartTags(channel.id);
        //LANGUAGES

        $scope.languages = FilterService.initLanguages(channel.langs);
        /*
         TrackingChannel.get_languages( {'channel_id' : channel.id }, function(res) {
         $scope.languages = FilterService.initLanguages(res.item);

         })
         */
        updateFacets();
      });

      $scope.$on(SmartTag.ON_SMARTTAG_UPDATE, function () {
        var channel = ChannelsService.getSelected();
        loadSmartTags(channel.id);
      });


      $scope.$watch('smart_tag.selected', function (nVal, oVal) {
//        $scope.topics = [];
        if ($scope.widget) {
          $scope.filters.smart_tags.visible = true
        }
        if (ChannelsService.getSelected()) {
          if ($scope.global_section == 'outbound') {
            AgentsService.fetchAgents();
          }
          updateFacets();
        }
        $scope.selected_smart_tags = $scope.smart_tag.selected ? [$scope.smart_tag.selected] : [];
      });


      $scope.scrollToTop = function () {
        // set the location.hash to the id of
        // the element you wish to scroll to.
        $location.hash('top');
        // call $anchorScroll()
        $anchorScroll();
      };

      /* Dashboard related */
      var lock = {
        removeWidget: false,
        updateWidget: false
      };
      $scope.removeWidget = WidgetService.makeRemove(lock, 'removeWidget');

      $scope.$on(WidgetService.CHANGED, function (evt, data) {
        lock.updateWidget = true;
        $scope.widget = data.widget;
      });

      $scope.dateRange = FilterService.getDateRange();
      $scope.currentDate = FilterService.getSelectedDateRangeName();

      $scope.$watch('widget', setupWidget);

      function setupWidget(nVal) {
        if (lock.updateWidget) {
          lock.updateWidget = false;
        }

        if (nVal && !_.isEmpty(nVal)) {

          if (nVal.settings.plot_by == 'distribution') {
            $scope.switchTab('share');
          }
          if (nVal.extra_settings.widget_type == 'topics') {
            $scope.switchTab('topics');
          }


          if (nVal.settings.intentions.length !== $scope.intentions_filter.length) {
            FilterService.setSelectedIntentions(nVal.settings.intentions);
          }
          if (nVal.settings.statuses
            && nVal.settings.statuses.length !== $scope.statuses_filter.length) {
            FilterService.setSelectedStatuses(nVal.settings.statuses);
          }
          if (nVal.settings.topics.length > 0) {
            MyTopics.add(nVal.settings.topics);
          }

          if (nVal.settings.languages && nVal.settings.languages.length > 0) {
            FilterService.setSelectedLanguages(nVal.settings.languages)
          }

          var selected_tag = $scope.widget.extra_settings.tag_id || ($scope.locationParams && $scope.locationParams.tag_id);
          $scope.dateRange = FilterService.getDateRange();
          FilterService.setDateRange($scope.widget.extra_settings.range_type);
          $scope.currentDate = FilterService.getSelectedDateRangeName();

          $scope.setFilter($scope.widget.settings.group_by);
          $scope.options.cloud_type = $scope.widget.extra_settings.topics_params.cloud_type;
          $scope.$watch('smart_tags.length', function (nVal, oVal) {
            if (nVal > 0) {
              if (selected_tag) {
                var selected = _.find($scope.smart_tags, function (item) {
                  return item.id === selected_tag;
                });
                $scope.smart_tag.selected = selected;
                $scope.selected_smart_tags = [$scope.smart_tag.selected];
              }

              if ($scope.locationParams != null && !(_.isEmpty($scope.locationParams))) {
                $scope.filters.smart_tags.visible = true;
                $scope.dateRange = FilterService.getDateRange();
                var selectedRange = FilterService.getDateRangeByAlias($scope.locationParams.range);
                if (selectedRange) {
                  FilterService.setDateRange(selectedRange.type);
                  $scope.currentDate = FilterService.getSelectedDateRangeName();
                }
              }
            } else {
              $scope.selected_smart_tags = [];
            }
          });
        }
      }

      $scope.locationParams = null;
      $scope.location = $location;
      $scope.$watch('location.search()', function (nVal) {
        $scope.locationParams = $location.search();
        if (lock.removeWidget) {
          return;
        }

        WidgetService.loadFromLocation().then(function (w) {
          $scope.widget = w;
          setupWidget($scope.widget);
        });

      }, true);

      var ReplyChannels = $resource('/reply_channels/json', {}, {
        fetch: {method: 'GET', isArray: false}
      })

      $scope.openReplyDialog = function (post) {

        $scope.dialogScope = {
          post: post,
          acc: AccountsService.getCurrent()
        };

        $scope.user_profile.posts = [];
        $scope.user_profile.user = post.user.screen_name;
        UserProfile.fetch(
          {
            channel_id: ChannelsService.getSelectedId(),
            user_name: $scope.user_profile.user
          }, function (res) {
            $scope.user_profile.posts = res.list;
          });
        $scope.signature = AccountsService.getCurrent().signature;
        $scope.post = {
          id_str: post.id_str,
          profile_image_url: post.user.profile_image_url,
          name: post.user.name,
          screen_name: post.user.screen_name,
          text: $sce.trustAsHtml(post.text),
          created_at: post.created_at,
          message_type: post.message_type
        };
        ReplyChannels.fetch(
          {},
          function (res) {
            $scope.channelsList = res.list;
            // if only one channel is present - select it
            if (res.list.length == 1) {
              $scope.replyChannel = res.list[0];
            }
          }
        );
        $('#replyModal').modal('show');

      }

      $scope.btnSendReplyEnabled = false;
      $scope.responseCommand = Response;

      $scope.postCustomReply = function (post, replyChannel, replyContent) {
        // reply is different from response because an agent may choose reply Channel for it
        if (!$scope.btnSendReplyEnabled) {
          return;
        }
        var param = {
          "creative": replyContent,
          "tag": replyChannel.id,
          "latest_post": post.id_str,
          "outbound_channel": replyChannel.id,
          "prefix": post.screen_name,
          "suffix": AccountsService.getCurrent().signature
        };
        $scope.responseCommand.post_reply(
          param,
          function (res) {
            $('#replyModal').modal('hide');
          }
        );
      };

      $scope.onReplyInputsChange = function () {
        if ($scope.replyChannel && $scope.replyContent !== null && $scope.replyContent) {
          $scope.btnSendReplyEnabled = true;
        } else {
          $scope.btnSendReplyEnabled = false;
        }
        document.getElementById('replyTextarea').focus();

        // TODO: this could be refactored with responseMessage in app.js
        var reply_max = 140;
        // 2 since 1 is for @-symbol, and 1 for a space
        var reply_length = $scope.replyContent.length + $scope.post.screen_name.length + 2;
        if ($scope.signature.length > 0) {
          reply_length += $scope.signature.length;
        }
        ;
        var reply_remaining = reply_max - reply_length;
        $scope.replyCountRemaining = reply_remaining;
        var textarea_counter = document.getElementById('textarea_counter');
        if (reply_remaining <= 3) {
          textarea_counter.style.color = 'red';
        } else if (reply_remaining > 3 && textarea_counter.style.color == 'red') {
          textarea_counter.style.color = 'black';
        }
        if (reply_remaining < 0) {
          $scope.btnSendReplyEnabled = false;
        }
      };

    });
