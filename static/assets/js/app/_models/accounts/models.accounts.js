(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('AccountsRest', AccountsRest);

  /** @ngInject */
  function AccountsRest(ModelRest) {
    var BASE_URL = '/accounts';
    var Accounts = function () {
      this.listUrl = [BASE_URL, 'json'].join('/');
    };

    Accounts.prototype = new ModelRest(BASE_URL);

    Accounts.prototype.list = function() {
      this.setUrl(this.listUrl);
      return this.get();
    };

    Accounts.prototype.getOne = function(id) {
      if (_.isUndefined(id)) {
        id = 'no_account';
      }
      this.setUrl([BASE_URL, id, 'json'].join('/'));
      return this.get();
    };

    Accounts.prototype.update = function(id, data) {
      this.setUrl([BASE_URL, id, 'json'].join('/'));
      return this.put(data);
    };

    Accounts.prototype.getSalesforce = function(id) {
      this.setUrl([BASE_URL, 'salesforce', id].join('/'));
      return this.get();
    };

    Accounts.prototype.revokeSalesforce = function(id) {
      this.setUrl([BASE_URL, 'salesforcerevoke', id].join('/'));
      return this.post();
    };

    Accounts.prototype.loginSalesforce = function() {
      this.setUrl([BASE_URL, 'salesforcelogin'].join('/'));
      return this.post();
    };

    return Accounts;
  }
})();