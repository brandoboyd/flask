(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('ModelRest', ModelRest);

  /** @ngInject */
  function ModelRest($http) {
    var ModelRest = function (url) {
      this.url = url; // todo: need to attend prefix like /tap-api
    };

    ModelRest.prototype = Object.create(ModelRest.prototype);

    ModelRest.prototype.request = function (params) {
      var options = {
        url: this.url,
        headers: {
          'Content-Type': 'application/json'
        }
      };

      if (params && !_.isEmpty(params)) {
        _.extend(options, params);
      }

      return $http(options);  // handle success, error in controllers
    };

    ModelRest.prototype.post = function (params) {
      return this.request({method: 'POST', data: params});
    };

    ModelRest.prototype.get = function (params) {
      return this.request({method: 'GET', params: params});
    };

    ModelRest.prototype.put = function (params) {
      return this.request({method: 'PUT', data: params});
    };

    ModelRest.prototype.delete = function () {
      return this.request({method: 'DELETE'});
    };

    ModelRest.prototype.setUrl = function (url) {
      this.url = url;
    };

    return ModelRest;
  }
})();
