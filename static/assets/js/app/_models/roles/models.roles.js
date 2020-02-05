(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('UserRolesRest', UserRolesRest);

  /** @ngInject */
  function UserRolesRest(ModelRest) {
    var BASE_URL = '/user_roles';
    var UserRoles = function () {
      this.listUrl = [BASE_URL, 'json'].join('/')
    };

    UserRoles.prototype = new ModelRest(BASE_URL);

    UserRoles.prototype.list = function(params) {
      this.setUrl(this.listUrl);
      return this.get(params);
    };
    return UserRoles;
  }
})();