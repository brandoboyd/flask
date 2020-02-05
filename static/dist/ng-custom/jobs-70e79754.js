(function() {
  'use strict';

  angular.module('jobs', [
    'ui.router',
    
    'slr.services',
    'slr.utils',
    'slr.components',
    'slr.models',
  ])

  .value('uiJqConfig', {
    tooltip: {
        animation: false,
        placement: 'bottom',
        container: 'body'
    }
  });

})();
(function() {
  'use strict';

  angular.module('jobs')
    .config(jobsAppConfig);

  function jobsAppConfig($stateProvider, $urlRouterProvider) {
    $urlRouterProvider.when('', 'reports');
    $urlRouterProvider.when('/', 'reports');
    $urlRouterProvider.otherwise('reports');

    $stateProvider
      .state('jobs', {
        abstract    : true,
        url         : '/',
        template    : '<ui-view/>',
      })

      .state('jobs.reports', {
        url         : 'reports?wid',
        templateUrl : '/jobs/partials/reports.tab',
        controller  : 'JobReportsCtrl',
        controllerAs: 'vm',
      })

      .state('jobs.details', {
        url         : 'details',
        templateUrl : '/jobs/partials/details.tab',
        controller  : 'JobDetailsCtrl',
        controllerAs: 'vm',
      })
  }
  jobsAppConfig.$inject = ["$stateProvider", "$urlRouterProvider"];
})();
(function() {
  'use strict';

  angular
    .module('jobs')
    .controller('JobDetailsCtrl', JobDetailsCtrl);

  function Pagination (limit, requestFn) {
    this.limit = limit;
    this.offset = 0;
    this.hasMore = true;
    this.requestFn = requestFn;
  }
  Pagination.prototype = {
    reset : function() {
      this.offset = 0;
      this.hasMore = true;
    },
    request: function (params) {
      params.limit = this.limit;
      params.offset = this.offset;
      var paging = this;
      return this.requestFn(params).then(function(response) {
        if (response.list && response.list.length == 0) {
          paging.hasMore = false;
        } else {
          paging.hasMore = response.more_results_available;
          paging.offset = paging.offset + response.list.length;
        }
        return response;
      });
    }
  };

  /* @ngInject */
  function JobDetailsCtrl($scope, $state, JobsFactory, SystemAlert) {
    var vm = this;

    var paginator = new Pagination(30, JobsFactory.getJobs);
    var debouncedFetchJobs = _.debounce(fetchJobs, 500);
    var isDrillDown = false;
    var searchParams = {};
    var searchFieldsToOmit = ['level', 'plot_by', 'plot_type'];

    vm.jobs     = [];
    vm.filters  = { name : '' };
    vm.tableSorter   = {
      predicate : 'status',
      reverse   : false,
    };
    vm.loading    = false;
    vm.resumeJob  = resumeJob;
    vm.abandonJob = abandonJob;
    vm.loadMore   = debouncedFetchJobs;


    $scope.$on(JobsFactory.SEARCH_PARAM_CHANGE, onSearchParamChange);

    activateController();

    function activateController() {
    }

    function fetchJobs() {
      console.log('[Job Details] fetchJobs from ', paginator.offset);
      if (paginator.hasMore === false) {
        return
      }
      vm.loading = true;

      paginator.request(searchParams )
        .then(function(data) {
          if (data.list.length === 0) {
            paginator.hasMore = false;
          } else {
            vm.jobs = _.map(vm.jobs.concat(data.list), function(job) {
              return _.extend(job, {
                canBeResumed: job.status == 'Failed',
                enabled: ['Pending', 'Failed'].indexOf(job.status) >= 0
              });
            });
            paginator.hasMore = data.more_data_available;
            paginator.offset = vm.jobs.length;
          }
        })
        .catch(function(err) {
          paginator.hasMore = false;
        })
        .finally(function() {
          vm.loading = false;
        });
    }
    
    function abandonJob(job) {
      if (job.status !== 'Pending') {
        SystemAlert.warn('You can drop only \'Pending\' Jobs from queue');
        return;
      }

      var jobToUpdate = _.find(vm.jobs, { id: job.id });
      JobsFactory.abandonJob(job.id)
        .then(function(resp) {
          if (resp.list && resp.list.length > 0) {
            angular.copy(resp.list[0], jobToUpdate); // Update the job in the table
          }
        });
    }

    function resumeJob(job) {
      if (job.status !== 'Failed') {
        SystemAlert.warn('You can resume only \'Failed\' Jobs');
        return;
      }

      var jobToUpdate = _.find(vm.jobs, { id: job.id });
      JobsFactory.resumeJob(job.id)
        .then(function(resp) {
          if (resp.list && resp.list.length > 0) {
            angular.copy(resp.list[0], jobToUpdate); // Update the job in the table
          }
        });
    }

    function onSearchParamChange(evt, data) {
      console.log('[Job Details] new search params ', data.params);
      searchParams = _.omit(data.params, searchFieldsToOmit);

      if (isDrillDown) {
        // If drilled down from reports page, 
        isDrillDown = false;
      } else {
        paginator.reset();
        vm.jobs = [];
        debouncedFetchJobs();
      }
    }
  }
  JobDetailsCtrl.$inject = ["$scope", "$state", "JobsFactory", "SystemAlert"];

})();
(function() {
  'use strict';

  angular
    .module('jobs')
    .controller('JobMainCtrl', JobMainCtrl);

  /* @ngInject */
  function JobMainCtrl($scope, $q, $timeout, JobsFactory, FilterService, WidgetService, AccountsService) {

    var vm = this;
    vm.widget     = {};
    vm.facets     = {};
    vm.menuTabs   = JobsFactory.getMenuTabs();
    vm.currentTab = '';
    vm.onFacetsChange = onFacetsChange;
    
    var reportOptionId = null;
    var debouncedTrigger = _.debounce(triggerRender, 100, {leading: false, trailing: true});

    $scope.$on(FilterService.DATE_RANGE_CHANGED, debouncedTrigger);
    $scope.$on(JobsFactory.EMIT_REPORT_OPTION, onReportOptionChange);
    $scope.$on('$stateChangeSuccess', onStateChangeSuccess);

    activateController();

    function activateController() {
      loadDefaultDateRange();

      $q.when()
        .then(function() {
          return loadDefaultFacets();
        })
        .then(function() {
          return loadWidgetIfAny();
        });
    }

    function loadWidgetIfAny() {
      vm.widget = {
        removing  : false,
        updating  : false,
        item      : null,
        getParams : function() {
          return {
            settings: getSearchParams(),
            extra_settings: {
              request_url   : '/jobs/reports',
              source        : '/jobs#/reports?wid=',
              target        : 'JOBS',
              directive     : 'chart',
              chart_type    : 'LINE',
              level         : 'day',
              yAxisFormat   : JobsFactory.getYAxisFormat(reportOptionId),
              yAxisLabel    : JobsFactory.getYAxisLabel(reportOptionId),
              account_info  : AccountsService.getCompactAccount()
            }
          }
        },
        setup: function (w) {
          if (vm.widget.updating) {
            vm.widget.updating = false;
          }

          if (!w || _.isEmpty(w)) {
            return;
          }

          loadWidgetSettings();
        },
        remove: WidgetService.makeRemove(vm.widget, 'removing')
      };

      $scope.$watch('vm.widget.item', vm.widget.setup);
      $scope.$watch('location.search()', locationChanged);
      $scope.$on(WidgetService.CHANGED, function (evt, data) {
        var w = vm.widget;
        w.updating = true;
        w.item = data.widget;
      });
    }

    function locationChanged() {
      var w = vm.widget;
      if (w.removing) {
        return;
      }
      WidgetService.loadFromLocation();
    }

    function loadWidgetSettings() {
      var settings = vm.widget.item.settings;
      // Load date range
      if (settings.from && settings.to) {
        FilterService.updateDateRange({
          from: moment.utc(settings.from),
          to  : moment.utc(settings.to)
        });
      }

      vm.dateRange.from = settings.from;
      vm.dateRange.to = settings.to;
      vm.dateRangeName = FilterService.getSelectedDateRangeName();

      // Load facets
      _.each(vm.facets, function(group, key) {
        _.each(group.list, function(item) {
          item.enabled = settings[key] && (settings[key].indexOf(item.id) > -1);
        });
      });

      // Load Report Option
      reportOptionId = settings['plot_by'];

      $scope.$broadcast(JobsFactory.BROADCAST_REPORT_OPTION, reportOptionId);

      debouncedTrigger();
    }

    function loadDefaultDateRange() {
      vm.dateRange = FilterService.getDateRange({local: true});
      vm.dateRangeName = FilterService.getSelectedDateRangeName();
    }

    function loadDefaultFacets() {
      return JobsFactory.getFacets().then(function(facets) {
        vm.facets = facets;
      });
    }

    function getSearchParams() {
      vm.dateRange = FilterService.getDateRange({local: true});
      var params = {
        from        : vm.dateRange.from,
        to          : vm.dateRange.to,
        level       : 'day',
        plot_by     : reportOptionId,
        plot_type   : vm.currentTab === 'reports'? 'time': null,
      };
      return angular.extend(params, getFacetParams());
    }

    function getFacetParams() {
      return _.mapValues(vm.facets, function(group, key) {
        return _(group.list)
          .filter(function(item) { return item.enabled })
          .pluck('id')
          .value()
      });
    }

    function onFacetsChange() {
      // More stuff for facets interaction
      if (Object.keys(vm.facets).length > 0) {
        debouncedTrigger();
      }
    }

    function onReportOptionChange(evt, optionId) {
      if (reportOptionId !== optionId) {
        reportOptionId = optionId;
        debouncedTrigger();
      }
    }

    function triggerRender() {
      $scope.$broadcast(JobsFactory.SEARCH_PARAM_CHANGE, { params: getSearchParams() });
    }

    function onStateChangeSuccess(evt, toState, toParams, fromState, fromParams) {
      vm.currentTab = '';
      if (toState.name === 'jobs.reports') {
        vm.currentTab = 'reports';
      } else if (toState.name === 'jobs.details' && vm.widget) {
        vm.currentTab = 'details';
        vm.widget.remove() // Reset widget which is only for reports page
      }
      debouncedTrigger();
    }
  }
  JobMainCtrl.$inject = ["$scope", "$q", "$timeout", "JobsFactory", "FilterService", "WidgetService", "AccountsService"];
})();
(function() {
  'use strict';

  angular
    .module('jobs')
    .controller('JobReportsCtrl', JobReportsCtrl);

  /* @ngInject */
  function JobReportsCtrl($scope, $timeout, JobsFactory, SystemAlert) {
    var vm = this;
    vm.reportOptions = [ ];
    vm.currentReportOption = {};
    vm.onReportOptionChange = onReportOptionChange;
    vm.chart = {
      data: [],
      settings: {
        chart_type: 'LINE',
        target: 'JOBS',
        level: 'day',
        yAxisFormat: ',.0d',
      }
    };

    var searchParams = {};
    var debouncedDraw = _.debounce(drawReports, 500);

    $scope.$on(JobsFactory.SEARCH_PARAM_CHANGE, onSearchParamChange);
    $scope.$on(JobsFactory.BROADCAST_REPORT_OPTION, onReportOptionReset);

    activateController();

    function activateController() {
      JobsFactory.getReportOptions().then(function (options) {
        if (options.length > 0) {
          vm.reportOptions = options;

          if (!vm.currentReportOption.id) {
            vm.currentReportOption.id = options[0].id;
          }

          onReportOptionChange();
        }
      });
    }

    function drawReports() {
      SystemAlert.showLoadingMessage();
      console.log('[Job Reports] draw graphs with params ', searchParams);
      JobsFactory.getReports(searchParams)
        .then(function (data) {
          vm.chart.data = data;
          vm.chart.settings.yAxisFormat = JobsFactory.getYAxisFormat(vm.currentReportOption.id);
          vm.chart.settings.yAxisLabel = JobsFactory.getYAxisLabel(vm.currentReportOption.id);
        })
        .finally(function() {
          $timeout(SystemAlert.hideLoadingMessage, 300);
        });
    }

    function onSearchParamChange(evt, data) {
      console.log('[Job Reports] new search params ', data.params);
      searchParams = data.params;
      debouncedDraw();
    }

    function onReportOptionChange() {
      var option = _.find(vm.reportOptions, { id: vm.currentReportOption.id });
      if (option) {
        angular.copy(option, vm.currentReportOption);
        $scope.$emit(JobsFactory.EMIT_REPORT_OPTION, vm.currentReportOption.id);
      }
    }

    function onReportOptionReset(evt, optionId) {
      vm.currentReportOption.id = optionId;
    }
  }
  JobReportsCtrl.$inject = ["$scope", "$timeout", "JobsFactory", "SystemAlert"];

})();
(function() {
  'use strict';

  angular
    .module('jobs')
    .factory('JobsFactory', JobsFactory);

  /** @ngInject */
  function JobsFactory($q, $http) {
    var yAxisFormats = {
      count: ',.0d',
      time: ',.2f'
    };
    var yAxisLabels = {
      count: 'Jobs',
      time: 'Duration (sec.)'
    };

    var factory = {
      SEARCH_PARAM_CHANGE     : 'JOBS_SEARCH_PARAM_CHANGED',
      BROADCAST_REPORT_OPTION : 'JOBS_BROADCAST_REPORT_OPTION',
      EMIT_REPORT_OPTION      : 'JOBS_EMIT_REPORT_OPTION',

      getMenuTabs     : getMenuTabs,

      getFacets       : getFacets,
      getReportOptions: getReportOptions,
      getJobs         : getJobs,
      getReports      : getReports,
      resumeJob       : resumeJob,
      abandonJob      : abandonJob,
      // resumeJobs      : resumeJobs,
      // abandonJobs     : abandonJobs,

      getYAxisFormat  : getYAxisFormat,
      getYAxisLabel   : getYAxisLabel,
    };

    return factory;
    //////////////////////////////////////////

    function getFacets () {
      return $http.get('/jobs/facets')
        .then(function(resp){
          return resp.data.list;
        })
    }

    function getReportOptions () {
      return $http.get('/jobs/reports/options')
        .then(function(resp){
          return resp.data.list;
        })
    }

    function getJobs(params) {
      return $http.post('/jobs/list', params)
        .then(function(resp) {
          return resp.data;
        });
    }

    function resumeJob(id) {
      return $http.post('/jobs/resume/' + id)
        .then(function(resp) {
          return resp.data;
        })
    }

    function abandonJob(id) {
      return $http.post('/jobs/abandon/' + id)
        .then(function(resp) {
          return resp.data;
        })
    }

    function getReports (params) {
      return $http.post('/jobs/reports', params)
        .then(function(resp) {
          return resp.data.list;
        });
    }

    function getMenuTabs() {
      return [{
        name  : 'Reports',
        sref  : 'jobs.reports',
        class : 'icon-bar-graph-variable-2'
      }, {
        name  : 'Details',
        sref  : 'jobs.details',
        class : 'icon-chat-oval-multi'
      }];
    }

    // function resumeJobs(ids) {
    //   return _.reduce(ids, function(promise, id) {
    //     return promise.then(function() {
    //       return $http.post('/jobs/resume/' + id);
    //     });
    //   }, $q.when());
    // }

    // function abandonJobs(ids) {
    //   return _.reduce(ids, function(promise, id) {
    //     return promise.then(function() {
    //       return $http.post('/jobs/abandon/' + id);
    //     });
    //   }, $q.when());
    // }

    function getYAxisFormat (reportOption) {
      return yAxisFormats[reportOption] || ',.2f';
    }

    function getYAxisLabel (reportOption) {
      return yAxisLabels[reportOption] || '';
    }
  }
  JobsFactory.$inject = ["$q", "$http"];
})();