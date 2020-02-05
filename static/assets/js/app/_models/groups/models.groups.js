(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('GroupsRest', GroupsRest);

  /** @ngInject */
  function GroupsRest(ModelRest) {
    var Groups = function () {};
    var BASE_URL = '/groups';

    Groups.prototype = new ModelRest(BASE_URL);

    Groups.prototype.list = function() {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.get();
    };

    Groups.prototype.getOne = function(id) {
      var url = [BASE_URL, 'json'].join('/');
      this.setUrl(url + '?id=' + id);
      return this.get();
    };

    Groups.prototype.save = function(params) {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.post(params);
    };

    Groups.prototype.remove = function(id) {
      var url = [BASE_URL, 'json'].join('/');
      this.setUrl(url + '?id=' + id);
      return this.delete();
    };

    Groups.prototype.action = function(action, params) {
      this.setUrl([BASE_URL, action, 'json'].join('/'));
      return this.post(params);
    };

    return Groups;
  }
})();