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
})();