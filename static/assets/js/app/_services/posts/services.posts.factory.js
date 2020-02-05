(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory("Posts", Posts)
    .factory('PostsExport', PostsExport)
    .factory('PostFilter', PostFilter);

  /** @ngInject */
  function Posts($rootScope, $resource, ChannelsService, FilterService) {
    var Posts = $resource('/posts/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
    var posts = [];
    //var dateRange = FilterService.getDateRange();
    var search_tabs = [];
    var search_tab = {};
    var is_search = false;
    Posts.level = 'day';

    Posts.ON_DOT_POSTS_FETCHED = 'on_dot_posts_fetched';
    Posts.ON_TAB_POSTS_FETCHED = 'on_tab_posts_fetched';
    Posts.ON_POSTS_FAILED = 'on_posts_failed';
    Posts.ON_POSTS_FETCHED = 'on_posts_fetched';
    Posts.ON_POSTS_BEING_FETCHED = 'on_posts_being_fetched';
    Posts.ON_SEARCH_TAB_SELECTED = 'on_search_tab_selected';
    Posts.ON_SEARCH_PARAMS_UPDATED = 'on_search_params_updated';

    Posts.setLevel = function (level) {
      Posts.level = level;
    }
    Posts.getSearchState = function () {
      return is_search;
    };
    Posts.setSearchState = function (search) {
      is_search = search;
      $rootScope.$broadcast(Posts.ON_SEARCH_TAB_SELECTED);
    };
    Posts.getPosts = function () {
      return posts;
    };

    Posts.updateSearchTabs = function (newTabs) {
      search_tabs = newTabs;
    };
    Posts.getSearchTabs = function () {
      return search_tabs;
    };
    Posts.setCurrentTab = function (tab) {
      search_tab = tab;
      Posts.initExpandedSearchParams(tab);
      // $rootScope.$broadcast(Posts.ON_SEARCH_TAB_SELECTED);
    };
    Posts.getCurrentTab = function () {
      return search_tab;
    };

    Posts.initExpandedSearchParams = function (tab) {

      if (!tab.expandedSearchParams) {
        tab.expandedSearchParams = jQuery.extend(true, {}, tab.params);

        if (tab.expandedSearchParams.from == null) {

          var date = new Date(tab.expandedSearchParams.timestamp);
          var UTCdate = FilterService.getUTCDate(date);

          tab.expandedSearchParams.dateRange = {
            from: UTCdate.toString("MM/dd/yyyy"),
            to: UTCdate.add(1).days().toString("MM/dd/yyyy")
          }

        } else {

          tab.expandedSearchParams.dateRange = {
            from: tab.expandedSearchParams.from,
            to: tab.expandedSearchParams.to
          }

        }
      }

    };
    Posts.getExpandedSearchParams = function () {
      return search_tab.expandedSearchParams;
    };
    Posts.updateThresholds = function (thresholds) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.thresholds = thresholds;
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };
    Posts.updateSortBy = function (what) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.sort_by = what;
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };
    Posts.updateTerms = function (terms, init) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.terms = terms;
      if (!init) {
        $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
      }
    };
    Posts.updateIntentions = function (intentions) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.intentions = intentions;
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };
    Posts.updateDateRange = function (dateRange) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.dateRange = {
        "from": (dateRange.from).toString("MM/dd/yyyy"),
        "to": (dateRange.to).toString("MM/dd/yyyy")
      };
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };

    Posts.filterChanged = function (filterName, value, refresh) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams[filterName] = value;
      if (refresh)
        $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };

    Posts.has_more_posts = true;
    Posts.offset = 0;
    Posts.limit = 15;
    Posts.last_query_time = null;
    Posts.resetPaging = function () {
      Posts.offset = 0;
      Posts.limit = 15;
      Posts.last_query_time = null;
      Posts.has_more_posts = true;
      posts = [];
    };
    Posts.searchForPosts = function (params) {
      params.offset = Posts.offset;
      params.limit = Posts.limit;
      params.last_query_time = Posts.last_query_time;
      if (ChannelsService.getSelectedId() != null) {
        if (Posts.has_more_posts) {
          $rootScope.$broadcast(Posts.ON_POSTS_BEING_FETCHED);
          Posts.fetch({}, params, function (res) {
            var items = res.list;
            _.each(items, function (item) {
              posts.push(item);
            });
            Posts.has_more_posts = res.are_more_posts_available;
            Posts.offset = posts.length;
            Posts.last_query_time = res.last_query_time;
            $rootScope.$broadcast(Posts.ON_POSTS_FETCHED);
          }, function onError(res) {
            $rootScope.$broadcast(Posts.ON_POSTS_FAILED);
          });
        } else {
          console.log("HAS NO MORE POSTS");
          $rootScope.$broadcast(Posts.ON_NO_MORE_POSTS);
        }
      } else {
        posts = [];
        $rootScope.$broadcast(Posts.ON_POSTS_FETCHED);
      }
    };
    Posts.searchByGraph = function (item, params) {
      $rootScope.$apply(function () {
        Posts.setSearchState(true);
      });

      if (item) {
        Posts.searchForPosts(params);
      }

    };
    Posts.searchByTab = function (params) {
      Posts.setSearchState(true);
      Posts.searchForPosts(params);
    };

    $rootScope.$on("selectChanged", function ($scope, flag, id) {
      Posts.filterChanged(id, $scope.targetScope.params[id], (flag !== 'init'));
    });
    $rootScope.$on("thresholdsChanged", function ($scope) {
      Posts.updateThresholds($scope.targetScope.params.threshold);
    });

    return Posts;

  }

  /** @ngInject */
  function PostsExport($modal, $resource, AgentsService, ChannelsService, FilterService, SystemAlert) {
    var resource = $resource('/export/posts/json'),
      PostsExport = {
        "submit": dispatch('export'),
        "check": dispatch('check'),
        "exportPosts": exportPosts
      };

    function dispatch(action) {
      return function (params) {
        var postData = angular.copy(params);
        delete postData['smartTag'];
        postData.action = action;
        postData.all_selected = FilterService.facetsAllSelected();
        postData.limit = 1000;
        return resource.save(postData).$promise;
      };
    }

    function translate(facet, values) {
      var facets = {
        'intentions': {'junk': 'other'},
        'statuses': {'actual': 'replied'}
      };

      return _.map(values, function (val) {
        var facetMap = facets[facet];
        if (facetMap && facetMap[val]) {
          return facetMap[val];
        }
        return val;
      });
    }

    function exportPosts(params) {
      var SUCCESS = 7;  // constant from db/data_export.py

      function checkRunningTask() {
        return PostsExport.check(params).then(function (resp) {
          return resp.task && resp.task.state < SUCCESS;
        }, function onError() {
          return false;
        });
      }

      function submitExport() {
        return PostsExport.submit(params);
      }

      function makePopupViewModel(params) {
        var selectedChannel = ChannelsService.getSelected(),
          smartTag = params.smartTag,
          all = FilterService.isAllSelected,
          joined = function (lst) {
            if (Array.isArray(lst)) {
              return lst.join(', ');
            }
            return '';
          },
          reportName = function (pt) {
            if (!pt) {
              return '';
            }
            return {
              'top-topics': 'Trending Topics',
              'missed-posts': 'Missed Posts',
              'inbound-volume': 'Inbound Volume',
              'first-contact-resolution': 'First Contact Resolution',
              'work-done': 'Work Done',
              'response-time': 'Response Time',
              'response-volume': 'Response Volume',
              'sentiment': 'Sentiment'
            }[pt];
          },
          agentLabel = function (agentId) {
            return AgentsService.getLabel(agentId);
          },
          datePart = function (dateStr) {
            return dateStr.split(' ')[0];
          },
          dateRange = function (from, to) {
            from = datePart(from);
            to = datePart(to);
            if (from == to) {
              return from;
            }
            return from + " — " + to;
          };

        return {
          channel: selectedChannel,
          report_name: reportName(params.plot_type),
          date_range: dateRange(params.from, params.to),
          smart_tags: smartTag && smartTag.title,
          intentions: all('intentions') ? null :
            joined(translate('intentions', params.intentions)),
          sentiments: all('sentiments') ? null :
            joined(params.sentiments),
          status: all('statuses') ? null :
            joined(translate('statuses', params.statuses)),
          topics: joined(_.map(params.topics, function (item) {
            return item.topic;
          })),
          languages: all('languages') ? null :
            joined(params.languages),
          agents: joined(_.map(params.agents, agentLabel))
        };
      }

      function showConfirmPopup() {
        var d = $modal.open({
          backdrop: true,
          keyboard: true,
          templateUrl: '/partials/export/posts',
          controller: function ($scope) {
            var data = makePopupViewModel(params);
            $scope.data = data;
            $scope.table = _([
              ['Report Name', data.report_name],
              ['Date Range', data.date_range],
              ['Smart Tags', data.smart_tags],
              ['Intentions', data.intentions],
              ['Sentiments', data.sentiments],
              ['Posts Status', data.status],
              ['Topics, Keywords', data.topics],
              ['Languages', data.languages],
              ['Agents', data.agents]
            ]).filter(function (row) {
              return row[1];
            }).map(function (item) {
              return {title: item[0], value: item[1]};
            }).value();
            $scope.close = $scope.$close;
          }
        });
        return d.result;
      }

      checkRunningTask().then(function (taskIsRunning) {
//           if (taskIsRunning) { return; }
        showConfirmPopup().then(function (dialogResult) {
          if (dialogResult === true) {
            return submitExport().then(function (resp) {
              SystemAlert.success(resp.message, 5000);
            });
          }
        });
      });
    }

    return PostsExport;
  }

  /** @ngInject */
  function PostFilter($resource, ChannelsService) {
    var PostFilter = $resource('/commands/:action', {}, {
      reject: {method: 'POST', params: {action: "reject_post"}},
      star: {method: 'POST', params: {action: "star_post"}}
    });

    PostFilter.command = function (command, callback) {
      var actor = {
        star: {command: PostFilter.star, status: 'actionable'},
        reject: {command: PostFilter.reject, status: 'rejected'}
      }[command];
      return function (post_or_ids) {
        var params = {
          "posts": _.isArray(post_or_ids) ? post_or_ids : [post_or_ids.id_str],
          "channels": [ChannelsService.getSelectedId()]
        };
        actor.command(params, function () {
          callback(post_or_ids, actor.status);
        });
      };
    };

    return PostFilter;
  }
})();