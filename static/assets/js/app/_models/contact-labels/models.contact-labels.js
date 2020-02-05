(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('ContactLabelsRest', ContactLabelsRest);

  /** @ngInject */
  function ContactLabelsRest(ModelRest) {
    var ContactLabels = function () {};
    var BASE_URL = '/contact_labels';

    ContactLabels.prototype = new ModelRest(BASE_URL);

    ContactLabels.prototype.list = function() {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.get();
    };

    return ContactLabels;
  }
})();