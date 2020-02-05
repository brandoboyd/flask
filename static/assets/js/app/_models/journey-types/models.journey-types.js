(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('JourneyTypesRest', JourneyTypesRest);

  /** @ngInject */
  function JourneyTypesRest(ModelRest) {
    var JourneyTypes = function () {
    };
    var BASE_URL = '/journey_types';

    JourneyTypes.prototype = new ModelRest(BASE_URL);

    JourneyTypes.prototype.list = function () {
      this.setUrl(BASE_URL);
      return this.get();
    };

    JourneyTypes.prototype.getOne = function (id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    JourneyTypes.prototype.save = function (params) {
      if (params.id) {
        this.setUrl([BASE_URL, params.id].join('/'));
        return this.put(params);
      } else {
        this.setUrl(BASE_URL);
        return this.post(params);
      }
    };

    JourneyTypes.prototype.remove = function (id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    // STAGES
    JourneyTypes.prototype.getStages = function (id) {
      this.setUrl([BASE_URL, id, 'stages'].join('/'));
      return this.get();
    };

    JourneyTypes.prototype.getOneStage = function (id, stageId) {
      this.setUrl([BASE_URL, id, 'stages', stageId].join('/'));
      return this.get();
    };

    JourneyTypes.prototype.saveStage = function (params) {
      var url = [BASE_URL, params.id, 'stages'].join('/');

      if (_.has(params, 'stageId')) {
        url += '/' + params.stageId;
      }

      this.setUrl(url);
      return this.post(params.data);
    };
    JourneyTypes.prototype.removeStage = function (id, stageId) {
      this.setUrl([BASE_URL, id, 'stages', stageId].join('/'));
      return this.delete();
    };

    return JourneyTypes;
  }
})();