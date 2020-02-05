(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('SchemaProfilesRest', SchemaProfilesRest);

  /** @ngInject */
  function SchemaProfilesRest($q, ModelRest) {
    var SchemaProfiles = function () {};

    SchemaProfiles.prototype = new ModelRest();

    SchemaProfiles.prototype.setType = function(type) {
      if (type === 'agent' || type === 'customer') {
        this.baseURL = '/' + type + '_profile';
        this.readyToUse = true;
      } else {
        this.readyToUse = false;
      }
    }

    SchemaProfiles.prototype.save = function(params) {
      if (params.type === 'create') {
        this.setUrl([this.baseURL, 'create'].join('/'));
      } else {
        this.setUrl([this.baseURL, 'update'].join('/'));
      }

      var formData = new FormData();
      if (params['csv_file']) {
        formData.append('csv_file', params['csv_file']);
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

    SchemaProfiles.prototype.getOne = function() {
      var deferred = $q.defer();

      this.setUrl([this.baseURL, 'get'].join('/'));

      this.get()
        .then(function(resp) {
          // check for empty profile
          if (Object.keys(resp.data.data).length === 0) {
            deferred.resolve({ data: null });
          } else {
            deferred.resolve(resp.data);
          }
        })
        .catch(function(err) {
          deferred.reject(err);
        });

      return deferred.promise;
    };

    SchemaProfiles.prototype.fetchFieldData = function(fieldName, params) {
      this.setUrl([this.baseURL, 'view', fieldName].join('/'));
      return this.get(params);
    };

    SchemaProfiles.prototype.delete = function() {
      this.setUrl([this.baseURL, 'delete'].join('/'));
      return this.post();
    };

    SchemaProfiles.prototype.updateSchema = function(params) {
      this.setUrl([this.baseURL, 'update_schema'].join('/'));
      return this.post(params);
    };

    SchemaProfiles.prototype.applySchema = function() {
      this.setUrl([this.baseURL, 'sync/apply'].join('/'));
      return this.post();
    };

    SchemaProfiles.prototype.acceptSchema = function() {
      this.setUrl([this.baseURL, 'sync/accept'].join('/'));
      return this.post();
    };

    SchemaProfiles.prototype.cancelSchema = function() {
      this.setUrl([this.baseURL, 'sync/cancel'].join('/'));
      return this.post();
    };

    return SchemaProfiles;
  }
})();
