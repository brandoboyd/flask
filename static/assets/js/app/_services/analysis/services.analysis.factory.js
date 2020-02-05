(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('AnalysisService', AnalysisService);

  /** @ngInject */
  function AnalysisService(AnalysisRest, $q) {
    var Analysis = new AnalysisRest();
    var F = {};
    var flags = {
      isBuilt: false,
      isEmpty: false
    };
    var reports = [];
    var deferred;

    F.getReports = function () {
      return reports;
    };

    F.fetchReports = function (sref) {
      var list = [];
      deferred = $q.defer();

      Analysis.list()
        .success(function (res) {
          if (!res.list.length) {
            flags.isEmpty = true;
          } else {
            flags.isEmpty = false;
            list = _(res.list)
              .sortBy('created_at')
              .reverse()
              .map(function (item) {
                return _.extend(item, {
                  name: item.title,
                  type: 'report',
                  sref: sref + '(' + JSON.stringify({id: item.id}) + ')'
                });
              })
              .value();
          }

          deferred.resolve(list);
          reports = list;
        });

      return deferred.promise;
    };

    F.isBuilt = function() {
      return flags.isBuilt;
    };

    F.setAsBuilt = function () {
      flags.isBuilt = true;
    };

    F.isEmpty = function () {
      return flags.isEmpty;
    };

    F.unshiftReport = function (report) {
      reports.unshift(report);
    };

    return F;
  }
})();