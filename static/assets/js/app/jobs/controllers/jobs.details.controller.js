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

})();