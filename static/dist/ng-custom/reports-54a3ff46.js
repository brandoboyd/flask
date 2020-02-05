angular.module('app_state_reports', ['slr.components'])
  .factory('AppState', ['$rootScope', 'ChannelsService', 'AppStore',
    function ($rootScope, ChannelsService, AppStore) {
      $rootScope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
        AppStore.store("reports_channel", ChannelsService.getSelected());
      });

      return {
        read: function (name) {
          return AppStore.read(name);
        },
        find_by_id: function (list, itemId) {
          return _.find(list, function (el) {
            return el.id === itemId
          });
        }
      }

    }
  ])

var Reports = angular.module('reports', [
    'ui.scrollfix',
    'ngSanitize',
    'ngRoute',
    'ngResource',

    'slr.components',

    'app_state_reports',
    'infinite-scroll'
  ])
  .config(["$routeProvider", function ($routeProvider) {
    $routeProvider
      .when('/top-topics', {
        redirectTo: function (routeParams, path, search) {
          var encodeUrlParams = function (data) {
              var parts = [],
                encodeUri = encodeURIComponent;
              for (var key in data) {
                if (data.hasOwnProperty(key)) {
                  parts.push(encodeUri(key) + '=' + encodeUri(data[key]));
                }
              }
              return parts.join('&');
            },
            q = encodeUrlParams(search);
          return '/trending-topics' + '?' + q;

        }
      })
      .when('/trending-topics', {
        action: 'top-topics',
        name: 'Trending Topics',
        description: 'What are the trending topics?',
        tooltip: 'Topics that are appearing frequently in incoming social conversations'
      })
      .when('/missed-posts', {
        action: 'missed-posts',
        name: 'Missed Calls',
        description: 'How many posts have been missed?',
        tooltip: 'The average amount of actionable social conversations that did not receive a response'
      })
      .when('/inbound-volume', {
        action: 'inbound-volume',
        name: 'Call Volume',
        description: 'What is the inbound volume?',
        tooltip: 'The total amount of incoming social conversations'
      })
      .when('/first-contact-resolution', {
        action: 'first-contact-resolution',
        name: 'First Contact Resolution',
        description: 'How properly we address the customer\'s need the first time they contact us',
        //tooltip: 'Tooltip textgoes here'
      })
      .when('/work-done', {
        action: 'work-done',
        name: 'Work Done',
        description: 'The duration and length of conversations',
        //tooltip: 'Tooltip textgoes here'
      })
      .when('/response-time', {
        action: 'response-time',
        name: 'Response Time',
        description: 'What is the average response time?',
        tooltip: 'The average social response time'
      })
      .when('/response-volume', {
        action: 'response-volume',
        name: 'Response Volume',
        description: 'What is the response volume?',
        tooltip: 'The average amount of actionable social conversations that did receive a response'
      })
      .when('/sentiment', {
        action: 'sentiment',
        name: 'Sentiment',
        description: 'What is the user sentiment?',
        tooltip: 'A view of overall sentiment in incoming social conversations (such as, positive, negative, or neutral)'
      })
      .otherwise({redirectTo: '/response-time'});
  }])
  .value('uiJqConfig', {
    // The Tooltip namespace
    tooltip: {
      animation: false,
      placement: 'bottom',
      container: 'body'
    }
  });

