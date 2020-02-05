(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('Trial', Trial);

  /** @ngInject */
  function Trial($resource) {
    return {
      create: function (params) {
        var defaults = {
          account_name: "",
          first_name: "",
          last_name: "",
          // full_name: "",
          email: "",
          start_date: new Date().format('mm/dd/yyyy'),
          end_date: ""
        };
        var res = new this.resource(params || defaults);
        return res;
      },

      resource: $resource('/trials/:id/json', {id: '@id'})
    };
  }
})();