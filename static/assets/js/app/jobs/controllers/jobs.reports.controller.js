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

})();