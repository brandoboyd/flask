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
})();