Reports.controller('ReportsCtrl', ["$log", "$scope", "$rootScope", "$route", "$resource", "$timeout", "$location", "$sce", "$window", "$http", "$anchorScroll", "ChannelsService", "SmartTag", "SmartTags", "Posts", "PostsExport", "FilterService", "Topics", "TopicsCloud", "TrackingChannel", "MyTopics", "AgentsService", "PlotTypes", "PostFilter", "TopicCloudMixin", "WidgetService", "AccountsService", "Utils", function ($log,
                                            $scope,
                                            $rootScope,
                                            $route,
                                            $resource,
                                            $timeout,
                                            $location,
                                            $sce,
                                            $window,
                                            $http,
                                            $anchorScroll,
                                            ChannelsService,
                                            SmartTag,
                                            SmartTags,
                                            Posts,
                                            PostsExport,
                                            FilterService,
                                            Topics,
                                            TopicsCloud,
                                            TrackingChannel,
                                            MyTopics,
                                            AgentsService,
                                            PlotTypes,
                                            PostFilter,
                                            TopicCloudMixin,
                                            WidgetService,
                                            AccountsService, Utils) {
  angular.extend($scope, TopicCloudMixin);
  var lock = {
    showSubtopics: false,
    removeWidget: false
  };


  $scope._ = _; //to use underscore in ng expressions;

  //DebugUtils.logWatches($scope);

  $scope.submenu = {
    is: function () {
      return false;
    }
  };
  $scope.options = { cloud_type: 'none' };
  $scope.tabStatus = {};
  $scope.scrollingCalled = false;

  $scope.is_facet_disabled = false;
  $rootScope.$on('onJsonBeingFetched', function () {
    $scope.is_facet_disabled = true;
  });
  $rootScope.$on('onJsonFetched', function () {
    $scope.is_facet_disabled = false;
  });

  $rootScope.$on('$routeChangeSuccess', function (e) {
    if (lock.removeWidget) {
      return;
    }

    WidgetService.loadFromLocation().then(function () {
      $scope.widget = WidgetService.getCurrent();
      setupWidget($scope.widget);
    });

    var current = _.pick($route.current, 'name', 'action', 'description', 'tooltip', 'originalPath');
    current.is = function () {
      var names = angular.isArray(arguments[0]) ? arguments[0] : Array.prototype.slice.call(arguments, 0);
      return (names.indexOf(current.action) !== -1 ||
      new RegExp(names.join('|'), 'ig').test(current.originalPath));
    };
    $scope.submenu = current;

    PlotTypes.setPage($scope.submenu.action);
    $scope.resetAll(true);
    syncDateRangeButtons();
    $scope.tabStatus.isTopicsDisabled = true;
    $scope.topicsDisabledTooltip = "No Topics Cloud view available";
    $scope.distributionDisabledTooltip = "No distribution view available";

    if (_.isUndefined(current.action)) {
      return;
    }

    if (current.is('missed-posts', 'inbound-volume', 'response-time', 'response-volume')) {
      $scope.tabStatus.disabled = true;
    } else {
      $scope.tabStatus.disabled = false;
      $scope.distributionDisabledTooltip = "";
    }
    if (current.is('top-topics')) {
      if (!$scope.facets.topics.visible) {
        $scope.toggleFacet('topics');
      }
      $scope.tabStatus.isTopicsDisabled = false;
      $scope.topicsDisabledTooltip = "";

      if (current.is('trending-topics')) {
        $scope.getTopicCloud();
        $scope.changeCloudView('delta');
      }
    }
    if (current.is('response-time', 'response-volume')) {
      if (!$scope.facets.agents.visible) {
        $scope.toggleFacet('agents');
      }
    }
  });

  $scope.getFacetURL = function () {
    var baseFacetURL = "/partials/facets/";
    if ($scope.submenu.action) {
      return baseFacetURL + $scope.submenu.action;
    } else {
      return baseFacetURL + 'response-time';
    }
  };

  $scope.getSubMenuTooltip = function () {
    return "Hello";
  };

  ChannelsService.load('inbound', true, true);

  $scope.tab_options = {
    type: "time"
  };
  $scope.section = {
    is_search: Posts.getSearchState()
  };

  /* TABS' METHODS */

  $scope.isAllAgentsDisabled = false;

  $scope.getTrends = function () {
    blankReport();
    $scope.data = "loading";
    $scope.tab_options.type = 'time';
    PlotTypes.setType('time');
    $scope.isAllAgentsDisabled = false;
  };

  $scope.getDistribution = function () {
    blankReport();
    if ($scope.tabStatus.disabled) {
      return false
    } else {
      $scope.data = "loading";
      $scope.tab_options.type = 'share';
      PlotTypes.setType('share');
      if (PlotTypes.getActiveType() == 'share') {
        _.each($scope.agents, function (a) {
          a.enabled = true
        });
        $scope.isAllAgentsDisabled = true;
      }
    }
  };

  $scope.getDetails = function () {
    $scope.tab_options.type = 'details';
    $scope.searchByTab();
  };

  $scope.getTopicCloud = function () {
    if ($scope.submenu.is('top-topics')) {
      $scope.tab_options.type = 'topics';
    } else {
      return false;
    }
  };

  /* END OF TABS METHODS */

  //COMMON VARS
  $scope.setDateRange = function (range) {
    FilterService.setDateRange(range);
  };

  var getDateRangeButtons = function () {
    if ($scope.submenu.is('top-topics')) {
      return _.filter(FilterService.getDateRangeButtons(), function (item) {
        return _.indexOf(['Today', 'Yesterday', 'This Week'], item.type) !== -1
      })
    } else {
      return FilterService.getDateRangeButtons();
    }
  };


  var syncDateRangeButtons = function () {
    if (!$scope.submenu.is('inbound-volume', 'response-time', 'response-volume')) {
      if (FilterService.getSelectedDateRangeType() == 'Past 3 Months') {
        FilterService.setDateRange('Yesterday');
      }
    }
    $timeout(function () {
      $scope.currentDate = FilterService.getSelectedDateRangeName();
      ;
    }, 0);
  };

  syncDateRangeButtons();

  //TOPICS RELATED
  $scope.hotTopics = [];
  $scope.topics = [];
  $scope.myTopics = [];
  $scope.punks = [];
  $scope.isPunk = false;


  var getTopicsParams = function (term) {
    var params = {
      agents: $scope.submenu.is('sentiment', 'missed-posts', 'inbound-volume', 'top-topics') ? null : AgentsService.getParams(),
      channel_id: $scope.getChannelId(), //ChannelsService.getSelectedId(),
      parent_topic: term ? term.topic : null,
      from: $scope.dateRange.from.format('MM/DD/YYYY'),
      to: $scope.dateRange.to.format('MM/DD/YYYY'),
      intentions: $scope.submenu.is('sentiment', 'top-topics') ? null : FilterService.getIntentionsParams(),
      sentiments: $scope.submenu.is('sentiment') ? FilterService.getSentimentsParams() : null,
      level: FilterService.getSelectedTopicLevel(),
      statuses: $scope.submenu.is('top-topics') ? getPostStatusesParams() : null,
      plot_type: $scope.submenu.action,
      languages: FilterService.getLanguagesParams()
    };
    if ($scope.tab_options.type == 'topics') {
      params.cloud_type = $scope.options.cloud_type;
    }
    return params;
  };

  //TOPICS RELATED

  $scope.isAllOptionsShown = function () {
    return $scope.submenu.is('response-time', 'inbound-volume', 'response-volume');
  };

  $scope.getPunks = function (term) {
    lock.showSubtopics = true;
    if (term.topic_count != term.term_count) {
      Topics.search(term, getTopicsParams(term)).then(function (d) {
        $scope.punks = d;
        lock.showSubtopics = false;
      });
    } else {
      $scope.punks = [];
      lock.showSubtopics = false;
    }
  };

  $scope.getTopicSize = function (count) {
    return TopicsCloud.getTopicSize(count);
  }

  $scope.loadTopics = function () {
    var limit = $scope.submenu.is('top-topics') ? 15 : null;
    if (ChannelsService.getSelectedId() != null) {
      Topics.fetch(getTopicsParams(), limit).then(function (d) {
        $scope.hotTopics = _.defaults(d, {active: ''});
        $scope.punks = [];
      });
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

  $scope.deactivateTopics = function () {
    _.each($scope.hotTopics, function (topic) {
      topic.active = ''
    });
  }

  $scope.backToHotTopics = function () {
    $scope.loadTopics();
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

  $scope.toggle = function (el) {
    if (el.enabled) {
      MyTopics.remove(el);
    } else {
      MyTopics.add(el);
    }
  };

  // listeners
  $scope.$watch('punks', function (newVal, oldVal) {
    if (newVal !== oldVal) {
      ////console.log("WATCH PUNKS!!");
      $scope.topics = $scope.punks;
      $scope.isPunk = true;
    }
  });
  $scope.$watch('hotTopics', function (newVal, oldVal) {
    if (newVal !== oldVal) {
      ////console.log("WATCH HOT TOPICS!!");
      $scope.topics = $scope.hotTopics.slice(0);
      $scope.isPunk = false;
      if ($scope.submenu.is('top-topics') && $scope.firstTimeEarlyWarnings == true) {
        if ($scope.hotTopics.length) {
          MyTopics.add(_.first($scope.hotTopics, 15));
        }
        $scope.firstTimeEarlyWarnings = false;
      }
    }
  });

  $scope.reload = function () {
    $scope.searchByTab();
  };
  // END OF TOPICS

  // PLOTTING
  $scope.data = [];
  var setActiveFilter = function () {
    var active = PlotTypes.getActiveFilter();
    $scope.plot_filters = PlotTypes.getFilters();
    if (_.find($scope.plot_filters, function (el) {
        return el.type == active
      })) {
      PlotTypes.setFilter(active);
    } else {
      //set the first available filter or a 'topic' filter otherwise
      //PlotTypes.setFilter($scope.plot_filters.length > 0 ? $scope.plot_filters[0].type : 'topic' );
    }
  };

  $scope.$on(PlotTypes.ON_PLOT_TYPE_CHANGE, function () {
    setActiveFilter();
  });

  $scope.$watch('options.cloud_type', function(nVal, oVal) {
    if (nVal) {
      $scope.changeCloudView(nVal);
    }
  });

  $scope.setFilter = function (type) {
    PlotTypes.setFilter(type);
  };

  var Trends = $resource('/trends/json', {}, {
    getGraphData: {method: 'POST', isArray: false}
  });

  var getIntentionsParams = function () {
    if ($scope.submenu.is('sentiment', 'top-topics')) {
      return null
    } else if ($scope.submenu.is('missed-posts')) {
      return ['asks', 'problem', 'needs']
    } else {
      return FilterService.getIntentionsParams()
    }
  };

  var trendParams = null;
  var topicParams = null;

  $scope.getTrendParams = function () {
    return {
      channel_id: $scope.getChannelId(), //ChannelsService.getSelectedId(),
      agents: $scope.submenu.is('sentiment', 'missed-posts', 'inbound-volume', 'top-topics') ? null : AgentsService.getParams(),
      level: $scope.level,
      intentions: getIntentionsParams(),
      sentiments: $scope.submenu.is('sentiment') ? FilterService.getSentimentsParams() : null,
      topics: MyTopics.getSelected(),
      plot_by: (PlotTypes.getActiveType() == 'share') ? 'distribution' : 'time',
      group_by: PlotTypes.getActiveFilter(),
      from: $scope.dateRange.from.format('MM/DD/YYYY'),
      to: $scope.dateRange.to.format('MM/DD/YYYY'),
      plot_type: $scope.submenu.action,
      statuses: $scope.submenu.is('top-topics') ? getPostStatusesParams() : null,
      languages: FilterService.getLanguagesParams()
    };
  };


  $scope.getStoredTrendParams = function () {
    var directive, target;
    if ($scope.tab_options.type != 'topics') {
      if (PlotTypes.getActiveType() == 'time') {
        directive = 'trend-chart';
        target = 'NORMAL-TREND';
      } else {
        directive = 'distribution-chart';
        target = 'NORMAL-DISTRIBUTION';
      }
    } else {
      directive = 'topics-cloud';
      target = 'NORMAL-TOPICS';
    }

    var extra_settings = {
      request_url: '/trends/json',
      source: '/reports#/' + $scope.submenu.action + '?wid=',
      directive: directive,
      target: target,
      range_type: FilterService.getSelectedDateRangeType(),
      range_alias: FilterService.getSelectedDateRangeAlias(),
      channel_id: ChannelsService.getSelectedId(),
      tag_id: $scope.smart_tag.selected ? $scope.smart_tag.selected.id
        : null,
      report: $scope.submenu.action,
      topics: null,
      topics_params: getTopicsParams(),
      widget_type: $scope.tab_options.type == 'topics' ? 'topics' : 'chart',
      'account_info': AccountsService.getCompactAccount()
    };
    if ($scope.submenu.is('top-topics')) {
      extra_settings.topics = topicParams;
    }

    return {settings: trendParams, extra_settings: extra_settings};
  };


  $scope.loadGraph = function () {
    trendParams = $scope.getTrendParams();
    var params = $scope.getTrendParams();
    if ($scope.getChannelId() != null) {
      Trends.getGraphData({}, params, function (res) {
        $scope.buildGraph(res.list);
        Posts.setLevel(res.level);
      }, function onError() {
        $scope.data = [];
      });
    }
  };
  $scope.buildGraph = function (plot_data) {
    $scope.isTrends = false;
    $scope.extra_settings = {
      target: 'REPORTS',
      level: plot_data.length ? plot_data[0].level || 'day' : 'day',
      drilldownEnabled: true
    };
    if (PlotTypes.getActiveType() === 'time') {
      $scope.isTrends = true;
      $scope.chartData = plot_data;
      $scope.extra_settings = _.extend($scope.extra_settings, {
        yAxisLabel: 'Posts',
        yAxisFormat: ',.0d',
        chart_type: 'STACKED'
      });
    } else {
      $scope.isTrends = false;
      $scope.chartData = _.map(plot_data, function (d) {
        return {
          label: d.label,
          value: d.data[0][1]
        }
      });
      $scope.extra_settings.chart_type = 'PIE';
      $scope.extra_settings.valueFormat = ',.0d';
    }
  };

   var group_by_to_filter_mappings = {
     topics: MyTopics.setTopics,
     agents: AgentsService.setAgents,
     sentiments: FilterService.setSentiments
   };

  /** DRILDDOWNS */
  $scope.$on('reports.details.trends', function (event, params) {
    //console.log('params', params);
    var level = $scope.level || FilterService.getSelectedGraphLevel();
    var from_date = moment.utc(params.timestamp);
    var to_date = moment.utc(params.timestamp).add(1, level);

    // set dateRange in utc format
    $scope.dateRange = {
      from: from_date,
      to: to_date
    };
    $scope.level = 'hour';

    if (params.filterName) {
      group_by_to_filter_mappings[params.filterName]([params.filterValue]);
    }

    $scope.searchByTab(getSearchParams());
    $scope.tab_options.type = 'details';
  });

  $scope.$on('reports.details.distribution', function (event, params) {
    //console.log('params', params);
    group_by_to_filter_mappings[params.filterName]([params.filterValue]);
    $scope.searchByTab(getSearchParams());
    $scope.tab_options.type = 'details';
  });

  $scope.debounced_loadGraph = _.debounce($scope.loadGraph, 100);
  // END OF PLOTTING

  // POSTS RELATED

  $scope.posts = [];
  $scope.default_profile_url = "/static/assets/img/default_profile2.png";
  var formatDate = function (date) {
    return dateFormat(date, "yyyy-mm-dd HH:MM:ss", false);
  };

  var getSearchParams = function (item) {
    var group_by = PlotTypes.getActiveFilter();
    var plot_by = PlotTypes.getActiveType();

    // Make check more specific to when an agent was deleted
    var agents = [];
    if (item && group_by == 'agent') {
      var agentId = AgentsService.getAgentId(item.series.label);
      if (agentId != null) {
        agents = [agentId];
      }
    } else {
      agents = AgentsService.getParams();
    }

    var intentions = item && group_by == 'intention' ? [item.series.label]
      : getIntentionsParams();
    var topics = item && group_by == 'topic' ? MyTopics.getSelected()['length'] > 0 ? [{
      topic: item.series.label,
      topic_type: item.series.topic_type
    }] : []
      : MyTopics.getSelected();
    var sentiments = item && group_by == 'sentiment' ? [item.series.label]
      : FilterService.getSentimentsParams();
    var level,
      interval,
      zoomed = item && item.series && item.series.zoomed;
    if (zoomed) {
      level = zoomed.level;
      interval = {from: zoomed.from, to: zoomed.to};
    } else {
      level = item && plot_by == 'time' ? (item.series.level ? item.series.level : $scope.level)
        : FilterService.getSelectedTopicLevel();
      interval = item && plot_by == 'time' ? FilterService.getPostsDateRangeByPoint(item.datapoint[0], plot_by, level) : null;
    }

    var statuses = item && group_by == 'status' ? [item.series.label] : getPostStatusesParams();

    var from = interval ? formatDate(interval.from) : $scope.dateRange.from.format('YYYY-MM-DD HH:mm:ss');
    var to = interval ? formatDate(interval.to) : $scope.dateRange.to.format('YYYY-MM-DD HH:mm:ss');

    //console.log('from: ' + from, 'to: ' + to);

    return {
      agents: $scope.submenu.is('sentiment', 'missed-posts', 'inbound-volume', 'top-topics') ? null : agents,
      channel_id: $scope.getChannelId(), //ChannelsService.getSelectedId(),
      intentions: $scope.submenu.is('sentiment', 'top-topics') ? null : intentions,
      sentiments: $scope.submenu.is('sentiment') ? sentiments : null,
      topics: topics,
      statuses: $scope.submenu.is('top-topics') ? statuses : null,
      plot_type: $scope.submenu.action,
      sort_by: $scope.params.sort_by,
      thresholds: $scope.params.thresholds,
      from: from,
      to: to,
      level: level,
      languages: FilterService.getLanguagesParams()
    }
  };

  var debounced_search_by_tab = _.debounce(Posts.searchByTab, 400);
  var debounced_search_by_grapgh = _.debounce(Posts.searchByGraph, 400);

  $scope.searchByTab = function (params) {
    ////console.log("reset paging!!!");
    Posts.resetPaging();
    $scope.graphItem = null; //reset graph search params
    $scope.posts = [];
    //$scope.showLoader = true;
    $scope.loadMoreParams = params || getSearchParams(null);
    debounced_search_by_tab($scope.loadMoreParams);
  };
  $scope.searchByGraph = function (item) {
    Posts.resetPaging();
    $scope.graphItem = item; //store the graph object between paging
    $scope.posts = [];
    $scope.showLoader = true;
    debounced_search_by_grapgh(item, getSearchParams(item));
  };
  $scope.exportPosts = function () {
    return PostsExport.exportPosts(angular.extend(
      getSearchParams(), {smartTag: $scope.smart_tag.selected}));
  };

  $scope.isBusy = false;
  $scope.graphItem = null;

  $scope.loadMore = function () {
    //console.log("Call loadMore!!!");
    if ($scope.graphItem) {
      debounced_search_by_grapgh($scope.graphItem, getSearchParams($scope.graphItem));
    } else {
      //console.log('loadMoreParams', $scope.loadMoreParams);
      debounced_search_by_tab($scope.loadMoreParams);
    }
  }

  $scope.sortByOptions = {date: 'time', intention: 'confidence'};
  $scope.sort_by = 'date';
  $scope.sortBy = function (what) {
    $scope.params.sort_by = $scope.sortByOptions[what || 'date'];
    $scope.sort_by = what;
  };

  // Post actions
  var postStatusChanged = function (post) {
    post.is_disabled = true;
    //$scope.searchByTab();
  };
  $scope.rejectPost = PostFilter.command('reject', postStatusChanged);
  $scope.starPost = PostFilter.command('star', postStatusChanged);


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

  $scope.onTagRemoved = function (elem) {
    if (elem.removeUIElement) {
      elem.targetElement.tag_filter_status = "tag_rejected";
    }
  };

  // END OF POSTS RELATED

  var getPostStatusesParams = function () {
    return _.filter(FilterService.getPostStatusesParams(), function (item) {
      return _.indexOf(['actual', 'actionable'], item) !== -1
    });
  };

  var getPostStatuses = function () {
    return _.filter(FilterService.getPostStatuses(), function (item) {
      return _.indexOf(['actual', 'actionable'], item.label) !== -1
    });
  };

  $scope.statuses_filter = getPostStatuses();

  $scope.updatePostStatuses = function () {
    FilterService.updatePostStatuses();
  };
  $scope.removeStatus = function (item) {
    FilterService.removeStatus(item);
  };
  $scope.$watch('facets.statuses.all', function (newVal) {
    FilterService.setIsAllStatuses(newVal);
    if (newVal) {
      FilterService.setStatuses([]);
    }
  });

  /******** TEAM/AGENTS *********/

  /** AGENTS RELATED **/
  $scope.agents = [];


  $scope.setAllAgents = function (all) {
    AgentsService.setAll(all);
  };


  $scope.getSelectedAgents = function (agents) {
    return _.filter(agents, function (a) {
      return a.enabled == true
    });
  }

  $scope.$watch('agents', function (newVal, oldVal) {
    var selected = $scope.getSelectedAgents(newVal);
    if (selected.length > 0) {
      $scope.setFilter('agent');
    } else {
      PlotTypes.resetPlotFilters();
    }
    if (newVal != oldVal) {
      AgentsService.setChanged(newVal);
    }
  }, true);


  // global listeners

  $scope.$on(AgentsService.ON_AGENTS_LOADED, function () {
    $scope.agents = AgentsService.getAll();
    if ($scope.widget && $scope.widget.settings.agents) {
      AgentsService.setChangedByIds($scope.widget.settings.agents);
    }
  });
  /******* END OF AGENTS *********/


  /********* SENTIMENTS AND INTENTIONS *********/
  $scope.intentions_filter = FilterService.getIntentions();
  $scope.sentiments_filter = FilterService.getSentiments();

  $scope.updateIntentions = function () {
    FilterService.updateIntentions();
  };
  $scope.updateSentiments = function () {
    FilterService.updateSentiments();
  };

  var updateViews = function (reload) {
    if ($scope.tab_options.type !== 'details') {
      if ($scope.submenu.is('sentiment')) {
        PlotTypes.setFilter('sentiment', true);
      } else if ($scope.submenu.is('top-topics')) {
        PlotTypes.setFilter('topic', true);
      }
      //$scope.loadGraph();
      $scope.debounced_loadGraph();
    } else {
      if (reload) {
        $scope.searchByTab();
      }
      $timeout(function () {
        $scope.selected_items_ids = {};
      }, 100)
    }

    if ($scope.facets.topics.visible && $scope.punks.length == 0 && !lock.showSubtopics) {
      $scope.loadTopics();
    }
  };


  var debounced_updateViews = _.debounce(updateViews, 100);

  var blankReport = function () {
    if ($scope.topics === undefined) {
        $scope.topics = [];
    }
    if ($scope.agents === undefined) {
        $scope.agents = [];
    }
    if ($scope.myTopics === undefined) {
        $scope.myTopics = MyTopics.purge();
    }
    if ($scope.params.thresholds === undefined) {
        $scope.params.thresholds = {intention: 0};
    }
    if ($scope.agents.length === 0) {
        if ($scope.submenu.is('response-time', 'response-volume')) {
          AgentsService.fetchAgents();
        }
    }
    $scope.chartData = "LOADING";
    $scope.firstTimeEarlyWarnings = true;
    debounced_updateViews(true);
  };

  /*  DETAILS SPECIFIC */
  $scope.params = {
    thresholds: {
      "intention": 0
    },
    sort_by: 'time'
  };

  $scope.$watch("params", function (newVal, oldVal) {
    if (newVal != oldVal) {
      $scope.searchByTab();
    }
  }, true);
  /* END DETAILS SPECIFIC */

  $scope.$watch('facets.topics.visible', function (newVal) {
    if (newVal == true) {
      $scope.loadTopics();
    }
  })


  /* smart tags */
  $scope.smart_tags = [];
  $scope.smart_tag = {
    selected: null
  };
  $scope.getChannelId = function () {
    return $scope.smart_tag.selected ? $scope.smart_tag.selected.id
      : ChannelsService.getSelectedId();
  };
  var loadSmartTags = function (channel_id) {
    SmartTags.fetch(channel_id).then(function (d) {
      // show tags only with inbound or any direction
      $scope.smart_tags = _.filter(d, function(tag) {
        return ['inbound', 'any'].indexOf(tag.direction) >= 0
      });

      if ($scope.smart_tag.selected != null) {
        var selected = _.indexOf(_.pluck(d, 'id'), $scope.smart_tag.selected.id);
        $scope.smart_tag.selected = $scope.smart_tags[selected];
      }
    });
  };

  $scope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
    blankReport();
    var channel = ChannelsService.getSelected();
    loadSmartTags(channel.id);
    $scope.languages = FilterService.initLanguages(channel.langs);
    /*
     TrackingChannel.get_languages( {'channel_id' : channel.id }, function(res) {
     $scope.languages = FilterService.initLanguages(res.item);
     })
     */
    $scope.smart_tag.selected_moderation = null;
  });
  $scope.$on(SmartTag.ON_SMARTTAG_UPDATE, function () {
    var channel = ChannelsService.getSelected();
    //blankReport(false);
    loadSmartTags(channel.id);
  });


  $scope.$watch('smart_tag.selected', function (nVal, oVal) {
    //blankReport();
    if ($scope.widget) {
      $scope.filters.smart_tags.visible = true
    }
    $scope.selected_smart_tags = $scope.smart_tag.selected ? [$scope.smart_tag.selected] : [];
    debounced_updateViews(true);
  });

  $scope.firstTimeEarlyWarnings = true;
  $scope.isPlotByVisible = false;


  $scope.$watch('submenu.action', function (newPage) {
    if (!newPage) return;
    if (ChannelsService.getSelected() != null) {
      blankReport();
      //no grouping by default;
      PlotTypes.resetPlotFilters();
      if (newPage == 'sentiment') {
        PlotTypes.setFilter('sentiment', true);
        $scope.getTrends();
      } else if (newPage == 'top-topics') {
        PlotTypes.setFilter('topic', true);
        $scope.firstTimeEarlyWarnings = true;
      } else {
        $scope.getTrends();
      }
    }
  });

  $scope.$on(Posts.ON_SEARCH_TAB_SELECTED, function () {
    $scope.tab_options.type = 'details';
  });

  $scope.$on(Posts.ON_POSTS_FETCHED, function (tab) {
    $timeout(function () {
      $scope.showLoader = false;
    }, 500)
    $scope.posts = Posts.getPosts();
  });

  $scope.$on(Posts.ON_NO_MORE_POSTS, function (tab) {
    $timeout(function () {
      $scope.showLoader = false;
    }, 500)
  });

  $scope.$on(Posts.ON_POSTS_BEING_FETCHED, function (tab) {
    $timeout(function () {
      $scope.showLoader = true;
    }, 10)
  });

  $scope.$on(Posts.ON_POSTS_FAILED, function (tab) {
    $scope.showLoader = false;
  });


  $scope.$on(MyTopics.ON_TOPICS_CHANGE, function () {
    $scope.myTopics = MyTopics.getSelected();
    $scope.plot_filters = PlotTypes.getFilters();

    var selected = MyTopics.getSelected();
    if (selected.length > 0) {
      $scope.facets.topics.all = false;
    } else {
      //MyTopics.purge();
      $scope.facets.topics.all = true;
    }
    $scope.topics = MyTopics.testSelection($scope.topics);
    debounced_updateViews(true);
  });

  $scope.$on(FilterService.DATE_RANGE_CHANGED, function () {
    $scope.firstTimeEarlyWarnings = true;
    var dr = FilterService.getDateRange();
    $scope.dateRange = {
      from: moment(dr.from).utc(),
      to: moment(dr.to).utc()
    };
    $scope.level = FilterService.getSelectedGraphLevel();
    debounced_updateViews(true);
  });

  $scope.$on(PlotTypes.ON_PLOT_TYPE_CHANGE, function () {
    debounced_updateViews(true);
  });

  $scope.$on(PlotTypes.ON_PLOT_FILTER_CHANGE, function () {
    debounced_updateViews(true);
  });

  $scope.noDataMessageHtml = function () {
    return $sce.trustAsHtml(Utils.noDataMessageHtml({
        noDataMessageHeader: function() {return "No Reports"},
        noDataMessage: function() {return ""}
      }
    ));
  };

  $scope.selectedIntentions = FilterService.getSelectedIntentions();
  $scope.selectedAgents = AgentsService.getSelectedTags();
  $scope.selectedSentiments = [];

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
    sentiments: {visible: false, all: true},
    statuses: {visible: false, all: true},
    smart_tags: {visible: false, all: true},
    languages: {visible: false, all: true}
  };


  /********* LANGUAGES **********/

  $scope.languages = [];
  $scope.updateLanguages = function () {
    FilterService.updateLanguages();
  }

  $scope.toggleFacet = function (facetName) {
    var facet = $scope.facets[facetName];
    return facet.visible ? facet.visible = false : facet.visible = true;
  };

  $scope.removeLanguage = function (item) {
    FilterService.removeLanguage(item)
  };
  $scope.removeIntention = function (item) {
    FilterService.removeIntention(item);
  };

  $scope.removeSentiment = function (item) {
    FilterService.removeSentiment(item);
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

  $scope.$watch('facets.sentiments.all', function (newVal) {
    FilterService.setIsAllSentiments(newVal);
    if (newVal) {
      FilterService.setSentiments([]);
    }
  });
  $scope.$watch('facets.agents.all', function (newVal) {
    AgentsService.setIsAllSelected(newVal);
    if (newVal) {
      AgentsService.setAll(false);
    }
  });
  $scope.$watch('facets.topics.all', function (newVal) {
    if (newVal) {
      if (!$scope.scrollingCalled) {
        MyTopics.purge();
      }
      else {
        $scope.scrollingCalled = false;
      }

    }
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
    if (ChannelsService.getSelectedId() != null) {
      debounced_updateViews(true);
    }
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
    if (ChannelsService.getSelectedId() != null) {
      debounced_updateViews(true);
    }
  });

  $scope.$on(FilterService.SENTIMENTS_CHANGED, function () {
    var selected = FilterService.getSelectedSentiments();
    if (selected.length > 0) {
      FilterService.setIsAllSentiments(false);
      $scope.selectedSentiments = selected;
      $timeout(function () {
        $scope.facets.sentiments.all = false;
      }, 10)
    } else {
      $scope.selectedSentiments = [];
      $scope.facets.sentiments.all = true;
    }
    if (ChannelsService.getSelectedId() != null) {
      debounced_updateViews(true);
    }
  });


  $scope.$on(AgentsService.ON_AGENTS_CHANGED, function () {
    var selected = AgentsService.getSelectedTags();
    if (selected.length > 0) {
      AgentsService.setIsAllSelected(false);
      $scope.selectedAgents = selected;
      $scope.facets.agents.all = false;
    } else {
      $scope.selectedAgents = [];
      $scope.facets.agents.all = true;
    }
    if (ChannelsService.getSelected() != null) {
      debounced_updateViews(true);
    }
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
    if (ChannelsService.getSelectedId() != null) {
      debounced_updateViews(true);
    }
  });


  var resetActiveWidget = function () {

    if ($scope.widget &&
      $scope.widget.settings.plot_type !== $scope.submenu.action) {
      $scope.widget = null;
    }
  }

  $scope.resetAll = function (noResetSmartTag) {
    $scope.facets.intentions.all = true;
    $scope.facets.agents.all = true;
    $scope.facets.topics.all = true;
    $scope.facets.sentiments.all = true;
    $scope.facets.statuses.all = true;
    $scope.facets.smart_tags.all = true;
    $scope.data = 'Loading';
    setActiveFilter();
    resetActiveWidget();
    $scope.deactivateTopics();
    if (_.isUndefined(noResetSmartTag) || !noResetSmartTag) {
      $scope.smart_tag.selected = null;
      $scope.selected_smart_tags = [];
      $scope.facets.languages.all = true;
    }

  };

  $scope.getPlotterURL = function (reset) {
    if ($scope.tab_options.type != 'topics') {
      if (PlotTypes.getActiveType() == 'time') {
        return "/partials/plot/time_plot"
      } else {
        return "/partials/plot/share_plot"
      }
    } else {
      return "/partials/topics/cloud"
    }
  };


  /* MODERATION */

  $scope.master = {checked: false};
  $scope.selected_items = [];
  $scope.selected_items_ids = {};

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
        debounced_updateViews(false);
      })
    } else {
      toggleStatus(selection, status);
    }
  };
  $scope.rejectPost = PostFilter.command('reject', postStatusChanged);
  $scope.starPost = PostFilter.command('star', postStatusChanged);

  $scope.lru_smart_tag = null;

  $rootScope.$on(SmartTag.LRU_TAG_CHANGED, function () {
    $scope.lru_smart_tag = SmartTag.lru_tag;
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
      [$scope.smart_tag.selected_moderation.id]).then(function (res) {
      //scope.appliedTags.push(added_tag[0]);
      post.smart_tags.push($scope.smart_tag.selected_moderation);
    });
  };

  $scope.addLRUTag = function (post) {
    SmartTags.addPostTags(ChannelsService.getSelectedId(), post.id_str,
      [$scope.lru_smart_tag.id]).then(function (res) {
      //scope.appliedTags.push(added_tag[0]);
      post.smart_tags.push($scope.lru_smart_tag);
    });
  };


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
      debounced_updateViews(false);
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
      debounced_updateViews(true);
    });
  };

  $scope.actionableItems = function () {
    PostFilter.command('star', postStatusChanged)(_.pluck($scope.selected_items, 'id_str'));
  };

  $scope.rejectItems = function () {
    PostFilter.command('reject', postStatusChanged)(_.pluck($scope.selected_items, 'id_str'));
  };

  $scope.scrollToTop = function (e) {
    $scope.scrollingCalled = true;
    $location.hash('top');
    $anchorScroll();
    return false;
  }


  /* Dashboard related */

  $scope.removeWidget = WidgetService.makeRemove(lock, 'removeWidget');
  $scope.$on(WidgetService.CHANGED, function (evt, data) {
    $scope.widget = data.widget;
  });

  $scope.$watch('widget', setupWidget);

  function setupWidget(nVal) {
    if (!nVal) {
      return;
    }
    //set stored dateRange
    FilterService.setDateRange($scope.widget.extra_settings.range_type);
    $scope.currentDate = FilterService.getSelectedDateRangeName();
    //set plot type: Distribution or Time
    if ($scope.widget.settings.plot_by == 'distribution'
      && $scope.widget.extra_settings.widget_type !== 'topics') {
      $scope.getDistribution();
    } else if ($scope.widget.extra_settings.widget_type == 'topics') {
      $scope.tab_options.type = 'topics';
      $scope.options.cloud_type = $scope.widget.extra_settings.topics_params.cloud_type;
    } else {
      $scope.getTrends();
    }
    var selected_tag = $scope.widget.extra_settings.tag_id;
    $scope.$watch('smart_tags.length', function (nVal, oVal) {
      if (nVal > 0) {
        if (selected_tag) {
          var selected = _.find($scope.smart_tags, function (item) {
            return item.id === selected_tag;
          });
          $scope.smart_tag.selected = selected;
          $scope.selected_smart_tags = [$scope.smart_tag.selected];
        }
      } else {
        $scope.selected_smart_tags = [];
      }
    });

    if (nVal.settings.sentiments
      && nVal.settings.sentiments.length > 0
      && nVal.settings.sentiments.length !== $scope.sentiments_filter.length) {

      _.each($scope.sentiments_filter, function (st) {
        if (_.indexOf(nVal.settings.sentiments, st.label) != -1) {
          st.enabled = true
        }
        FilterService.updateSentiments();
      })
      $scope.toggleFacet('sentiments');
    }

    if (nVal.settings.languages && nVal.settings.languages.length > 0) {
      FilterService.setSelectedLanguages(nVal.settings.languages)
    }

    if (nVal.settings.topics.length > 0) {
      MyTopics.add(nVal.settings.topics);
      $scope.firstTimeEarlyWarnings = false;
    }
  }

}]);

Reports.controller("ChannelsCtrl", ["$scope", "ChannelsService", "AppState", "WidgetService", function ($scope, ChannelsService, AppState, WidgetService) {
  $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function (scope, bookmark) {
    setChannels(WidgetService.getCurrent());
  });

  $scope.$on(WidgetService.CHANGED, function (evt, data) {
    setChannels(data.widget);
  });

  /* watchers */
  $scope.$watch('channel', function (newVal, oldVal) {
    if (newVal !== oldVal) {
      ChannelsService.setSelected($scope.channel);
    }
  });

  function setChannels(widget) {
    $scope.channels = ChannelsService.getList();
    var stored_channel = AppState.read("reports_channel");
    var service_channel = AppState.read("service_channel");

    var valid_channel = service_channel ?
      _.find($scope.channels, function (el) {
        return el.parent_id === service_channel.parent_id
      }) :
      stored_channel ? AppState.find_by_id($scope.channels, stored_channel.id) : null;

    if (!widget) {
      $scope.channel = valid_channel ? valid_channel : ChannelsService.getSelected();
    } else {
      $scope.channel = _.find($scope.channels, function (el) {
        return el.id === $scope.widget.extra_settings.channel_id
      });
    }
  }
}]);

