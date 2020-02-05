(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('DatasetsRest', DatasetsRest);

  /** @ngInject */
  function DatasetsRest($q, ModelRest) {
    var Datasets = function () {};
    var BASE_URL = '/dataset';

    Datasets.prototype = new ModelRest(BASE_URL);

    Datasets.prototype.list = function() {
      this.setUrl([BASE_URL, 'list'].join('/'));
      return this.get();
    };

    Datasets.prototype.getOne = function(name) {
      this.setUrl([BASE_URL, 'get', name].join('/'));
      return this.get();
    };

    Datasets.prototype.save = function(params) {
      if (params.type === 'append') {
        this.setUrl([BASE_URL, 'update', params.name].join('/'));
      } else {
        this.setUrl([BASE_URL, 'create'].join('/'));
      }

      var formData = new FormData();
      if (params['csv_file']) {
        formData.append('csv_file', params['csv_file']);
      }
      if (params.type === 'create') {
        formData.append('name', params['name']);
      }
      if (params['sep']) {
        formData.append('sep', params['sep']);
      }


      return this.request({
        method: 'POST',
        data: formData,
        transformRequest: angular.identity,
        headers: { 'Content-Type': undefined }
      });
    };

    Datasets.prototype.updateSchema = function (name, params) {
      this.setUrl([BASE_URL, 'update_schema', name].join('/'));
      return this.post(params);
    };

    Datasets.prototype.applySchema = function (name) {
      this.setUrl([BASE_URL, 'sync/apply', name].join('/'));
      return this.post();
    };

    Datasets.prototype.acceptSchema = function (name) {
      this.setUrl([BASE_URL, 'sync/accept', name].join('/'));
      return this.post();
    };

    Datasets.prototype.cancelSchema = function (name) {
      this.setUrl([BASE_URL, 'sync/cancel', name].join('/'));
      return this.post();
    };

    Datasets.prototype.delete = function(name) {
      this.setUrl([BASE_URL, 'delete', name].join('/'));
      return this.post();
    };

    Datasets.prototype.fetchFieldData = function(name, fieldName, params) {
      this.setUrl([BASE_URL, 'view', name, fieldName].join('/'));
      return this.get(params);
    };

    Datasets.prototype.getDistributionData = function(name) {
      this.setUrl([BASE_URL, 'get', name].join('/'));

      var deferred = $q.defer();

      this.get().success(function(res) {
        var dist = res.data.data_distribution;
        var from_dt, to_dt;
        var length = dist.length;

        // FIX ME: server response is not sorted by datetime yet
        dist = _.sortBy(dist, function(item) { return item[0] });
        if (length > 0) {
          from_dt = dist[0][0];
          to_dt = dist[length - 1][0];
        }
        deferred.resolve({
          distribution: [{
            key: 'sample',
            bar: true,
            values: dist,
          }],
          from_dt: from_dt,
          to_dt: to_dt,
        });
      }).catch(function(err) {
        deferred.reject(err);
      });

      return deferred.promise;
    }

    return Datasets;
  }
})();
