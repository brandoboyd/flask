(function() {
  'use strict';

  angular
    .module('slr.models', [
      'ngResource'
    ]);
})();
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
  ModelRest.$inject = ["$http"];
})();

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
  AccountsRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('AnalysisRest', AnalysisRest);

  /** @ngInject */
  function AnalysisRest(ModelRest) {
    var Analysis = function () {};
    var BASE_URL = '/analyzers';

    Analysis.prototype = new ModelRest(BASE_URL);

    Analysis.prototype.list = function() {
      this.setUrl(BASE_URL);
      return this.get();
    };

    Analysis.prototype.run = function(params) {
      this.setUrl(BASE_URL);
      return this.post(params);
    };

    Analysis.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    Analysis.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    Analysis.prototype.stop = function(id) {
      this.setUrl([BASE_URL, id, 'stop'].join('/'));
      return this.post();
    };

    return Analysis;
  }
  AnalysisRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('ChannelsRest', ChannelsRest);

  /** @ngInject */
  function ChannelsRest(ModelRest) {
    var Channels = function () {
    };
    var BASE_URL = '/channels'; // todo: implement REST end-points in server

    Channels.prototype = new ModelRest(BASE_URL);

    Channels.prototype.list = function () {
      return this.get();
    };

    Channels.prototype.save = function (params) {
      return this.post(params);
    };

    // TODO: Methods below do not satisfy RESTful pattern, they are very specifc, and need to be refactored
    
    Channels.prototype.fetchChannels = function (params) {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.post(params);
    };

    var configureChannelUrl = '/configure/channel_update/json';
    Channels.prototype.getOne = function (id) {
      this.setUrl(configureChannelUrl + '?channel_id=' + id);
      return this.get();
    };

    Channels.prototype.updateConfigureChannel = function (params) {
      this.setUrl(configureChannelUrl);
      return this.post(params);
    };

    Channels.prototype.getConfigureChannels = function (params) {
      this.setUrl(configureChannelUrl);
      return this.get(params);
    };

    Channels.prototype.getChannelTypes = function () {
      this.setUrl('/configure/channel_types/json');
      return this.get();
    };

    var newChannelUrl = '/configure/channels/json';
    Channels.prototype.saveNewChannel = function (params) {
      this.setUrl(newChannelUrl);
      return this.post(params);
    };

    // from _commons/channels
    Channels.prototype.loadChannelsByType = function (params) {
      this.setUrl('/channels_by_type/json');
      return this.post(params);
    };

    return Channels;
  }
  ChannelsRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('TrackingChannel', TrackingChannel);

  // TODO: need to be refactored
  /** @ngInject */
  function TrackingChannel($resource) {
    return $resource('/tracking/:what/json', {what: '@what'}, {
      add_keyword: {method: 'POST', params: {what: 'keywords'}, isArray: false},
      add_skipword: {method: 'POST', params: {what: 'skipwords'}, isArray: false},
      add_watchword: {method: 'POST', params: {what: 'watchwords'}, isArray: false},
      add_username: {method: 'POST', params: {what: 'usernames'}, isArray: false},
      add_language: {method: 'POST', params: {what: 'languages'}, isArray: false},
      remove_keyword: {method: 'DELETE', params: {what: 'keywords'}, isArray: false},
      remove_skipword: {method: 'DELETE', params: {what: 'skipwords'}, isArray: false},
      remove_watchword: {method: 'DELETE', params: {what: 'watchwords'}, isArray: false},
      remove_username: {method: 'DELETE', params: {what: 'usernames'}, isArray: false},
      remove_language: {method: 'DELETE', params: {what: 'languages'}, isArray: false},
      get_keywords: {method: 'GET', params: {what: 'keywords'}, isArray: false},
      get_skipwords: {method: 'GET', params: {what: 'skipwords'}, isArray: false},
      get_watchwords: {method: 'GET', params: {what: 'watchwords'}, isArray: false},
      get_usernames: {method: 'GET', params: {what: 'usernames'}, isArray: false},
      get_languages: {method: 'GET', params: {what: 'languages'}, isArray: false}
    });
  }
  TrackingChannel.$inject = ["$resource"];
})();
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
  ContactLabelsRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('CustomerSegmentsRest', CustomerSegmentsRest);

  /** @ngInject */
  function CustomerSegmentsRest(ModelRest) {
    var CustomerSegments = function () {};
    var BASE_URL = '/api/customer_segments';

    CustomerSegments.prototype = new ModelRest(BASE_URL);

    CustomerSegments.prototype.list = function() {
      return this.get();
    };

    CustomerSegments.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    CustomerSegments.prototype.save = function(params) {
      return this.post(params);
    };

    CustomerSegments.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    return CustomerSegments;
  }
  CustomerSegmentsRest.$inject = ["ModelRest"];
})();
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
  DatasetsRest.$inject = ["$q", "ModelRest"];
})();

(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('MetricsRest', MetricsRest);

  /** @ngInject */
  function MetricsRest(ModelRest) {
    var Metrics = function() {}; // TODO: this end-point does not exist for time being
    var BASE_URL = '/journeys';

    Metrics.prototype = new ModelRest(BASE_URL);

    Metrics.prototype.list = function() {
      this.get();
    };

    return Metrics;
  }
  MetricsRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('EventTypesRest', EventTypesRest);

  /** @ngInject */
  function EventTypesRest(ModelRest) {
    var EventTypes = function () {};
    var BASE_URL = '/event_type';

    EventTypes.prototype = new ModelRest(BASE_URL);

    EventTypes.prototype.list = function(channel_type_id) {
      if (channel_type_id) {
        this.setUrl([BASE_URL, 'list?channel_type_id=' + channel_type_id].join('/'));
      } else {
        this.setUrl([BASE_URL, 'list'].join('/'));
      }
      return this.get();
    };

    EventTypes.prototype.getOne = function(name) {
      this.setUrl([BASE_URL, 'get', name].join('/'));
      return this.get();
    };

    EventTypes.prototype.updateSchema = function (name, params) {
      this.setUrl([BASE_URL, 'update_schema', name].join('/'));
      return this.post(params);
    };

    EventTypes.prototype.applySchema = function (name) {
      this.setUrl([BASE_URL, 'sync/apply', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.acceptSchema = function (name) {
      this.setUrl([BASE_URL, 'sync/accept', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.cancelSchema = function (name) {
      this.setUrl([BASE_URL, 'sync/cancel', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.delete = function(name) {
      this.setUrl([BASE_URL, 'delete', name].join('/'));
      return this.post();
    };

    EventTypes.prototype.create = function (params) {
      this.setUrl([BASE_URL, 'create'].join('/'));
      return this.post(params);
    };

    EventTypes.prototype.importData = function(params) {
      this.setUrl([BASE_URL, 'import_data'].join('/'));

      var formData = new FormData();
      if (params.name) {
        formData.append('name', params.name);
      }
      if (params.file) {
        formData.append('file', params.file);
      }
      if (params.sep) {
        formData.append('sep', params.sep);
      }
      if (params.channel_id) {
        formData.append('channel_id', params.channel_id);
      }

      return this.request({
        method: 'POST',
        data: formData,
        transformRequest: angular.identity,
        headers: { 'Content-Type': undefined }
      });
    };

    EventTypes.prototype.discoverSchema = function(params) {
      this.setUrl([BASE_URL, 'discover_schema'].join('/'));

      var formData = new FormData();
      if (params.name) {
        formData.append('name', params.name);
      }
      if (params.file) {
        formData.append('file', params.file);
      }
      if (params.sep) {
        formData.append('sep', params.sep);
      }

      return this.request({
        method: 'POST',
        data: formData,
        transformRequest: angular.identity,
        headers: { 'Content-Type': undefined }
      });
    };

    return EventTypes;
  }
  EventTypesRest.$inject = ["ModelRest"];
})();
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
  GroupsRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('JourneysRest', JourneysRest);

  /** @ngInject */
  function JourneysRest(ModelRest) {
    var Journeys = function () {};
    var BASE_URL = '/journeys';

    Journeys.prototype = new ModelRest(BASE_URL);

    Journeys.prototype.mcp = function(params) {
      this.setUrl([BASE_URL, 'mcp'].join('/'));
      return this.post(params);
    };

    return Journeys;
  }
  JourneysRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('JourneyFunnelsRest', JourneyFunnelsRest);

  /** @ngInject */
  function JourneyFunnelsRest(ModelRest) {
    var JourneyFunnels = function () {};
    var BASE_URL = '/funnels';

    JourneyFunnels.prototype = new ModelRest(BASE_URL);

    JourneyFunnels.prototype.list = function() {
      return this.get();
    };

    JourneyFunnels.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    JourneyFunnels.prototype.save = function(params, isEditMode) {
      // Edit mode doesn't accept 'POST' request.
      if (isEditMode) {
        return this.put(params);
      } else {
        return this.post(params);
      }
    };
    
    JourneyFunnels.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    return JourneyFunnels;
  }
  JourneyFunnelsRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('JourneyTagsRest', JourneyTagsRest);

  /** @ngInject */
  function JourneyTagsRest(ModelRest) {
    var JourneyTags = function () {};
    var BASE_URL = '/journey_tags';

    JourneyTags.prototype = new ModelRest(BASE_URL);

    JourneyTags.prototype.list = function() {
      return this.get();
    };

    JourneyTags.prototype.getOne = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.get();
    };

    JourneyTags.prototype.save = function(params) {
      return this.post(params);
    };

    JourneyTags.prototype.remove = function(id) {
      this.setUrl([BASE_URL, id].join('/'));
      return this.delete();
    };

    return JourneyTags;
  }
  JourneyTagsRest.$inject = ["ModelRest"];
})();
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
  JourneyTypesRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('PredictorsRest', PredictorsRest);

  /** @ngInject */
  function PredictorsRest(ModelRest, $q) {
    var Predictors = function () {
    };
    var BASE_URL = '/predictors';

    Predictors.prototype = new ModelRest(BASE_URL);

    Predictors.prototype.facets = {};

    Predictors.prototype.getOne = function (predictorId) {
      this.setUrl([BASE_URL, predictorId].join('/'));
      return this.get();
    };

    Predictors.prototype.list = function (params) {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.get(params);
    };

    Predictors.prototype.getPredictorFacets = function (predictor) {
      this.setUrl([BASE_URL, predictor.id, 'detail?facets=1'].join('/'));
      return this.get();
    };

    Predictors.prototype.getDefaultPredictor = function () {
      this.setUrl([BASE_URL, 'default-template'].join('/'));
      return this.get();
    };

    Predictors.prototype.getPredictorDetails = function (predictorId) {
      this.setUrl([BASE_URL, predictorId, 'detail'].join('/'));
      return this.get();
    };

    Predictors.prototype.doClassifier = function (action, predictor_id) {
      this.setUrl([BASE_URL, 'command', action, predictor_id].join('/'));

      if (action !== 'reset' && action !== 'retrain') {
        throw Error("Only actions 'reset' and 'retrain' supported. Given '" + action + "'");
      }
      return this.get();
    };

    Predictors.prototype.generatePredictorData = function (predictorId, fromDt, toDt) {
      this.setUrl([BASE_URL, 'command', 'generate_data', predictorId].join('/'));
      return this.post({'from_dt': fromDt, 'to_dt': toDt});
    };

    Predictors.prototype.purgePredictorData = function (predictorId, fromDt, toDt) {
      this.setUrl([BASE_URL, 'command', 'purge_data', predictorId].join('/'));
      return this.post({'from_dt': fromDt, 'to_dt': toDt});
    };

    Predictors.prototype.checkGenerationStatus = function (predictorId) {
        this.setUrl([BASE_URL, 'command', 'check_status', predictorId].join('/'));
        return this.get();
    };

    Predictors.prototype.removePredictor = function (predictorId) {
      this.setUrl([BASE_URL, predictorId].join('/'));
      return this.delete();
    };

    // MODELS
    Predictors.prototype.getOneModel = function (predictorId, modelId) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId].join('/'));
      return this.get();
    };

    Predictors.prototype.listModels = function (predictorId, with_deactivated) {
      var url = [BASE_URL, predictorId, 'models'].join('/');
      if (with_deactivated) {
        url += '?with_deactivated=true';
      }
      this.setUrl(url);
      return this.get();
    };

    Predictors.prototype.saveModel = function (predictorId, params) {
      this.setUrl([BASE_URL, predictorId, 'models'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.doModelAction = function (predictorId, modelId, action, params) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId, action].join('/'));
      return this.post(params);
    };

    Predictors.prototype.updateModel = function (predictorId, modelId, params) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId].join('/'));
      return this.put(params);
    };

    Predictors.prototype.removeModel = function (predictorId, modelId) {
      this.setUrl([BASE_URL, predictorId, 'models', modelId].join('/') + '?hard=true');
      return this.delete();
    };

    Predictors.prototype.create = function (params) {
      this.setUrl([BASE_URL, 'json'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.getDetails = function (id, params) {
      this.setUrl([BASE_URL, id, 'data/json'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.getMatchResults = function (id, params) {
      this.setUrl([BASE_URL, id, 'search'].join('/'));
      return this.post(params);
    };

    Predictors.prototype.update = function (predictorId, params) {
      this.setUrl([BASE_URL, predictorId].join('/'));
      return this.post(params);
    };

    return Predictors;
  }
  PredictorsRest.$inject = ["ModelRest", "$q"];
})();

(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('SmartTagsRest', SmartTagsRest);

  /** @ngInject */
  function SmartTagsRest(ModelRest) {
    var BASE_URL = '/smart_tags';
    var SmartTags = function () {
      this.listUrl = [BASE_URL, 'json'].join('/')
    };

    SmartTags.prototype = new ModelRest(BASE_URL);

    SmartTags.prototype.list = function(params) {
      this.setUrl(this.listUrl);
      return this.get(params);
    };

    SmartTags.prototype.action = function(action, params) {
      this.setUrl([BASE_URL, action, 'json'].join('/'));
      return this.post(params);
    };

    return SmartTags;
  }
  SmartTagsRest.$inject = ["ModelRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('Response', Response);

  // TODO: need to be refactored
  /** @ngInject */
  function Response($resource) {
    return $resource('/commands/:action', {}, {
      star: {method: 'POST', params: {action: "star_response"}, isArray: false},
      unstar: {method: 'POST', params: {action: "unstar_response"}, isArray: false},
      forward: {method: 'POST', params: {action: "forward_response"}, isArray: false},
      follow: {method: 'POST', params: {action: "follow_user"}, isArray: false},
      unfollow: {method: 'POST', params: {action: "unfollow_user"}, isArray: false},
      like: {method: 'POST', params: {action: "like_post"}, isArray: false},
      share: {method: 'POST', params: {action: "share_post"}, isArray: false},
      retweet: {method: 'POST', params: {action: "retweet_response"}, isArray: false},
      skip: {method: 'POST', params: {action: "skip_response"}, isArray: false},
      reject: {method: 'POST', params: {action: "reject_response"}, isArray: false},
      post: {method: 'POST', params: {action: "post_response"}, isArray: false},
      post_response_and_case: {method: 'POST', params: {action: "post_response_and_case"}, isArray: false},
      post_custom: {method: 'POST', params: {action: "custom_response"}, isArray: false},
      post_reply: {method: 'POST', params: {action: "custom_reply"}, isArray: false},
      post_custom_response_and_case: {method: 'POST', params: {action: "post_custom_response_and_case"}, isArray: false}
    });
  }
  Response.$inject = ["$resource"];
})();
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
  UserRolesRest.$inject = ["ModelRest"];
})();
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
  SchemaProfilesRest.$inject = ["$q", "ModelRest"];
})();

(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('ChannelTypesRest', ChannelTypesRest);

  /** @ngInject */
  function ChannelTypesRest($q, ModelRest) {
    var ChannelTypes = function () {};
    var BASE_URL = '/channel_type';

    ChannelTypes.prototype = new ModelRest(BASE_URL);

    ChannelTypes.prototype.list = function(params) {
      this.setUrl([BASE_URL, 'list'].join('/'));
      return this.get(params);
    };

    ChannelTypes.prototype.getOne = function(name) {
      this.setUrl([BASE_URL, 'get', name].join('/'));
      return this.get();
    };

    ChannelTypes.prototype.create = function (params) {
      this.setUrl([BASE_URL, 'create'].join('/'));
      return this.post(params);
    };

    ChannelTypes.prototype.update = function (name, params) {
      this.setUrl([BASE_URL, 'update', name].join('/'));
      return this.post(params);
    };

    ChannelTypes.prototype.applySync = function (name, params) {
      this.setUrl([BASE_URL, 'apply_sync', name].join('/'));
      return this.post();
    };

    ChannelTypes.prototype.delete = function (name) {
      this.setUrl([BASE_URL, 'delete', name].join('/'));
      return this.post();
    };

    return ChannelTypes;
  }
  ChannelTypesRest.$inject = ["$q", "ModelRest"];
})();

(function () {
  'use strict';

  angular
    .module('slr.utils', [
      'ark-components',
      'ark-ui-bootstrap',
      'ui.select2',
      'ui.jq'
    ])
    .config(["$httpProvider", function ($httpProvider) {
      //initialize get if not there
      if (!$httpProvider.defaults.headers.get) {
        $httpProvider.defaults.headers.get = {};
      }
      //disable IE ajax request caching
      $httpProvider.defaults.headers.get['If-Modified-Since'] = '0';
      // flask needs this to detect AJAX request (via flask.request.is_xhr)
      $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
      //register custom interceptor
      $httpProvider.interceptors.push('myHttpInterceptor');
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .service('Utils', Utils);

  /** @ngInject*/
  function Utils() {
    this.toTitleCase = function (str) {
      return str.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
      });
    };

    this.roundUpTo2precision = function (num) {
      if (!num) return 0;
      var res;
      if (num.length) {
        res = _.map(num, function (n) {
          return Math.round(n * 100) / 100;
        });
      } else {
        res = Math.round(num * 100) / 100;
      }
      return res;
    };

    this.mean = function (list) {
      return list.reduce(function (p, c) {
          return parseFloat(p) + parseFloat(c);
        }) / list.length;
    };

    this.objToArray = function (obj, objkeys) {
      var keys = _.keys(obj);
      var values = _.values(obj);
      var arr = [];

      if (!objkeys) {
        objkeys = ['key', 'value'];
      }

      _.each(keys, function (k, i) {
        if (values[i] !== null) {
          arr.push(_.object(objkeys, [k, values[i]]));
        }
      });
      return arr;
    };

    this.compareArrays = function (a1, a2) {
      return (a1.length == a2.length) && a1.every(function (el, i) {
          return el === a2[i];
        });
    };

    this.noDataMessageHtml = function (params) {
      var noDataMessage = function (params) {
        var defaultNoDataMessage = null,
          noDataMessage = params.hasOwnProperty('noDataMessage') ? (params.noDataMessage() || defaultNoDataMessage) : defaultNoDataMessage;
        return noDataMessage;
      };

      var noDataMessageHeader = function (params) {
        var defaultNoDataHeader = " No Data Available",
          noDataMessageHeader = params.hasOwnProperty('noDataMessageHeader') ? (params.noDataMessageHeader() || defaultNoDataHeader) : defaultNoDataHeader;
        return noDataMessageHeader;
      };

      var header = "<i class='icon-alert-triangle'></i> header".replace('header', noDataMessageHeader(params));
      var message = !noDataMessage(params) ? '' : "<p>message</p>".replace('message', noDataMessage(params));
      return "<div class='alert alert-info text-center'>" + header + message + "</div>";
    };

    this.generateTicks = function (opts, tickSize) {
      var ticks = [],
        start = opts.min,
        i = 0,
        v = Number.NaN,
        prev;

      do {
        prev = v;
        v = start + i * tickSize;
        ticks.push(v);
        ++i;
      } while (v < opts.max && v != prev);
      return ticks;
    };

    this.formatSeconds = function (seconds) {
      function makeLabel(v, mode) {
        mode = mode || 'minutes';
        if (isNaN(v)) {
          return "";
        }
        var res;
        if (v >= 3600) {
          res = "" + Math.floor(v / 3600) + 'h';
          v = v % 3600;
        } else if (v >= 60) {
          var round = mode == 'seconds' ? Math.floor : Math.ceil;
          res = "" + round(v / 60) + 'm';
          v = v % 60;
        } else {
          if (mode == 'minutes') {
            return "";
          } else if (mode == 'seconds') {
            return Math.ceil(v) + 's';
          }
        }
        return res + " " + makeLabel(v, mode);
      }

      return seconds ? makeLabel(seconds, seconds < 60 ? "seconds" : "minutes") : "0";
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    // create the interceptor as a service, intercepts ALL angular ajax http calls
    .factory('myHttpInterceptor', myHttpInterceptor);

  /** @ngInject */
  function myHttpInterceptor($q, $log, $timeout, $rootScope, $injector) {
    var SystemAlert = function () {
        return $injector.get('SystemAlert');
      },
    //list of endpoints where we don't want to show loading message:
      exclude_loading_urls = [
        '/posts/json',
        '/posts/crosstag/json',
        '/error-messages/json',
        '/error-messages/count',
        '/smart_tags/json'
      ],
      exclude_error_urls = [
        '/twitter/users',
        '/predictors/expressions/validate',
        '/facet-filters/agent',
        '/facet-filters/customer'
      ],
      ON_JSON_BEING_FETCHED = 'onJsonBeingFetched',
      ON_JSON_FETCHED = 'onJsonFetched';

    function shouldShowErrorForUrl(url) {
      return (exclude_error_urls.indexOf(url) == -1);
    }

    function shouldShowLoadingForUrl(url) {
      return (exclude_loading_urls.indexOf(url) == -1);
    }

    function formatErrorResponse(resp) {
      var status = resp.status,
        method = resp.config.method,
        url = resp.config.url,
        params = resp.config.params || resp.config.data,
        data = resp.data;
      return [[method, url, status].join(' '), {requestParams: params, responseData: data}];
    }

    function showAlert(response) {
      var d = response.data,
        e = d.error || d.result || d.messages, // all possible error sources
        w = d.warn,
        ok = d.ok;
      if (ok === false && e) {
        var error = angular.isArray(e) ? e[0].message : e;
        if (shouldShowErrorForUrl(response.config.url)) {
          SystemAlert().error(error);
        }
        $log.error('response', formatErrorResponse(response), response);
      }
      if (ok === false && w) {
        var warn = angular.isArray(w) ? w[0].message : w;
        if (shouldShowErrorForUrl(response.config.url)) {
          SystemAlert().warn(warn);
        }
      }
      return {ok: ok, shown: (ok === false && (e || w))};
    }

    return {
      'request': function (config) {
        $rootScope.$broadcast(ON_JSON_BEING_FETCHED);
        // Don't show loading message automatically, will use explicitly
        // if (shouldShowLoadingForUrl(config.url)) {
        //   SystemAlert().showLoadingMessage();
        // }
        return config || $q.when(config);
      },

      'requestError': function (rejection) {
        $log.error('requestError', rejection);
        return $q.reject(rejection);
      },

      'response': function (response) {
        $rootScope.$broadcast(ON_JSON_FETCHED);
        $timeout(SystemAlert().hideLoadingMessage, 800);
        var alert = showAlert(response);
        return (alert.ok === false ? $q.reject(response) : response || $q.when(response));
      },

      'responseError': function (response) {
        SystemAlert().hideLoadingMessage();
        var alert = showAlert(response);
        if (response.status !== 0 && !alert.shown && shouldShowErrorForUrl(response.config.url)) {
          SystemAlert().error('Unknown error - failed to complete operation.');
        }
        if (response.status === 0 && response.data === ""
          && shouldShowErrorForUrl(response.config.url)
          && shouldShowLoadingForUrl(response.config.url)) {
          // network or cross-domain error
          var isFirefox = false;
          try { // workaround for #4010
            // Note: status=0 is also being set for cancelled requests,
            // and Firefox display those when pending ajax requests
            // are cancelled during page change.
            isFirefox = (navigator.userAgent.toLowerCase().indexOf('firefox') > -1);
          } catch (err) {
          }

          if (!isFirefox) {
            SystemAlert().error('Network error. Request has been rejected.');
          }
        }
        $log.error('responseError', response);
        return $q.reject(response);
      }
    };
  }
  myHttpInterceptor.$inject = ["$q", "$log", "$timeout", "$rootScope", "$injector"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .factory('SystemAlert', SystemAlert);

  /**
   * Handles error System alerts, e.g. coming from server
   */
  /** @ngInject */
  function SystemAlert($http, $rootScope) {
    function pollErrorCount() {
      return $http({
        method: 'GET',
        url: "/error-messages/count"
      }).then(function (res) {
        if (parseInt(res.data['count']) > 0) {
          return fetchErrorMessages();
        }
      });
    }

    function fetchErrorMessages() {
      return $http({
        method: 'GET',
        url: "/error-messages/json"
      }).then(function (resp) {
        var data = resp.data,
          errors = data['data'],
          messages = [];
        for (var idx = 0; idx < errors.length; idx++) {
          messages.push({
            type: 'error',
            message: errors[idx]['message']
          });
        }
        instance.showMessages(messages);
      });
    }

    var timer = null,
      instance = {
        MESSAGE_EVENT: 'SystemAlert.MESSAGE_EVENT',
        startPolling: function () {
          if (!timer) {
            timer = setInterval(pollErrorCount, 20000);
          }
        },
        stopPolling: function () {
          clearInterval(timer);
          timer = null;
        },
        showMessages: function (msgs, timeout) {
          $rootScope.$emit(this.MESSAGE_EVENT, {messages: msgs, timeout: timeout});
        },

        showLoadingMessage: function () {
          angular.element('#loading').show();
        },
        hideLoadingMessage: function () {
          angular.element('#loading').hide();
        }
      };
    ['error', 'info', 'success', 'warn'].forEach(function (method) {
      instance[method] = function (msg, timeout) {
        this.showMessages({type: method, message: msg}, timeout);
      }.bind(instance);
    });
    instance.log = instance.success;

    instance.startPolling();
    return instance;
  }
  SystemAlert.$inject = ["$http", "$rootScope"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('array', Array);

  /**
   * ng-repeat="item in items | _:'pluck':'title' | array:'join':', '" -> Title1, Title2, Title3
   * @returns {Function}
   * @constructor
   */
  function Array() {
    return function (array, method) {
      return Array.prototype[method].apply(array, Array.prototype.slice.call(arguments, 2));
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('linky2', linky2);

  function linky2() {
    var URLregex = /(\b(https?:\/\/|www\.)\S*\w)/g;
    return function (input) {
      if (!input) return input;
      return input.replace(URLregex, function (s) {
        s = (s.indexOf('://') == -1) ? 'http://' + s : s;
        return '<a href="' + s + '" target="_blank" rel="nofollow">' + s + '</a>';
      });
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('momentutc', momentutc);

  // http://momentjs.com
  function momentutc() {
    return function (time, format) {
      if (format) {
        return moment.utc(time).format(format);
      } else {
        // returning moment object is not safe, because: moment.utc(aTimestamp) != moment.utc(aTimestamp)
        // if moment object were returned, angular will detect the returned value has changed even for same input
        // thereby recusively calling $digest cycle, eventually crashing with:
        // Error: $rootScope:infdig Infinite $digest Loop
        return moment.utc(time).toString();
      }
    };
  }
})();

(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('moment', Moment);

  // http://momentjs.com
  function Moment() {
    return function (time, format) {
      if (format) {
        return moment(time).format(format);
      } else {
        // returning moment object is not safe, because: moment.utc(aTimestamp) != moment.utc(aTimestamp)
        // if moment object were returned, angular will detect the returned value has changed even for same input
        // thereby recusively calling $digest cycle, eventually crashing with:
        // Error: $rootScope:infdig Infinite $digest Loop
        return moment(time).toString();
      }
    };
  }
})();

(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('pluralize', pluralize);

  /**
   * pluralize:{'sing':'post', 'pl':'posts'}
   * @returns {Function}
   */
  function pluralize() {
    return function (num, text) {
      if (num === 1) {
        return num + ' ' + text.sing;
      } else {
        return num + ' ' + text.pl;
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('propsFilter', propsFilter);

  function propsFilter() {
    return function (items, props) {
      var out = [];

      if (angular.isArray(items)) {
        items.forEach(function (item) {
          var itemMatches = false;

          var keys = Object.keys(props);
          for (var i = 0; i < keys.length; i++) {
            var prop = keys[i];
            var text = props[prop].toLowerCase();
            if (item[prop].toString().toLowerCase().indexOf(text) !== -1) {
              itemMatches = true;
              break;
            }
          }

          if (itemMatches) {
            out.push(item);
          }
        });
      } else {
        // Let the output be the input untouched
        out = items;
      }

      return out;
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('toTitleCase', toTitleCaseFilter);

  /**
   * 'customer gender' | toTitleCase -> Customer gender
   * @param Utils
   * @returns {Function}
   */
  /** @ngInject */
  function toTitleCaseFilter(Utils) {
    return function (str) {
      if (str) {
        return Utils.toTitleCase(str.replace(/[_-]/g, ' ')).replace('Id', '');
      }
    }
  }
  toTitleCaseFilter.$inject = ["Utils"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('truncate', truncate);

  function truncate() {
    return function (text, length, end) {
      if (isNaN(length))
        length = 10;
      if (_.isUndefined(end)) {
        end = "...";
      }
      if (text && text.length <= length || text && text.length - end.length <= length) {
        return text;
      }
      else {
        return String(text).substring(0, length) + end;
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('_', Underscore);

  /**
   * ng-repeat="item in items | _:'unique'"
   * ng-repeat="item in items | _:'pluck':'title'"
   * @returns {Function}
   * @constructor
   */
  function Underscore() {
    return function (obj, method) {
      var args = Array.prototype.slice.call(arguments, 2);
      args.unshift(obj);
      return _[method].apply(_, args);
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('arkSwitch', arkSwitch);

  /** @ngInject */
  function arkSwitch() {
    return {
      restrict: 'E',
      templateUrl: '/static/assets/js/app/_utils/directives/ark-switch/utils.ark-switch.directive.html',
      scope: {
        switchModel: '=',
        switchId: '=',
        switchOn: '=',
        switchOff: '=',
        disabledCase: '='
      }
    }
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('search', search);

  /** @ngInject */
  function search() {
    return {
      restrict: 'E',
      scope: {
        filter: '=',
        placeholderText: '@',
        control: '=?'
      },
      templateUrl: '/static/assets/js/app/_utils/directives/search/utils.search.directive.html',
      link: function (scope) {
        scope.isReloadShown = angular.isDefined(scope.control);
        scope.reload = function () {
          if (angular.isDefined(scope.control)) {
            scope.control();
          }
        }
      }
    }
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('slrAlert', systemAlertContainer);

  /**
   * display manual alerts from controllers
   * also handle alerts coming from backend thru HTTP requests
   */
  /** @ngInject */
  function systemAlertContainer($rootScope, SystemAlert, toaster) {
    var state = {
        messages: []
      },
      template = '<div>' +
        '<ark-toaster toaster-options="alertOptions"></ark-toaster>' +
        '</div>';

    return {
      restrict: "AE",
      template: template,
      replace: true,
      link: function (scope) {
        scope.alertOptions = {
          'time-out': 5000,
          'close-button': true,
          'position-class': 'toast-top-right'
        };

        $rootScope.$on(SystemAlert.MESSAGE_EVENT, function (event, data) {
          var newMessages = data.messages;
          if (!angular.isArray(newMessages)) {
            newMessages = [newMessages];
          }
          state.messages.push.apply(state.messages, newMessages);
          _.each(newMessages, function (alert) {
            toaster.pop(alert.type, alert.message, '', data.timeout || 2000);
          });
        });
      }
    }
  }
  systemAlertContainer.$inject = ["$rootScope", "SystemAlert", "toaster"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('dateIsGreaterThan', dateIsGreaterThan);

  function dateIsGreaterThan() {
    var name = 'dateIsGreaterThan',
      startDate;

    return {
      require: 'ngModel',
      link: function (scope, elm, attrs, ctrl) {
        function isGreater(d1, d2) {
          return !d1 || new Date(d1) > new Date(d2);
        }

        function validateSelf(viewValue) {
          if (isGreater(viewValue, startDate)) {
            ctrl.$setValidity(name, true);
            return viewValue;
          } else {
            ctrl.$setValidity(name, false);
            return undefined;
          }
        }

        function validateStartDate(date) {
          startDate = date;
          ctrl.$setValidity(name, isGreater(ctrl.$modelValue, startDate));
        }

        ctrl.$parsers.unshift(validateSelf);
        scope.$watch(attrs[name], validateStartDate);
      }
    };
  }

})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('emailcheck', emailCheck);

  function emailCheck() {
    var EMAIL_REGEXP = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$/;
    var testEmails = function (emails) {
      return _.all(emails.split(/[,;:\s\n\t]+/), function (email) {
        return EMAIL_REGEXP.test(email);
      });
    };
    return {
      restrict: 'A',
      require: 'ngModel',
      link: function (scope, elm, attrs, ctrl) {
        ctrl.$parsers.unshift(function (viewValue) {
          if (!viewValue) {
            ctrl.$setValidity('emailcheck', true);
            return viewValue;
          }
          ctrl.$setValidity('emailcheck', testEmails(viewValue));
          return viewValue;
        });

        scope.$watch(attrs.ngModel, function (val) {
          if (val) {
            ctrl.$setValidity('emailcheck', testEmails(val));
          }
        });
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('slrInfoModal', slrInfoModal);

  /**
   * ARK UI bootstrap $modal to display the static content
   */
  /** @ngInject */
  function slrInfoModal($modal) {
    return {
      restrict: 'EA',
      scope: {
        template: '@slrInfoModal'
      },
      link: function (scope) {
        var settings = {
          scope: scope
        };

        if (scope.template.slice(-4) === 'html') {
          _.extend(settings, {templateUrl: scope.template});
        } else {
          _.extend(settings, {template: scope.template});
        }

        $modal.open(settings);
      }
    }
  }
  slrInfoModal.$inject = ["$modal"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('myMaxlength', myMaxLength);

  function myMaxLength() {
    return {
      require: 'ngModel',
      link: function (scope, element, attrs, ngModelCtrl) {
        var maxlength = Number(attrs.myMaxlength);

        function fromUser(text) {
          if (text && text.length > maxlength) {
            var transformedInput = text.substring(0, maxlength);
            ngModelCtrl.$setViewValue(transformedInput);
            ngModelCtrl.$render();
            ngModelCtrl.$overflow = true;
            return transformedInput;
          }
          ngModelCtrl.$overflow = false;
          return text;
        }

        ngModelCtrl.$parsers.push(fromUser);
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('postSmartTags', postSmartTags);

  /** @ngInject */
  function postSmartTags() {
    var tpl = '<select id="sel_{{ $id }}" style="width:100%" data-placeholder="Pick a tag">' +
      '<option value=""></option>' +
      '<option ng-value="item.id" ng-repeat="item in allSmartTags">{{ item.title }}</option></select>';
    return {
      template: tpl,
      replace: true
    }
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('removeSmartTag', removeSmartTag);

  /** @ngInject */
  function removeSmartTag(SmartTags, ChannelsService) {
    return {
      scope: {
        item: "=removeSmartTag",
        tag: "=",
        selectedTagFilter: "="
      },
      link: function (scope, elm, attrs) {
        scope.channelId = ChannelsService.getSelectedId();
        elm.on('click', function () {
          var post_id = scope.item.id_str;
          var response_id = attrs.responseId;
          SmartTags.removePostTags(scope.channelId, post_id, scope.tag.id, response_id).then(function (res) {
            scope.item.smart_tags = _.filter(scope.item.smart_tags, function (el) {
              return el.id !== scope.tag.id
            });
            scope.$emit(SmartTags.ON_POST_TAGS_REMOVED, response_id, post_id);
          });
        })
      }
    }
  }
  removeSmartTag.$inject = ["SmartTags", "ChannelsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('responseMessage', responseMessage);

  /** @ngInject */
  function responseMessage($compile, AccountsService, $rootScope) {
    return {
      replace: true,
      template: '<div class="responseText"  ng-model="scope.message">'
      + '<span class="respondTo"   ng-bind="respondTo"></span>'
      + '<span ng-show="!isEditMode && isEmpty()" class="placeholder respondFrom">Please type a response...&nbsp;</span>'
      + '<span class="respondFrom" ng-bind="signature"></span>'
      + '</div>',
      require: '?ngModel',
      scope: {
        responseMessage: '=',
        model: '=ngModel',
        focus: '=responseMessageFocus'
      },

      link: function (scope, element, attrs, ngModel) {
        var acc = AccountsService.getCurrent();
        var response = scope.responseMessage;
        if (scope.responseMessage.platform == 'Twitter') {
          // Twitter limit is 140 chars
          scope.limit = 140;
        } else if (scope.responseMessage.platform == 'Facebook') {
          // Facebook has no clear limit, need to check what actually makes sense
          // for our inbox.
          scope.limit = 400;
        } else {
          // This should NEVER be the case. Just a safety precaution.
          scope.limit = 100;
        }

        scope.respondTo = response.post.user.user_name + ' ';
        scope.message = ' ';
        scope.signature = acc ? ' ' + acc.signature : '';
        scope.isEditMode = false;
        scope.responseMessage.custom_response = _.extend({}, scope.message);
        scope.responseMessage.prefix = scope.respondTo;
        scope.responseMessage.suffix = scope.signature;
        scope.isEmpty = function () {
          return !(scope.message || "").trim().replace('&nbsp;').length;
        };

        $rootScope.$watch('showMatches', function (nVal) {
          if (!nVal) {
            scope.message = response.match ? response.match.matchable.creative : response.matchable.creative;
            ngModel.$render(false);
          } else {
            scope.message = '&nbsp;';
            ngModel.$render(false);
            m.focus();
          }

        })
        scope.cancelEdit = function (el) {
          element.removeClass("beingEdited");
          m.attr({'contenteditable': false});
          scope.isEditMode = false;
          scope.$parent.isEditMode = false;
          scope.message = scope.message;
          ngModel.$render(false);

        }

        element.on('click', function () {
          if (scope.$parent.responseType && scope.$parent.responseType != 'posted') {

            m.attr({'contenteditable': true});
            m.focus();
            if (!scope.$parent.$$phase) {
              scope.$apply(scope.$parent.isEditMode = true);
            }
            if (!element.hasClass("beingEdited")) {
              ngModel.$render(true);
            } else {
              angular.noop();
            }
            element.addClass("beingEdited");

          } else {
            angular.noop();
          }

        });

        scope.$watch('focus', function (nVal, oVal) {
          if (nVal != oVal) {
            if (nVal == true) {
              element.trigger('click');
              scope.isEditMode = true;
            } else {
              scope.isEditMode = false;
            }
          }
        })

        scope.submitCustomResponse = function (message_type) {
          scope.$parent.submitCustomResponse(response, message_type)
        }

        scope.postCustomResponseCreateCase = function () {
          scope.$parent.postCustomResponseCreateCase(response)
        }

        scope.$watch('$parent.isEditMode', function (nVal) {
          scope.isEditMode = nVal;
        });

        scope.isLimitExceeded = function () {
          return scope.count <= -1 || scope.model.trim().length == 0 || scope.model.trim() == scope.message.trim()
        }

        scope.caseButtonVisibility = function () {
          return !response.is_conversation_synced && acc.is_sf_auth;
        }

        scope.postButtonVisibility = function () {
          if (typeof hsp != "undefined") {
            return false;
          }
          return scope.responseMessage.has_both_pub_and_dm || scope.responseMessage.message_type == 0;
        }

        scope.postHSButtonVisibility = function () {
          if (typeof hsp != "undefined") {
            return response.message_type == 0;
          } else {
            return false
          }
        }

        scope.isOriginalResponse = function () {
          if (scope.message == scope.responseMessage.custom_response) {
            return false
          } else {
            return scope.isLimitExceeded();
          }
        }

        scope.submitHSResponse = function (message_type) {
          if (!message_type) message_type = 'public';
          if (scope.message == scope.responseMessage.custom_response) {
            // TODO: do we also allow direct?
            scope.$parent.postResponse(response, message_type);
          } else {
            scope.submitCustomResponse(message_type);
          }
        }

        scope.dmButtonVisibility = function () {
          return response.message_type == 1
        }

        var btns = $compile('<div ng-show="isEditMode" class="editPanel">\
                              <span ng-bind="count" class="counter"></span>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="cancelEdit(this)">Cancel</button>\
                              <button class = "btn btn-xs btn-default" \
                                      ng-click = "postCustomResponseCreateCase()"\
                                      ng-disabled = "isLimitExceeded()"\
                                      ng-show  = "caseButtonVisibility()">Post&ensp;&amp;&ensp;Create Case</button>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="submitCustomResponse(\'public\')"\
                                      ng-disabled = "isLimitExceeded()"\
                                      ng-show = "postButtonVisibility()">Post</button>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="submitHSResponse()"\
                                      ng-disabled = "isOriginalResponse()"\
                                      ng-show = "postHSButtonVisibility()">Post</button>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="submitCustomResponse(\'direct\')"\
                                      ng-disabled = "isLimitExceeded()"\
                                      ng-show = "dmButtonVisibility()">DM</button>\
                            </div>')(scope);

        element.after(btns);
        var m = $compile('<span class="message" ng-model="scope.message">' + twttr.txt.autoLink(scope.message) + '</span>')(scope);

        element.find('.respondTo').after(m);

        var messageEl = m;

        ngModel.$render = function (edit) {
          if (edit) {
            messageEl.html(scope.message);
          } else {
            messageEl.html(twttr.txt.autoLink(scope.message));
          }
          scope.model = scope.message;
        };

        // Listen for change events to enable binding
        messageEl.on('blur keyup change', function () {
          scope.$apply(read);
        });

        //read();
        // Write data to the model
        function read() {
          var html = messageEl.text();
          ngModel.$setViewValue(html);
          scope.model = ngModel.$viewValue;
        }

        var message_length = 0;
        var counter = element.next('.editPanel').find('.counter');
        var filler = '0123456789123456789'

        scope.$watch('model', function (nVal) {
          var extractedUrls = twttr.txt.extractUrlsWithIndices(nVal);
          var virtualTweet = nVal;
          //add 1 for '@' which we don't display but need to count
          message_length = (1 + scope.respondTo.length) + virtualTweet.length + scope.signature.length;

          if (nVal.length > 0) {
            if (extractedUrls.length > 0) {
              _.each(extractedUrls, function (el) {
                virtualTweet = virtualTweet.replace(el.url, filler);
              })
            }
            scope.responseMessage.custom_response = nVal;
            scope.count = scope.limit - message_length;
            if (scope.count <= 3) {
              counter.addClass('counter-red');
            } else if (scope.count > 3 && counter.hasClass('counter-red')) {
              counter.removeClass('counter-red');
            }
          } else {
            messageEl.html('&nbsp;');
            scope.count = scope.limit - message_length;
          }
        })
      }
    }
  }
  responseMessage.$inject = ["$compile", "AccountsService", "$rootScope"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('s2Readonly', s2Readonly);

  /** @ngInject */
  function s2Readonly($timeout) {
    return {
      restrict: "A",
      link: function (scope, iElement, iAttrs) {
        iAttrs.$observe('s2Readonly', function (value) {
          if (value == 'true') {
            $timeout(function () {
              iElement.select2(iAttrs.s2Readonly ? 'disable' : 'enable');
            }, 600, false)
          }
        });
      }
    }
  }
  s2Readonly.$inject = ["$timeout"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('scrollTo', scrollTo);

  // TODO: this directive could be flexible, if you pass Selector. Currently it always scrolls to ng-repeat  
  /** @ngInject */
  function scrollTo() {
    return {
      scope: {
        scrollTo: '=',
        highlightClass: '@'
      },
      link: function (scope, el, attrs) {
        function scrollToIndex(idx) {
          var $scrollToEl = angular.element(el).find('div[ng-repeat]').eq(idx);
          var $scrollView = angular.element(el);
          $scrollView.scrollTo($scrollToEl.offset().top - $scrollView.offset().top);
          if (attrs.highlightClass) {
            $scrollToEl.addClass(attrs.highlightClass);
          }
        }

        scope.$watch('scrollTo', function (val) {
          if (angular.isNumber(val) && val > -1) {
            scrollToIndex(val);
          }
        });
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('sorter', sorter);

  function sorter() {
    var template = "<a style=\"width: 100%;display: block;\" " +
      "ng-click=\"onClick()\">" +
      "<span class=\"pull-left\">" +
      "{{ title }}" +
      "&nbsp;<span ng-if='questionTooltip' class='icon-iw-active-circle-question' tooltip='{{questionTooltip}}' tooltip-placement='top'>&nbsp;" +
      "</span>" +
      "<span class=\"pull-right\">" +
      "<i class=\"icon-search-previous\" ng-show=\"!isArrShown\"></i>" +
      "<i class=\"icon-search-next\" ng-show=\"isArrShown\"></i>" +
      "</span></a>";

    return {
      template: template,
      scope: {
        title: '@title',
        questionTooltip: '@questionTooltip',
        predicate: '@predicate',
        sorter: '='
      },
      link: function (scope, el, attrs) {
        el.addClass("nowrap");

        var pred = scope.predicate,
          tableState = scope.sorter || scope.$parent.table.sort;
        scope.isArrShown = false;

        angular.extend(scope, {
          onClick: function () {
            tableState.predicate = pred;
            tableState.reverse = !tableState.reverse;
            scope.isArrShown = !scope.isArrShown;
          }
        });
      }
    }
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('tagAssignment', tagAssignment);

  /** @ngInject */
  function tagAssignment(SmartTags, ChannelsService) {
    var validatePostTag = function (elm, scope, removeClassName) {
      elm.find('div').on('click', function () {
        SmartTags.addPostTags(
          scope.channelId, scope.postId, scope.tag.id)
          .then(function () {
            elm.removeClass(removeClassName);
            elm.addClass('starred');
          });
      }); //click
    };
    return {
      scope: {
        tag: "=tagAssignment",
        activeTag: "=",
        channelId: "@",
        postId: "="
      },
      link: function (scope, elm) {
        if (_.isArray(scope.activeTag) ? _.indexOf(scope.activeTag, scope.tag.id) !== -1 : scope.activeTag == scope.tag.id) {
          if (scope.tag.assignment == 'starred') {
            elm.addClass('starred');
          } else if (scope.tag.assignment == 'highlighted') {
            elm.addClass('highlighted');
            validatePostTag(elm, scope, 'highlighted');
          } else {
            elm.addClass('selected');
          }
        } else if (scope.activeTag !== ChannelsService.getSelectedId()) {
          elm.addClass('co-highlighted');
          validatePostTag(elm, scope, 'co-highlighted');
        }
      }
    }
  }
  tagAssignment.$inject = ["SmartTags", "ChannelsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('toTopScroller', toTopScroller);

  /** @ngInject */
  function toTopScroller($location, $anchorScroll) {
    return {
      restrict: 'A',
      link: function (scope, elem) {
        angular.element(document).scroll(function () {
          var y = angular.element(this).scrollTop();
          var navWrap = $('#top').offset().top;
          if (y - 200 > navWrap) {
            angular.element('.to-top-scroller').show()
          } else {
            angular.element('.to-top-scroller').hide()
          }
        });

        elem.on('click', function () {
          $location.hash('top');
          $anchorScroll();
        });
      }
    }
  }
  toTopScroller.$inject = ["$location", "$anchorScroll"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('toggleResponsiveMenu', toggleResponsiveMenu);

  /** @ngInject */
  function toggleResponsiveMenu($timeout) {
    return {
      restrict: 'A',
      scope: {
        toggleResponsiveMenu: '@'
      },
      link: function (scope, elem) {
        elem.bind('click', function () {
          $timeout(function () {
            angular.element(scope.toggleResponsiveMenu).toggle();
          }, 100);
        });
      }
    }
  }
  toggleResponsiveMenu.$inject = ["$timeout"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiConversations', uiConversations);

  /** @ngInject */
  function uiConversations($modal, $rootScope, ChannelsService, ConversationService, PostFilter, SmartTags) {
    return {
      template: '<a href="" ng-click="getConversation()" ng-show="item.has_conversation"><span class="icon-chat-oval"></span> View Conversation</a>',
      replace: true,
      scope: {
        item: "=uiConversations",
        activeTag: "=selectedTagFilter"
      },
      link: function (scope, elm, attrs) {
        scope.getConversation = function () {
          var post_id = scope.item.id_str;
          var response_id = attrs.responseId;

          var channel_id = ChannelsService.getSelectedId();
          ConversationService.list_by_post(post_id, channel_id).then(function (res) {
            scope.openDialog(res, response_id, post_id);
          })
        };
        scope.openDialog = function (list, response_id, post_id) {
          var d = $modal.open({
            backdrop: true,
            keyboard: true,
            templateUrl: '/partials/conversations/convModal',
            //resolve: { item: function(){ return angular.copy(scope.item) }},
            controller: ["$scope", function ($scope) {
              $scope.posts = list;
              $scope.modal_title = 'Conversation';
              $scope.unreplied_posts = _.filter(list, function (el) {
                return el.filter_status != 'actual'
              });
              $scope.default_profile_url = "/static/assets/img/default_profile2.png";
              // Post actions
              var postStatusChanged = function (post) {
                post.is_disabled = true;
              };
              $scope.rejectPost = PostFilter.command('reject', postStatusChanged);
              $scope.starPost = PostFilter.command('star', postStatusChanged);

              $scope.$on(SmartTags.ON_POST_TAGS_REMOVED, function (event) {
                if (event.defaultPrevented != true) {
                  var tag_removed = event.targetScope.tag;
                  var all_tags = _.flatten(_.pluck($scope.unreplied_posts, 'smart_tags'));
                  var same_tag = _.find(all_tags, function (tag) {
                    return tag.id == tag_removed.id
                  })
                  if (typeof same_tag == 'undefined') {
                    if (tag_removed.id == scope.activeTag.id) {
                      //pass along the tag which was removed because we are no longer in the tag scope here
                      $rootScope.$broadcast(SmartTags.ON_POST_TAGS_REMOVED, response_id, post_id, tag_removed, true);
                      $scope.close();
                    }
                  }
                }
              });

              $scope.close = $scope.$close;

              (function killBackgroundScroll(dialog) {
                // workaround for Chrome
                if (!dialog) {
                  return;
                }

                var $body = $('body'),
                  overflowVal = 'visible',
                  scrollTop = $body.scrollTop(),
                  scrollTo = function (px) {
                    $body.scrollTop(px);
                    //$body.scrollTo(px, {duration:0});
                  };

                dialog.opened.then(function suppressScroll() {
                  $body.css({'overflow': 'hidden'});
                  setTimeout(function () {
                    scrollTo(scrollTop);
                    $body.find('.modal-backdrop').bind('click', returnScroll);

                    $scope.scrollToPost = _.find(list, function (item) {
                      return item.id_str === post_id;
                    });
                    $scope.scrollToIndex = _.indexOf(list, $scope.scrollToPost);
                  }, 0);
                });
                dialog.result.then(returnScroll);

                function returnScroll() {
                  $body.css({'overflow': overflowVal});
                  scrollTo(scrollTop);
                  $body.find('.modal-backdrop').unbind('click', returnScroll);
                }
              }(d));

            }]
          });

        }
      }
    }
  }
  uiConversations.$inject = ["$modal", "$rootScope", "ChannelsService", "ConversationService", "PostFilter", "SmartTags"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiModal', uiModal);


  /**
   *
   */
  /** @ngInject */
  function uiModal($timeout) {
    return {
      restrict: 'EAC',
      require: 'ngModel',
      link: function (scope, elm, attrs, model) {
        //helper so you don't have to type class="modal hide"
        elm.addClass('modal');
        elm.on('shown', function () {
          elm.find("[autofocus]").focus();
        });
        scope.$watch(attrs.ngModel, function (value) {
          elm.modal(value ? 'show' : 'hide');
        });
        //If bootstrap animations are enabled, listen to 'shown' and 'hidden' events
        elm.on(jQuery.support.transition && 'shown' || 'show', function () {
          $timeout(function () {
            model.$setViewValue(true);
          });
        });
        elm.on(jQuery.support.transition && 'hidden' || 'hide', function () {
          $timeout(function () {
            model.$setViewValue(false);
          });
        });
      }
    };
  }
  uiModal.$inject = ["$timeout"];
}());

(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiSelectTags2', uiSelectTags2);

  function uiSelectTags2() {
    var noFoundMessage = 'Hit Enter or Tab to add a new value';
    return {
      require: '?ngModel',
      link: function (scope, element, attrs, ngModel) {
        var sel = element.select2({
          tags: [], formatNoMatches: function (term) {
            return noFoundMessage
          }
        });
        sel.bind("change", function () {
          ngModel.$setViewValue((sel).select2("val"));
          scope.$apply();
        });

        scope.$watch(attrs.ngModel, function (newVal) {
          if (!newVal) return;
          element.select2({
            tags: newVal, formatNoMatches: function (term) {
              return noFoundMessage
            }
          });
        });
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiSlider', uiSlider);

  function uiSlider() {
      var default_config = {
        range: "max",
        min: 0,
        max: 1,
        step: 0.01
      };

      return {
        require: 'ngModel',
        link: function (scope, elm, attrs, ctrl) {
          //var config = scope.slider_config || default_config;
          var config = scope.slider_config || angular.extend({}, default_config, scope.$eval(attrs.uiSlider));
          var sliderElm = elm.slider(config, {
            slide: function (event, ui) {
              //we don't want update model onSlide
              elm.prev().val((ui.value));
            },
            stop: function (event, ui) {
              scope.$apply(function () {
                var v = config.range === true ? ui.values : ui.value;
                ctrl.$setViewValue(v);
              });
            }
          });

          scope.$watch(attrs.ngModel, function (newVal) {
            // in range slider, if newVal is invalid, ui will break, so handle most possible default values
            if (config.range === true) {
              if (!(newVal instanceof Array) || newVal.length === 0) {
                return;
              }
            }

            var sliderValue = config.range === true ? {values: newVal} : {value: newVal};
            sliderElm.slider(sliderValue);
          }, config.range === true);
        }
      };
    }
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiSmartTags2', uiSmartTags2);

  /** @ngInject */
  function uiSmartTags2($compile, $timeout, $rootScope,
                        SmartTag, SmartTags, SmartTagForm, SystemAlert, ChannelsService) {
    return {
      template: '<a href="" ng-click="showTags()" class="hide-action"><i class="icon-tag-stat-add"></i> Add Tag</a>',
      replace: true,
      scope: {
        item: "="
        //channelId  : "@"
      },

      link: function (scope, elm) {
        scope.allSmartTags = [];
        scope.isTagsShown = false;
        scope.channelId = ChannelsService.getSelectedId();
        var channel = ChannelsService.getSelected();
        var post_id = scope.item.id_str;
        var el = null;
        var el_id = "sel_" + scope.$id;
        var stags = angular.element(elm).parent().next('.stags');
        var updateAvailableTags = function () {
          return SmartTags.fetch(scope.channelId, true).then(function (all_tags) {
            all_tags = _.filter(all_tags, function (tag) {
              return channel.type === tag.direction || tag.direction == 'any'
            });
            if (scope.item.smart_tags.length > 0) {
              scope.allSmartTags = _.filter(all_tags, function (el1) {
                return !_.find(scope.item.smart_tags, function (el2) {
                  return el1.id == el2.id
                });
              });
            } else {
              scope.allSmartTags = all_tags
            }
          });
        };

        elm.on("click", function (e) {
          e.stopPropagation();
        });

        // needed to be able to click through select2 drop mask
        $(document).on('mousedown', '#select2-drop-mask', function (e) {
          $('.dropdown.open').removeClass('open');
        });

        scope.$watch('item.smart_tags.length', function (nVal, oVal) {
          if (nVal != oVal) {
            updateAvailableTags();
          }
        });
        var addSmartTag = function (added_tag) {
          SmartTag.lru_tag = added_tag[0];
          $rootScope.$broadcast(SmartTag.LRU_TAG_CHANGED);
          SmartTags.addPostTags(scope.channelId, post_id, [added_tag[0].id]).then(function (res) {
            //scope.appliedTags.push(added_tag[0]);
            scope.item.smart_tags.push(added_tag[0]);
          });
        };
        var createAndApplyTag = function (new_tag) {

          if (new_tag.length > 17) {
            SystemAlert.warn("Sorry! You only get 17 characters to name your tag.");
            return null;
          }

          var defaults = SmartTagForm.getSmartTagDefaults();
          defaults.title = new_tag;
          defaults.description = new_tag;
          defaults.channel = scope.channelId;
          //defaults.keywords    = ['_XX_'];
          var tagItem = new SmartTag();
          tagItem = angular.extend(tagItem, defaults);

          //create a new tag
          return SmartTag.update(tagItem, function (res) {
            //update the list of available tags
            scope.$root.$broadcast(SmartTag.ON_SMARTTAG_UPDATE);
            //add the new tag to the post
            addSmartTag([res.item]);
          });
        };

        var s2_settings = {
          maximumInputLength: 17,
          formatNoMatches: function () {
            return "No smart tags available"
          }
        }
        scope.showTags = function () {
          var tagsTitles = _.pluck(scope.allSmartTags, 'title')
          updateAvailableTags();
          if (el == null) {
            el = $compile("<div post-smart-tags></div>")(scope);
            stags.append(el).ready(function () {
              $timeout(function () {
                angular.element('#' + el_id).select2(s2_settings);
                angular.element('#' + el_id).select2('open');
                angular.element('#' + el_id).on("change", function (e) {
                  var added_tag = _.filter(scope.allSmartTags, function (el) {
                      return el.id == e.val
                    }
                  );
                  if (added_tag.length > 0) {
                    addSmartTag(added_tag);
                  }
                  scope.$apply();
                  stags.hide();
                  scope.isTagsShown = false;
                });

                jQuery('input.select2-input').on('keydown', function (e) {
                  var oldValue = _.contains(tagsTitles, e.target.value);
                  if (e.keyCode == 13 && !oldValue && !(/^\s*$/).test(e.target.value)) {
                    //createAndApplyTag(e.target.value.trim());
                    angular.element('#' + el_id).select2('close');
                    stags.hide();
                    scope.isTagsShown = false;
                  } else {
                    return
                  }
                });
                angular.element("#select2-drop-mask").on("mousedown", function (e) {
                  angular.element('#' + el_id).select2("close");
                  stags.hide();
                  scope.isTagsShown = false;
                });
              }, 600, false);
            });
          }
          if (scope.isTagsShown) {
            angular.element('#' + el_id).select2('close');
            stags.hide();
            scope.isTagsShown = false;

          } else {
            updateAvailableTags().then(function () {
              stags.show(0, function () {
                angular.element('#' + el_id).select2('val', '');
                //angular.element('#' + el_id).select2(s2_settings);
                angular.element('#' + el_id).select2('open');
              });
              scope.isTagsShown = true;
            })
          }
        };
      }
    };
  }
  uiSmartTags2.$inject = ["$compile", "$timeout", "$rootScope", "SmartTag", "SmartTags", "SmartTagForm", "SystemAlert", "ChannelsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiUserHistory', uiUserHistory);

  /** @ngInject */
  function uiUserHistory($modal, ChannelsService, ConversationService) {
    return {
      template: '<span>\
                        <button ng-show="item.has_history" class="btn btn-xs btn-info"\
                          ng-click="getUserProfile()"\
                          ui-jq="tooltip" title="User History">\
                        <span class="icon-chat-oval"></span></button>\
                        <button ng-hide="item.has_history" class="btn btn-xs disabled"\
                          ui-jq="tooltip" title="No customer history">\
                        <span class="icon-chat-oval"></span></button>\
                        </span>',
      replace: true,
      scope: {
        item: "="
      },
      link: function (scope, elm) {
        scope.getUserProfile = function () {
          var user = scope.item.user;
          var channel_id = ChannelsService.getSelectedId();
          ConversationService.list_by_user(channel_id, user).then(function (res) {
            scope.openDialog(_.flatten(res));
          })
        };

        scope.openDialog = function (list) {
          var d = $modal.open({
            backdrop: true,
            keyboard: true,
            backdropClick: true,
            templateUrl: '/partials/conversations/convModal',
            //resolve: { item: function(){ return angular.copy(scope.item) }},
            controller: ["$scope", function ($scope) {
              $scope.modal_title = "User History";
              $scope.posts = list;
              $scope.default_profile_url = "/static/assets/img/default_profile2.png";
              $scope.close = function (result) {
                $scope.$close(result);
              };
            }]
          });

        }
      }
    }
  }
  uiUserHistory.$inject = ["$modal", "ChannelsService", "ConversationService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services', [
      'slr.models',
      'slr.utils',
      'ngResource' // TODO: this is only for the time being. Move $http/$resource to models
    ]);
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('MetadataService', MetadataService);

  /** @ngInject */
  function MetadataService() {
    var MetadataService = {};
    var Apps = {
      'GSA': 'GSA',
      'GSE': 'GSE',
      'PRR': 'Predictive Matching',
      'JA': 'Journey Analytics',
      'NPS': 'NPS'
    };
    var intentions =
      [
        {display: 'asks', label: 'asks', enabled: false, color: '#38854d'},
        {display: 'needs', label: 'needs', enabled: false, color: '#0d89ab'},
        {display: 'likes', label: 'likes', enabled: false, color: '#ff9228'},
        {display: 'problems', label: 'problem', enabled: false, color: '#999999'},
        {display: 'checkins', label: 'checkins', enabled: false, color: '#333333'},
        {display: 'apologies', label: 'apology', enabled: false, color: '#6895d8'},
        {display: 'recommendations', label: 'recommendation', enabled: false, color: '#c26117'},
        {display: 'considerations', label: 'consideration', enabled: false, color: '#dfbc5f'},
        {display: 'discarded', label: 'discarded', enabled: false, color: '#ff0000'},
        {display: 'gratitude', label: 'gratitude', enabled: false, color: '#97b539'},
        {display: 'offers', label: 'offer', enabled: false, color: '#58cecb'},
        {display: 'other', label: 'junk', enabled: false, color: '#f5a7a2'}
      ];

    // TODO: should be merged with metadata above
    var intention_type = [

    ];

    var postStatuses =
      [
        {label: 'actionable', display: 'actionable', enabled: true},
        {label: 'actual', display: 'replied', enabled: true},
        //{ label : 'potential' , display : 'potential',  enabled : true},
        {label: 'rejected', display: 'rejected', enabled: true}
      ];

    var sentiments =
      [
        {label: 'positive', enabled: false, color: '#0DBD39'},
        {label: 'negative', enabled: false, color: '#E0351B'},
        {label: 'neutral', enabled: false, color: '#E0AB1B'}
      ];

    var event_types =
      [
        {label: 'voice', icon: 'icon-phone-voice'},
        {label: 'twitter', icon: 'icon-iw-active-circle-twitter'},
        {label: 'chat', icon: 'icon-chat-multi'},
        {label: 'web', icon: 'icon-cobrowse'},
        {label: 'webclick', icon: 'icon-cobrowse'},
        {label: 'faq', icon: 'icon-help'},
        {label: 'email', icon: 'icon-email'},
        {label: 'facebook', icon: 'icon-iw-active-circle-facebook'},
        {label: 'branch', icon: 'icon-tree-branch'},
        {label: 'nps', icon: 'icon-face-happy'}
      ];

    var defaultPathMetrics =
      [
        {label: 'Common Path', measure: 'max'}
      ];

    var message_types =
      [
        {display: 'Public messages', label: 0, enabled: true},
        {display: 'Direct messages', label: 1, enabled: true}
      ];

    var age_groups =
      [
        {
          display_name: '16 - 25',
          display: '16 - 25', label: '16 - 25', enabled: false
        },
        {
          display_name: '26 - 35',
          display: '26 - 35', label: '26 - 35', enabled: false
        },
        {
          display_name: '36 - 45',
          display: '36 - 45', label: '36 - 45', enabled: false
        },
        {
          display_name: '46 -',
          display: '46+', label: '46 -', enabled: false
        }
      ];

    var customer_statuses =
      [
        {
          display_name: 'NEW',
          display: 'NEW', label: 'NEW', enabled: false
        },
        {
          display_name: 'REGULAR',
          display: 'REGULAR', label: 'REGULAR', enabled: false
        },
        {
          display_name: 'IMPORTANT',
          display: 'IMPORTANT', label: 'IMPORTANT', enabled: false
        },
        {
          display_name: 'VIP',
          display: 'VIP', label: 'VIP', enabled: false
        }
      ];

    var agent_occupancy =
      [
        {display: '0% - 10%', label: '0% - 10%', enabled: false},
        {display: '11% - 30%', label: '11% - 30%', enabled: false},
        {display: '31% - 50%', label: '31% - 50%', enabled: false},
        {display: '51% - 100%', label: '51% - 100%', enabled: false}
      ];

    var nps = [
      {value: 'n/a', display_name: 'N/A'},
      {value: 'promoter', display_name: 'Promoters'},
      {value: 'passive', display_name: 'Passives'},
      {value: 'detractor', display_name: 'Detractors'}
    ];

    var journey_status = [
      {display_name: 'finished'},
      {display_name: 'abandoned'},
      {display_name: 'ongoing'}
    ];

    var languages = [];

    var plot_filters = [
      {type: 'sentiment', enabled: false},
      {type: 'topic', enabled: false},
      {type: 'intention', enabled: false},
      {type: 'status', enabled: false},
      {type: 'agent', enabled: false},
      {type: 'time', enabled: false},
      {type: 'segment', enabled: false},
      {type: 'industry', enabled: false},
      {type: 'Status', enabled: false},
      {type: 'location', enabled: false},
      {type: 'gender', enabled: false},
      {type: 'Mean Error', enabled: false},
      {type: 'Mean Latency', enabled: false},
      {type: 'Mean Reward', enabled: false}
    ];

    var CSVSeparators = [
      { value: '\t', text: 'TAB' },
      { value: ',', text: 'COMMA' },
    ];

    var dateFileTypes = [
      { value: 'json', text: 'JSON', extension: '.json' },
      { value: 'csv', text: 'CSV', extension: '.csv' },
    ];

    var schemaFieldTypes = [

      { value: 'boolean', id: 'boolean', text: 'Boolean' },
      { value: 'integer', id: 'integer', text: 'Numeric' }, //TODO? actual value is still 'integer'
      { value: 'list',    id: 'list', text: 'List' },
      { value: 'string',  id: 'string', text: 'String' },
      { value: 'timestamp', id: 'timestamp', text: 'Timestamp' },
      { value: 'dict',    id: 'dict', text: 'Dict' }
    ];

    var eventTypeFieldFlags = [
      { value: 'faceted', text: 'Faceted' },
      { value: 'required', text: 'Requried'},
    ];

    MetadataService.getIntentions = function () {
      return intentions;
    };

    MetadataService.getAgeGroups = function () {
      return age_groups;
    };

    MetadataService.getAgentOccupancy = function () {
      return agent_occupancy;
    };

    MetadataService.getCustomerStatuses = function () {
      return customer_statuses;
    };

    MetadataService.getJourneyStatus = function () {
      return journey_status;
    };

    MetadataService.getLanguages = function () {
      return languages;
    };

    MetadataService.getMessageTypes = function () {
      return message_types;
    };

    MetadataService.getNPS = function () {
      return nps;
    };

    MetadataService.getPlotFilters = function () {
      return plot_filters;
    };

    MetadataService.getPostStatuses = function () {
      return postStatuses;
    };

    MetadataService.getSentiments = function () {
      return sentiments;
    };
    
    MetadataService.getApps = function () {
      return Apps;      
    };

    MetadataService.getSchemaFieldTypes = function () {
      return schemaFieldTypes;
    };

    MetadataService.getBeautifiedStatus = function(entity, type) {
      if (!entity) {
        return 'N/A';
      }

      var entity_type = type && type == 'channel' ? 'Channels' : 'Schema';

      switch (entity.sync_status) {
        case 'IMPORTING':
          return (entity.load_progress < 100)
            ? 'Loading data...'
            : 'Appending data...';
          break;
        case 'SYNCING':
          return 'Applying schema...';
        case 'SYNCED':
          return 'Schema applied';
        case 'OUT_OF_SYNC':
          return entity_type + ' out of synchronization';
        case 'IN_SYNC':
          return entity_type + ' synchronized';
        default:
          return 'N/A';  
      }
    };

    MetadataService.getEventTypes = function () {
      return event_types;
    };

    MetadataService.getCSVSeparators = function() {
      return CSVSeparators;
    };

    MetadataService.getDataFileTypes = function() {
      return dateFileTypes;
    };
    
    MetadataService.getEventTypeIcon = function (eventtype) {
      var icon = 'icon-iw-active-circle-question';
      var found = _.find(event_types, {label: eventtype.toLowerCase()});
      if (found) {
        icon = found.icon;
      }
      return icon;
    };

    MetadataService.getEventTypes = function () {
      return event_types;
    };

    MetadataService.getEventTypeFieldFlags = function () {
      return eventTypeFieldFlags;
    };

    MetadataService.getDefaultPathMetrics = function () {
      return defaultPathMetrics;
    };

    MetadataService.getIntentionClass = function (intention_type) {
      var className;
      switch(intention_type) {
        case ('Asks for Something'): className = 'asks'; break;
        case ('States a Need / Want'): className = 'needs'; break;
        case ('States a Problem / Dislikes'): className = 'problem'; break;
        case ('Likes...'): className = 'likes'; break;
        case ('Offer Help'): className = 'offer'; break;
        case ('Checkin'): className = 'checkins'; break;
        case ('Gratitude'): className = 'gratitude'; break;
        case ('Apology'): className = 'apology'; break;
        case ('Recommendation'): className = 'recommendation'; break;
        case ('Junk'): className = 'junk'; break;
        default : className = 'junk';
      }
      return className;
    };

    MetadataService.processDataType = function (d) {
      switch (d.toLowerCase()) {
        case('string'):
          return 'Label'; break;
        case('integer'):case('double'):case('timestamp'):
          return 'Numeric'; break;
        case('boolean'):
          return 'Boolean'; break;
        default:
          return 'Numeric'; break;
      }
    };


    return MetadataService;
  }
})();

(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('FilterService', FilterService);

  // TODO: this requires refactoring, in case of some methods are deprecated, or do not make sense, or duplicated
  /**
   * Global filter factory
   * has the same behaviour per each page
   */
  /** @ngInject */
  function FilterService($rootScope, MetadataService) {
    var partial = _.partial,
      allSelected = {
        intentions: true,
        age_groups: true,
        customer_statuses: true,
        agent_occupancy: true,
        message_types: true,
        statuses: true,
        sentiments: true,
        languages: true,
        nps: true,
        journey_status: true
      },

      facetOptions = {
        intentions: MetadataService.getIntentions(),
        age_groups: MetadataService.getAgeGroups(),
        customer_statuses: MetadataService.getCustomerStatuses(),
        agent_occupancy: MetadataService.getAgentOccupancy(),
        statuses: MetadataService.getPostStatuses(),
        sentiments: MetadataService.getSentiments(),
        message_types: MetadataService.getMessageTypes(),
        languages: MetadataService.getLanguages(),
        nps: MetadataService.getNPS(),
        journey_status: MetadataService.getJourneyStatus()
      };

    var dateRangeObj = {
      from: Date.today(),                //(0).days().fromNow(),
      to: Date.today().add({days: 1})                 //(1).days().fromNow()
    };

    var dateRange = {
      from: dateRangeObj.from.toString("MM/dd/yyyy"),
      to: dateRangeObj.to.toString("MM/dd/yyyy")
    };

    // TODO: change "new Date" to momentjs ?
    var today = new Date(dateRangeObj.from),
      this_week_start = Date.mon() <= Date.today() ? Date.mon() : Date.sun().add(-6).days(),
      this_month_start = new Date(dateRangeObj.from).moveToFirstDayOfMonth(),

      tomorrow = new Date(today).add({days: 1}),
      this_week_end = new Date(this_week_start).add({weeks: 1}),
      this_month_end = new Date(this_month_start).add({months: 1}),

      yesterday = new Date(today).add({days: -1}),
      last_week_start = new Date(this_week_start).add({weeks: -1}),
      last_week_end = new Date(last_week_start).add({weeks: 1}),
      last_month_start = new Date(this_month_start).add({months: -1}),
      last_month_end = new Date(last_month_start).add({months: 1}),

      before_last_month_start = new Date(last_month_start).add({months: -1}),
      before_last_month_end = new Date(before_last_month_start).add({months: 1}),

      demo_range_start = before_last_month_start,
      demo_range_end = new Date();

    var monthNames = ["January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"];
    //the logic behind 'to' the server expects is the end date -1 day
    var dateRangeButtons = [
      //{ alias: 'demo_date_range', type : 'Demo Date Range', from: demo_range_start, to: demo_range_end,  level: 'day', topic_level: 'day', graph_level: 'day', enabled : false },
      {
        alias: 'today',
        type: 'Today',
        from: today,
        to: new Date(today).add({days: 1}),
        level: 'hour',
        topic_level: 'day',
        graph_level: 'hour',
        enabled: true
      },
      {
        alias: 'yesterday',
        type: 'Yesterday',
        from: yesterday,
        to: today,
        level: 'hour',
        topic_level: 'day',
        graph_level: 'hour',
        enabled: false
      },
      {
        alias: 'this_week',
        type: 'This Week',
        from: this_week_start,
        to: this_week_end,
        level: 'day',
        topic_level: 'day',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'last_week',
        type: 'Last Week',
        from: last_week_start,
        to: last_week_end,
        level: 'day',
        topic_level: 'day',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'this_month',
        type: 'This Month',
        from: this_month_start,
        to: this_month_end,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'last_month',
        type: monthNames[last_month_start.getMonth()],
        from: last_month_start,
        to: last_month_end,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'before_last_month',
        type: monthNames[before_last_month_start.getMonth()],
        from: before_last_month_start,
        to: before_last_month_end,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'past_3_months',
        type: 'Past 3 Months',
        from: new Date(this_month_start).add({months: -2}),
        to: today,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'past_3_year',
        type: 'Past 3 years',
        from: new Date(this_month_start).add({years: -3}),
        to: today,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      }
    ];

    /* Private methods */

    var getSelected = function (list, label) {
      var field = label ? label : 'label';
      return _.pluck(_.filter(list,
        function (el) {
          return el.enabled == true
        }
      ), field);
    };

    var getEnabled = function (list) {
      return _.filter(list, function (el) {
        return el.enabled == true
      });
    };

    var setFacetFilters = function (selected, all, event) {
      _.each(all, function (el) {
        if (selected.length > 0)
          el.enabled = _.some(selected, function (sel) {
            return sel == el.label
          });
        else
          el.enabled = false
      });
      $rootScope.$broadcast(event);
      return all;
    };

    var removeSelectedFilter = function (filter, facet, event, field) {
      field = field ? field : 'label';
      var removed = _.find(facet, function (el) {
        return el[field] == filter
      });
      if (removed)
        removed.enabled = false;
      $rootScope.$broadcast(event);
    };

    var getFacetParams = function (facet) {
      var isAll = isAllSelected(facet),
        options = getFacetOptions(facet);
      if (isAll) {
        return _.pluck(options, 'label');
      } else {
        return getSelected(options);
      }
    };

    /* End of Private methods */
    var LANGUAGES = 'languages',
      INTENTIONS = 'intentions',
      AGE_GROUPS = 'age_groups',
      CUSTOMER_STATUSES = 'customer_statuses',
      AGENT_OCCUPANCY = 'agent_occupancy',
      SENTIMENTS = 'sentiments',
      STATUSES = 'statuses',
      MESSAGE_TYPES = 'message_types',
      NPS = 'nps',
      JOURNEY_STATUS = 'journey_status';

    var FilterService = {
      CHANGED: 'filter_changed',
      DATE_RANGE_CHANGED: 'date_range_changed',
      INTENTIONS_CHANGED: 'intentions_changed',
      AGE_GROUPS_CHANGED: 'age_groups_changed',
      CUSTOMER_STATUSES_CHANGED: 'customer_statuses_changed',
      AGENT_OCCUPANCY_CHANGED: 'agent_occupancy_changed',
      MESSAGE_TYPE_CHANGED: 'message_type_changed',
      POST_STATUSES_CHANGED: 'post_statuses_changed',
      SENTIMENTS_CHANGED: 'sentiments_changed',
      LANGUAGES_CHANGED: 'languages_changed',

      setSelectedIntentions: partial(setSelected, INTENTIONS),
      //setSelectedAgeGroups      : partial(setSelected, AGE_GROUPS),
      setSelectedLanguages: partial(setSelected, LANGUAGES),
      setSelectedSentiments: partial(setSelected, SENTIMENTS),
      setSelectedStatuses: partial(setSelected, STATUSES),
      setDateRange: setDateRange,
      setDateRangeByAlias: setDateRangeByAlias,
      getUTCDate: getUTCDate,
      getDateRangeButtons: getDateRangeButtons,
      getDateRange: getDateRange,
      update: update,
      updateDateRange: updateDateRange,
      getDateRangeObj: getDateRangeObj,
      getSelectedDateRangeType: getSelectedDateRangeType,
      getSelectedDateRangeAlias: getSelectedDateRangeAlias,
      getDateRangeByAlias: getDateRangeByAlias,
      getSelectedDateRangeName: getSelectedDateRangeName,
      getSelectedLevel: getSelectedLevel,
      getSelectedGraphLevel: getSelectedGraphLevel,
      getSelectedTopicLevel: getSelectedTopicLevel,
      toUTCDate: toUTCDate,
      getPostsDateRangeByPoint: getPostsDateRangeByPoint,
      getMessageTypes: partial(getFacetOptions, MESSAGE_TYPES),
      getIntentions: partial(getFacetOptions, INTENTIONS),
      getAgeGroups: partial(getFacetOptions, AGE_GROUPS),
      getCustomerStatuses: partial(getFacetOptions, CUSTOMER_STATUSES),
      getAgentOccupancy: partial(getFacetOptions, AGENT_OCCUPANCY),
      getNPSOptions: partial(getFacetOptions, NPS),
      getJourneyStatus: partial(getFacetOptions, JOURNEY_STATUS),
      getSentiments: partial(getFacetOptions, SENTIMENTS),
      isAllSelected: isAllSelected,
      facetsAllSelected: facetsAllSelected,
      isAllIntentionsSelected: partial(isAllSelected, INTENTIONS),
      //isAllAgeGroupsSelected    : partial(isAllSelected, AGE_GROUPS),
      isAllMessageTypesSelected: partial(isAllSelected, MESSAGE_TYPES),
      isAllStatusesSelected: partial(isAllSelected, STATUSES),
      isAllSentimentsSelected: partial(isAllSelected, SENTIMENTS),
      isAllLanguagesSelected: partial(isAllSelected, LANGUAGES),
      setIntentions: partial(setFacetFiltersCur, INTENTIONS),
      setAgeGroups: partial(setFacetFiltersCur, AGE_GROUPS),
      setCustomerStatuses: partial(setFacetFiltersCur, CUSTOMER_STATUSES),
      setAgentOccupancy: partial(setFacetFiltersCur, AGENT_OCCUPANCY),
      setMessageTypes: partial(setFacetFiltersCur, MESSAGE_TYPES),
      setStatuses: partial(setFacetFiltersCur, STATUSES),
      setSentiments: partial(setFacetFiltersCur, SENTIMENTS),
      updatePostStatuses: partial(updateEvent, STATUSES),
      updateIntentions: partial(updateEvent, INTENTIONS),
      updateAgeGroups: partial(updateEvent, AGE_GROUPS),
      updateCustomerStatuses: partial(updateEvent, CUSTOMER_STATUSES),
      updateAgentOccupancy: partial(updateEvent, AGENT_OCCUPANCY),
      updateMessageTypes: partial(updateEvent, MESSAGE_TYPES),
      updateSentiments: partial(updateEvent, SENTIMENTS),
      setIsAllMessageTypes: partial(setIsAll, MESSAGE_TYPES),
      setIsAllIntentions: partial(setIsAll, INTENTIONS),
      setIsAllAgeGroups: partial(setIsAll, AGE_GROUPS),
      setIsAllCustomerStatuses: partial(setIsAll, CUSTOMER_STATUSES),
      setIsAllAgentOccupancy: partial(setIsAll, AGENT_OCCUPANCY),
      setIsAllStatuses: partial(setIsAll, STATUSES),
      setIsAllSentiments: partial(setIsAll, SENTIMENTS),
      setIsAllLanguages: partial(setIsAll, LANGUAGES),
      removeIntention: removeIntention,
      removeAgeGroup: removeAgeGroup,
      removeCustomerStatus: removeCustomerStatus,
      removeAgentOccupancy: removeAgentOccupancy,
      removeStatus: removeStatus,
      removeSentiment: removeSentiment,
      getPostStatuses: partial(getFacetOptions, STATUSES),
      getSelectedMessageTypes: partial(getSelectedCur, MESSAGE_TYPES, 'display'),
      getSelectedIntentions: partial(getSelectedCur, INTENTIONS, 'display'),
      getSelectedAgeGroups: partial(getSelectedCur, AGE_GROUPS, 'display'),
      getSelectedCustomerStatuses: partial(getSelectedCur, CUSTOMER_STATUSES, 'display'),
      getSelectedAgentOccupancy: partial(getSelectedCur, AGENT_OCCUPANCY, 'display'),
      getSelectedSentiments: partial(getSelectedCur, SENTIMENTS),
      getMessageTypesParams: partial(getFacetParams, MESSAGE_TYPES),
      getLanguagesParams: partial(getFacetParams, LANGUAGES),
      getIntentionsParams: partial(getFacetParams, INTENTIONS),
      getAgeGroupsParams: partial(getFacetParams, AGE_GROUPS),
      getCustomerStatusesParams: partial(getFacetParams, CUSTOMER_STATUSES),
      getAgentOccupancyParams: partial(getFacetParams, AGENT_OCCUPANCY),
      getSentimentsParams: partial(getFacetParams, SENTIMENTS),
      getSelectedPostStatuses: getSelectedPostStatuses,
      getPostStatusesParams: partial(getFacetParams, STATUSES),
      initLanguages: initLanguages,
      getLanguages: partial(getFacetOptions, LANGUAGES),
      setLanguages: partial(setFacetFiltersCur, LANGUAGES),
      updateLanguages: partial(updateEvent, LANGUAGES),
      getSelectedLanguages: partial(getSelectedCur, LANGUAGES, 'title'),
      removeLanguage: removeLanguage
    };
    return FilterService;

    /* Public Methods (exposed via FilterService object) - use function declaration to hoist them */

    function setSelected(facet, labels) {
      var options = getFacetOptions(facet);
      _.each(options, function (el) {
        el.enabled = false;
        _.each(labels, function (label) {
          if (label == el.label) {
            el.enabled = true;
          }
        })
      });

      updateEvent(facet);
    }

    function setDateRange(range) {
      angular.forEach(dateRangeButtons, function (val, key) {
        if (val.type === range) {
          val.enabled = true;
          dateRangeObj.to = val.to;
          dateRangeObj.from = val.from;
          //console.log(dateRangeButtons);
        } else {
          val.enabled = false;
        }
      });
      updateDateRange(dateRangeObj);
      $rootScope.$broadcast(FilterService.DATE_RANGE_CHANGED);
    }

    function setDateRangeByAlias(alias) {
      var selected = getDateRangeByAlias(alias);
      setDateRange(selected.type);
    }

    function getUTCDate(date) {
      return new Date(date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
        date.getUTCHours(),
        date.getUTCMinutes(),
        date.getUTCSeconds());
    }

    function update(obj) {
      $rootScope.$broadcast(FilterService.CHANGED, obj);
    }

    function getDateRangeButtons(types) {
      var ids = {};
      _.each(types, function (type) {
        ids[type] = true;
      });
      var filteredDRbuttons = _.filter(dateRangeButtons, function (val) {
        return !ids[val.type];
      }, types);
      //console.log(filteredDRbuttons);
      return filteredDRbuttons;
    }

    function getDateRange(params) {
      var storedAllias = amplify.store('current_date_alias') || getSelectedDateRangeAlias();
      var datesByAlias = getDateRangeByAlias(storedAllias);
      //dateRange.from = (datesByAlias.from).toString("MM/dd/yyyy");
      //dateRange.to   = (datesByAlias.to).toString("MM/dd/yyyy");
      if (params && params.local) {
        // treat dateRange as local, and covert to UTC equivalent before sending request to server
        // useful when server can handle 'any'date range query (unlike aggregated posts data page which needs UTC days),
        // and UI (eg: setting pages) will format the dates in local timezone
        dateRange.from = moment.utc(dateRange.from).format('YYYY-MM-DD HH:mm:SS');
        dateRange.to = moment.utc(dateRange.to).format('YYYY-MM-DD HH:mm:SS');
      }
      return dateRange;
    }

    function updateDateRange(dates) {
      dateRangeObj = dates;
      dateRange.from = new Date(dates.from).toString("MM/dd/yyyy");
      dateRange.to = new Date(dates.to).toString("MM/dd/yyyy");

      angular.forEach(dateRangeButtons, function (val, key) {
        if (new Date(val.from).toString('MM/dd/yyyy') === dateRange.from &&
          new Date(val.to).toString('MM/dd/yyyy') === dateRange.to) {
          val.enabled = true;
        } else {
          val.enabled = false;
        }
      });
      $rootScope.$broadcast(FilterService.DATE_RANGE_CHANGED);
    }

    function getDateRangeObj() {
      return dateRangeObj;
    }

    function getSelectedDateRangeType() {
      return getEnabled(getDateRangeButtons())[0].type;
    }

    function getSelectedDateRangeAlias() {
      return getEnabled(getDateRangeButtons())[0].alias;
    }

    function getDateRangeByAlias(alias) {
      return _.find(dateRangeButtons, function (btn) {
        return btn.alias == alias
      })
    }

    function getSelectedDateRangeName() {
      var date = getEnabled(getDateRangeButtons())[0];
      var from = dateFormat(date.from, "mmm dd");
      var to = dateFormat(date.to, "mmm dd");
      var range = from + " - " + to;
      return range;
    }

    function getSelectedLevel() {
      return getEnabled(getDateRangeButtons())[0]['level'];
    }

    function getSelectedGraphLevel() {
      return getEnabled(getDateRangeButtons())[0]['graph_level'];
    }

    function getSelectedTopicLevel() {
      return getEnabled(getDateRangeButtons())[0]['topic_level'];
    }

    function toUTCDate(date, format) {
      var _date = new Date(date);
      var timestamp = Date.UTC(_date.getFullYear(), _date.getMonth(), _date.getDate());
      var local_date = new Date(timestamp);
      return format ? dateFormat(local_date, "yyyy-mm-dd HH:MM:ss", true) : timestamp;
    }

    function getPostsDateRangeByPoint(timePoint, plot_by, level) {
      level = level ? level : getSelectedLevel();
      var fromDate = new Date(timePoint),
        toDate;
      if (plot_by == 'time') {
        if (level == 'hour') {
          toDate = new Date(fromDate).add({hours: 1});
        } else if (level == 'day' || level == 'month') {
          fromDate = new Date(fromDate);
          toDate = new Date(fromDate).add({days: 1});
        }
      }
      toDate.add({seconds: -1});
      return {from: fromDate, to: toDate};
    }

    function ensureFacetIn(facet, obj) {
      if (!obj.hasOwnProperty(facet)) {
        throw Error("Unknown facet: " + facet);
      }
    }

    function isAllSelected(facet) {
      ensureFacetIn(facet, allSelected);
      return allSelected[facet];
    }

    function facetsAllSelected() {
      var res = [];
      for (var facet in allSelected) {
        if (allSelected.hasOwnProperty(facet) && allSelected[facet] === true) {
          res.push(facet);
        }
      }
      return res;
    }

    function setIsAll(facet, selected) {
      ensureFacetIn(facet, allSelected);
      allSelected[facet] = selected;
    }

    function getFacetOptions(facet) {
      ensureFacetIn(facet, facetOptions);
      var options = facetOptions[facet];
      if (facet == LANGUAGES || facet == STATUSES) {
        return options;
      } else {
        return _.sortBy(options, function (el) {
          return el.label;
        });
      }
    }

    function getEvent(facet) {
      var events = {
        intentions: FilterService.INTENTIONS_CHANGED,
        age_groups: FilterService.AGE_GROUPS_CHANGED,
        customer_statuses: FilterService.CUSTOMER_STATUSES_CHANGED,
        agent_occupancy: FilterService.AGENT_OCCUPANCY_CHANGED,
        message_types: FilterService.MESSAGE_TYPE_CHANGED,
        statuses: FilterService.POST_STATUSES_CHANGED,
        sentiments: FilterService.SENTIMENTS_CHANGED,
        languages: FilterService.LANGUAGES_CHANGED
      };
      return events[facet];
    }

    function setFacetFiltersCur(facet, list) {
      var all = getFacetOptions(facet),
        event = getEvent(facet);
      return setFacetFilters(list, all, event);
    }


    function updateEvent(facet) {
      var event = getEvent(facet);
      $rootScope.$broadcast(event);
    }

    function removeIntention(item) {
      removeSelectedFilter(item, FilterService.getIntentions(), FilterService.INTENTIONS_CHANGED, 'display');
    }

    function removeAgeGroup(item) {
      removeSelectedFilter(item, FilterService.getAgeGroups(), FilterService.AGE_GROUPS_CHANGED, 'display');
    }

    function removeCustomerStatus(item) {
      removeSelectedFilter(item, FilterService.getCustomerStatuses(), FilterService.CUSTOMER_STATUSES_CHANGED, 'display');
    }

    function removeAgentOccupancy(item) {
      removeSelectedFilter(item, FilterService.getAgentOccupancy(), FilterService.AGENT_OCCUPANCY_CHANGED, 'display');
    }

    function removeStatus(item) {
      //removeSelectedFilter(item, getPostStatuses(), POST_STATUSES_CHANGED);
      var removed = _.find(FilterService.getPostStatuses(), function (el) {
        //return el.label == item
        return el.display == item.display
      });
      if (removed)
        removed.enabled = false;
      $rootScope.$broadcast(FilterService.POST_STATUSES_CHANGED);
    }

    function removeSentiment(item) {
      removeSelectedFilter(item, FilterService.getSentiments(), FilterService.SENTIMENTS_CHANGED);
    }

    function getSelectedCur(facet, label) {
      var all = getFacetOptions(facet);
      return getSelected(all, label);
    }

    function getSelectedPostStatuses(returnItems) {
      var wrapper = returnItems ? getEnabled : getSelected;
      return wrapper(getFacetOptions(STATUSES));
    }

    function initLanguages(langs) {
      var languages = _.each(langs,
        function (el) {
          return _.defaults(el, {enabled: false, label: el.title});
        });
      facetOptions.languages = languages;
      return languages;
    }

    function removeLanguage(item) {
      removeSelectedFilter(item, FilterService.getLanguages(), FilterService.LANGUAGES_CHANGED, 'title');
    }
  }
  FilterService.$inject = ["$rootScope", "MetadataService"];
})();
(function () {
    'use strict';

    // TODO: Distribute to single services, and check on relevance
    angular
        .module('slr.services')
        .factory('StaffUsersService', StaffUsersService)
        .factory('AccountsService', AccountsService)
        .factory('AccountHelper', AccountHelper)
        .factory('ConfigureAccount', ConfigureAccount);

    /** @ngInject */
    function StaffUsersService($resource) {
        var resource = function makeResource(url, defaultParams, methods) {
            return $resource(url, defaultParams||{}, methods||{});
        };
        var r = resource('/users/staff/json', {}, {
            query: { method:'GET', isArray:false}
        });
        return r
    }
    StaffUsersService.$inject = ["$resource"];

    /** @ngInject */
    function AccountsService($resource, $rootScope, ConfigureAccount) {
        var state = {
                list: [],
                current: null
            },
            service = {
                ACCOUNTS_EVENT: 'AccountsServiceEvent',
                getList: function() {
                    return state.list;
                },
                getCurrent: function() {
                    return state.current;
                },
                getCompactAccount: function() {
                    // Fetch minimum fields for dashboard use
                    var account = state.current;
                    var fields = ['id', 'name', 'selected_app', 'available_apps', 'configured_apps'];
                    if (account) {
                        return _.pick(account, fields);
                    } else {
                        return null;
                    }
                },
                switchAccountId: function(accountId, cb) {
                    //console.log(accountId);
                    if (!accountId) return;
                    var account = _.find(state.list, function(acc) { return acc.id === accountId; });
                    if (account) {
                        return this.switchAccount(account, cb);
                    }
                },
                switchAccount: function(account, cb) {
                    if (account && !account.is_current) {
                        ConfigureAccount.save({}, {account_id: account.id}, cb).$promise.then(function(){
                            _.forEach(state.list, function(acc){
                                acc.is_current = acc.id === account.id;
                                if (acc.is_current) {
                                    state.current = acc;
                                }
                            });
                            notify();
                        });
                    }
                }
            };

        function notify(params) {
            $rootScope.$emit(service.ACCOUNTS_EVENT, params);
            return params;
        }

        var AccountsResource = $resource('/accounts/:acct/json', {}, {
            query: {method:'GET', isArray:false},
            update:{method:'PUT', isArray:false},
            noAccount: {method: 'GET', params: {acct: 'no_account'}}
        });

        angular.extend(service, AccountsResource);
        service.query = function() {
            var r = AccountsResource.query.apply(AccountsResource, arguments);
            r.$promise.then(onResult);
            function onResult (res) {
                state.list = res.data;
                state.current = _.find(state.list, function(item) {return item.is_current;});
                notify();
                return res;
            }

            return r;
        };
        ['update', 'delete', 'save'].forEach(function(action){
            var originalRequest = service[action],
                wrappedRequest = function() {
                    var r = originalRequest.apply(service, arguments);
                    r.$promise.then(notify);
                    return r;
                };
            service[action] = wrappedRequest;
        });

        function findById (acc) {
            return _.find(state.list, function(a){return a.id === acc.id;});
        }

        service.accountUpdate = function(account, action) {
            if (!account || !account.id) {
                return;
            }
            var exists = findById(account);
            if (!exists) {
                // account created
                state.list.push(account);
            } else if (action == 'delete') {
                state.list.splice(state.list.indexOf(exists), 1);
            } else {
                // account updated
                angular.extend(exists, account);
            }
            notify();
        };

        return service;
    }
    AccountsService.$inject = ["$resource", "$rootScope", "ConfigureAccount"];

    /** @ngInject */
    function AccountHelper(FilterService) {
        var toOpt = function(v) {return {label: v, value: v}},
            accountTypeOptions = _.map([
                "Angel", "Native", "GSE", "HootSuite", "Salesforce", "Skunkworks", "OmniChannel"
            ], toOpt);

        return {
            // Datepicker options
            options: {
                end_date: {dateFormat:'mm/dd/yy',
                    formatDate:'mm/dd/yy',
                    minDate:new Date(+new Date()+24*60*60*1000)}
            },
            accountTypeOptions: accountTypeOptions,
            isExpired: function (account) {
                return account && account.end_date && (FilterService.getUTCDate(new Date(account.end_date)) < FilterService.getUTCDate(new Date()));
            }
        }
    }
    AccountHelper.$inject = ["FilterService"];


    /** @ngInject */
    function ConfigureAccount($resource) {
        var AccountUpdateService = $resource('/configure/account_update/json', {}, {
                fetch: { method:'GET', isArray:false },
                update: { method:'POST', isArray:false }
            }),
            ConfigureAccountService = $resource('/configure/account/json'),
            ConfigureAccountUsers = $resource('/configure/account/userslist'),
            ConfigureAccountRemove = $resource('/configure/accounts/remove');

        return {
            fetch: AccountUpdateService.fetch,
            update: AccountUpdateService.update,
            save: ConfigureAccountService.save,
            removeUser: ConfigureAccountRemove.save,
            getUsers: ConfigureAccountUsers.get
        }
    }
    ConfigureAccount.$inject = ["$resource"];;
})();

(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('AgentsService', AgentsService);

  /** @ngInject */
  function AgentsService($rootScope, $resource, ChannelsService) {
    var agents = [],
      all_agents_selected = true;
    var AgentsService = $resource('/configure/agents/json', {}, {
      fetch: {method: 'GET', isArray: false}
    });

    AgentsService.ON_AGENTS_LOADED = 'on_agents_load';
    AgentsService.ON_AGENTS_CHANGED = 'on_agents_change';

    AgentsService.colors = ['#159d00', '#8eb000',
      '#bfb800', '#bf9200',
      '#bf6c00', '#0a67cf',
      '#0acbcf', '#23d30a',
      '#bfeb0c', '#fff70d',
      '#ffc60d', '#ff960d',
      '#ff5d0d', '#f70c1a',
      '#d60b99', '#7c0acf',
      '#180acf', '#006699',
      '#009999', '#009900',
      '#99cc00', '#cccc00',
      '#cc9900', '#cc6600',
      '#cc3300', '#cc0000',
      '#990066', '#660099',
      '#000099'];

    AgentsService.fetchAgents = function () {
      AgentsService.fetch({channel_id: ChannelsService.getSelectedId()}, function (res) {
        //return all elements set to default value - enabled:true
        //we need colors be assigned and preserved for each agent
        agents = _.map(res.list, function (el, index) {
          var label = el.display_name;
          if (label.indexOf('@') != -1) {
            label = label.substr(0, label.indexOf('@'));
          }
          var i = index == AgentsService.colors.length ? 0 : index;
          return _.defaults(el, {label: label, enabled: false, color: AgentsService.colors[i]})
        });
        $rootScope.$broadcast(AgentsService.ON_AGENTS_LOADED);
      });
    };

    AgentsService.setIsAllSelected = function (all) {
      all_agents_selected = all;
    };
    AgentsService.isAllSelected = function () {
      return all_agents_selected;
    };

    AgentsService.setChangedByIds = function (ids) {
      var changed = _.map(agents, function (el) {
        if (_.indexOf(ids, el.agent_id) != -1) {
          el.enabled = true
        }
        return el
      });
      AgentsService.setChanged(changed);
    };

    AgentsService.setChanged = function (selected) {
      agents = selected;
      $rootScope.$broadcast(AgentsService.ON_AGENTS_CHANGED);
    };
    AgentsService.getAll = function () {
      return agents;
    };
    AgentsService.setAll = function (all) {
      if (all) {
        _.each(agents, function (el) {
          el.enabled = true
        });
      } else {
        _.each(agents, function (el, idx) {
          el.enabled = false
        });
      }
      $rootScope.$broadcast(AgentsService.ON_AGENTS_ALL_CHANGED); // TODO:?
    };

    AgentsService.removeAgent = function (id) {
      var removed = _.find(AgentsService.getAll(), function (el) {
        return el.agent_id === id
      });
      if (removed)
        removed.enabled = false;
      $rootScope.$broadcast(AgentsService.ON_AGENTS_CHANGED);
    };

    AgentsService.getSelected = function () {
      var selected = _.filter(agents, function (el) {
        return el.enabled == true
      });
      return _.pluck(selected, 'agent_id');
    };

    AgentsService.getSelectedTags = function () {
      return _.filter(agents, function (el) {
        return el.enabled == true
      });
    };

    AgentsService.getParams = function () {
      // we return empty list for all agents
      // because there may be some agents that were deleted
      // they are not shown in selection, but posts from them need to be queried
      if (AgentsService.isAllSelected()) {
        return [];
      } else {
        return AgentsService.getSelected();
      }
    };

    AgentsService.getAgentId = function (name) {
      var agent = _.find(agents, function (el) {
        return el.display_name == name
      });
      if (agent != undefined) {
        return agent.agent_id;
      } else {
        return null;
      }

    };

    AgentsService.getLabel = function (agentId) {
      var agent = _.find(AgentsService.getAll(), function (a) {
        return a.agent_id === agentId;
      });
      return agent && agent.label || '';
    };

    AgentsService.setAgents = function (names) {
      _.each(agents, function (agent) {
        agent.enabled = names.indexOf(agent.display_name) > -1;
      });
    };

    return AgentsService;

  }
  AgentsService.$inject = ["$rootScope", "$resource", "ChannelsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('AppStore', AppStore);

  /** @ngInject */
  function AppStore($rootScope, ChannelsService) {
    var AppStore = {};
    AppStore.read = function (settings) {
      return amplify.store(settings)
    };
    AppStore.store = function (name, obj) {
      amplify.store(name, obj, {expires: 86400000})
    };
    $rootScope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
      var channel = ChannelsService.getSelected();
      if (channel.parent_id) {
        AppStore.store('service_channel', channel);
      }
      AppStore.store('common_channel', channel);
    });
    return AppStore;
  }
  AppStore.$inject = ["$rootScope", "ChannelsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('ChannelsService', ChannelsService);

  /** @ngInject */
  function ChannelsService($rootScope, $q, ChannelsRest) {
    var _ChannelsRest = new ChannelsRest();
    var ChannelsService = {};

    var channels = [];
    var selected_channel = null;

    ChannelsService.ON_CHANNELS_LOADED = 'on_channels_load';
    ChannelsService.ON_CHANNELS_FAILED = 'on_channels_load_fail';
    ChannelsService.ON_CHANNELS_SELECTED = 'on_channels_selected';
    ChannelsService.ON_BOOKMARK_LOADED = 'on_bookmark_loaded';

    ChannelsService.load = function (type, serviced_only, parent_names) {
      _ChannelsRest.loadChannelsByType({
        type: type,
        serviced_only: serviced_only,
        parent_names: parent_names
      }).success(function (res) {
        channels = res.list;
        selected_channel = res.list[0];
        $rootScope.$broadcast(ChannelsService.ON_CHANNELS_LOADED, res);
      })
        .error(function onError(res) {
          $rootScope.$broadcast(ChannelsService.ON_CHANNELS_FAILED, res);
        });
    };

    // same as above only return promise object here
    ChannelsService.getAll = function (type, serviced_only, parent_names) {
      var deferred = $q.defer();
      var params = {
        type: type,
        serviced_only: serviced_only,
        parent_names: parent_names
      };
      _ChannelsRest.loadChannelsByType(params)
        .success(function (res) {
          channels = res.list;
          selected_channel = selected_channel ? selected_channel : res.list[0];
          deferred.resolve(channels);
        });
      
      return deferred.promise;
    };

    ChannelsService.getList = function () {
      return channels;
    };

    ChannelsService.setDefault = function (channel) {
      _ChannelsRest.setSelected(channel);
    };

    ChannelsService.setSelected = function (channel) {
      selected_channel = channel;
      $rootScope.$broadcast(ChannelsService.ON_CHANNELS_SELECTED);
    };

    ChannelsService.getSelected = function () {
      return selected_channel;
    };

    ChannelsService.getSelectedId = function () {
      return selected_channel ? selected_channel.id : null;
    };

    ChannelsService.getType = function () {
      return selected_channel.type;
    };

    return ChannelsService;
  }
  ChannelsService.$inject = ["$rootScope", "$q", "ChannelsRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory("TopicsCloud", TopicsCloud)
    .factory("Topics", Topics)
    .factory("MyTopics", MyTopics)
    .factory('TopicCloudMixin', TopicCloudMixin);

  /** @ngInject */
  function TopicsCloud(Topics) {
    var TopicsCloud = {
      getTopicSize: function (count, type) {
        var fontMin = 12,
          fontMax = 40;
        var size = count == Topics.count.min ? fontMin
          : (count / Topics.count.max) * (fontMax - fontMin) + fontMin;
        var sizelog = count == Topics.count.min ? fontMin
          : (Math.log(count) / Math.log(Topics.count.max)) * (fontMax - fontMin) + fontMin;
        var styles = {log: {'font-size': sizelog + 'px'}, linear: {'font-size': size + 'px'}};
        return styles;
      }
    };
    return TopicsCloud;
  }
  TopicsCloud.$inject = ["Topics"];

  /** @ngInject */
  function Topics($http, $filter, MyTopics) {
    var url = '/hot-topics/json';
    var Topics = {
      count: {
        min: null,
        max: null
      },
      search: function (term, params) {
        var punks = [];
        var promise = $http({
          method: 'POST',
          url: url,
          data: params
        }).then(function (res) {
          punks = res.data.list;
          if (term.topic_count > 0) {
            // append topics list with parent topic as leaf
            var leaf = {
              topic: term.topic,
              enabled: false,
              term_count: term.topic_count,
              topic_count: term.topic_count
            };
            punks.push(leaf);
          }
          return MyTopics.testSelection(_.map(punks, function (el) {
            el.level = term.level + 1;
            el.parent = term.parent;
            return el
          }));

        });
        return promise;
      },
      fetch: function (params, limit) {
        var promise = $http({
          method: 'POST',
          url: url,
          data: params
        }).then(function (res) {
          var data = limit ? $filter('limitTo')(res.data.list, limit) : res.data.list;
          var topics = MyTopics.testSelection(_.map(data, function (el) {
            el.level = 0;
            el.parent = el.topic;
            return el
          }));
          //store max,min counts
          Topics.count.max = _.max(topics, function (topic) {
            return topic.term_count
          })['term_count'];
          Topics.count.min = _.min(topics, function (topic) {
            return topic.term_count
          })['term_count'];
          return topics;
        });
        return promise;
      }
    };
    return Topics
  }
  Topics.$inject = ["$http", "$filter", "MyTopics"];

  /** @ngInject */
  function MyTopics($rootScope, $resource) {
    var MyTopics = $resource('topics/json', {}, {
      fetch_count: {method: 'POST', isArray: false}
    });

    MyTopics.ON_TOPICS_CHANGE = 'on_topics_change';

    var my_topics = [];
    var selectedTopicsLookup = {};
    var updateLookup = function () {
      selectedTopicsLookup = {};
      angular.forEach(my_topics, function (val) {
        selectedTopicsLookup[topicHash(val)] = true;
      });
    };

    var get_topic_type = function (el) {
      if (el.hasOwnProperty('term_count')) {
        return (el.term_count === el.topic_count ? "leaf" : "node");
      } else if (el.hasOwnProperty('topic_type')) {
        return el.topic_type;
      }
    };

    var topicHash = function (item) {
      return item.topic + ':' + get_topic_type(item);
    };

    var hasTerm = function (item) {
      return selectedTopicsLookup.hasOwnProperty(topicHash(item));
    };

    var topicsChanged = function () {
      updateLookup();
      $rootScope.$broadcast(MyTopics.ON_TOPICS_CHANGE);
    };

    MyTopics.purge = function () {
      my_topics = [];
      topicsChanged();
      return my_topics;
    };

    MyTopics.populate = function (items) {
      MyTopics.purge();
      angular.forEach(items, function (item) {
        my_topics.push(item);
      });

      topicsChanged();

      return my_topics;
    };

    MyTopics.add = function (item) {
      if (angular.isArray(item)) {
        var topics = [];
        _.each(item, function (el) {
          topics.push({
            'topic': el.topic,
            'topic_type': get_topic_type(el),
            'parent': el.parent,
            'level': el.level
          })
        })
        my_topics = topics;
      } else {
        if (hasTerm(item)) {
          //SystemAlert.info("You have this term in your selected topics.");
          MyTopics.remove(item);
        } else {
          var topic = {
            'topic': item.topic,
            'topic_type': get_topic_type(item),
            'parent': item.parent,
            'level': item.level
          };
          var same_parent = _.filter(my_topics, function (el) {
            return el.parent == item.parent && el.level != item.level;
          });
          if (same_parent.length > 0) {
            _.each(same_parent, function (el) {
              MyTopics.remove(el, true);
            })
          }
          my_topics.push(topic);
        }
      }
      topicsChanged();
    };

    MyTopics.remove = function (item, silent) {

      my_topics = _.filter(my_topics, function (val) {
        return topicHash(val) != topicHash(item);
      });
      if (!silent) {
        topicsChanged();
      }
    };

    MyTopics.getSelected = function () {
      return MyTopics.getList();
    };

    MyTopics.testSelection = function (list) {
      updateLookup();
      var new_list = _.map(list, function (item) {
        item.enabled = hasTerm(item);
        return item;
      });
      return new_list;
    };

    MyTopics.getList = function () {
      return my_topics;
    };

    MyTopics.findTopic = function (topic, list) {
      var hash = angular.isObject(topic) ? topicHash(topic) : topicHash({topic: topic, topic_type: 'leaf'});
      var found = _.find(list, function (item) {
        return topicHash(item) === hash;
      });

      if (!angular.isObject(topic) && found === undefined) {
        hash = angular.isObject(topic) ? topicHash(topic) : topicHash({topic: topic, topic_type: 'node'});
        found = _.find(list, function (item) {
          return topicHash(item) === hash;
        });
      }

      return found;
    };

    MyTopics.setTopics = function (topics) {
      if (topics.indexOf('all') >= 0) {
        my_topics = [];
      } else {
        my_topics = _.map(topics, function (topic) {
          var topicObj = MyTopics.findTopic(topic, my_topics);
          if (topicObj === undefined) {
            console.log("Topic (" + topic + ") to be set as selected in facet was not found.");
          }
          return topicObj;
        });
      }
      topicsChanged();
      return my_topics;
    };

    return MyTopics;

  }
  MyTopics.$inject = ["$rootScope", "$resource"];

  /** @ngInject */
  function TopicCloudMixin() {
    var scopeMixin = {
      _topic_mixin_state: {
        cloud_type: 'none'
      },

      changeCloudView: function (cloud_type) {
        this._topic_mixin_state.cloud_type = cloud_type;
        this.loadTopics();
      },

      getCloudType: function () {
        return this._topic_mixin_state.cloud_type;
      }
    };
    return scopeMixin;
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory("ConversationService", ConversationService);

  // TODO: this is not factory, this most looks like a model service only
  /** @ngInject */
  function ConversationService($http) {
    var url_by_post = '/conversation/json';
    var url_by_user = '/user_profile/json';
    var ConversationService = {
      list_by_post: function (post_id, channel_id) {
        var promise = $http({
          method: 'GET',
          url: url_by_post,
          params: {'post_id': post_id, 'channel_id': channel_id}
        }).then(function (res) {
          return res.data.list;
        });
        return promise;
      },
      list_by_user: function (channel_id, user) {
        var promise = $http({
          method: 'GET',
          url: url_by_user,
          params: {'channel_id': channel_id, 'user_id': user.id, '_type': user._type}
        }).then(function (res) {
          return res.data.list;
        });
        return promise;
      }
    };
    return ConversationService
  }
  ConversationService.$inject = ["$http"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('DialogService', DialogService);

  /** @ngInject */
  function DialogService($rootScope) {
    var watcher = {
      OPEN_DIALOG_EVENT: 'OpenDialogEvent',
      CLOSE_DIALOG_EVENT: 'CloseDialogEvent',
      CLOSE: 'CloseDialogEvent'
    };

    watcher.openDialog = function (data) {
      $rootScope.$broadcast(this.OPEN_DIALOG_EVENT, data);
    };

    watcher.closeDialog = function (data) {
      $rootScope.$broadcast(this.CLOSE_DIALOG_EVENT, data);
    };

    return watcher;
  }
  DialogService.$inject = ["$rootScope"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('PredictorService', PredictorService);

  /**@ngInject */
  function PredictorService($http, $q) {

    var predictorFacets = {};
    var factory = {
      getAllPredictors: getAllPredictors,
      doClassifier: doClassifier,
      getPredictorTypes: getPredictorTypes,
      predictorFacets: predictorFacets,
      getSelectedPredictors: getSelectedPredictors,
      listAllPredictors: listAllPredictors
    };

    return factory;
    /////////////////////////////////////

    function getSelectedPredictors(ids) {
      var predictors;
      if (ids) {
        return $http({
          method: 'GET',
          url: '/predictors/json'
        }).then(function (res) {
          predictors = _.filter(res.data.list, function (item) {
            return ids.indexOf(item.id) !== -1;
          })
        }).then(function () {
          return predictors;
        });
      } else {
        return $q.when([]);
      }
    }

    function listAllPredictors(params) {
      var predictors;

      return $http({
        method: 'GET',
        url: '/predictors/json',
        params: params
      }).then(function (res) {
        predictors = res.data.list;
      }).then(function () {
        return predictors;
      });

    }

    function getAllPredictors(params) {

      var predictors = {};

      if (typeof params === 'undefined') {
        params = {}
      }
      params['aggregate'] = true

      var promise = $http({
        method: 'GET',
        url: '/predictors/json',
        params: params
      }).then(function (res) {

        //filter out complex predictors for now
        predictors['list'] = _.filter(res.data.list, function (pr) {
          return pr.predictor_type !== 'Composite Predictor'
        });

        var promises = _.map(predictors.list, function (predictor) {
          return $http({
            method: 'GET',
            url: '/predictors/' + predictor.id + '/detail?facets=1'
          }).then(processFacet);
        });
        return $q.all(promises);
      }).then(function () {
        return predictors;
      });

      return promise;
      ///////////////

      function processFacet(res) {
        if (!res.data) return;

        var facet = {
          action_vector: {},
          context_vector: {},
          models: {
            all: true,
            list: []
          }
        };

        facet.models.list = _.map(res.data.models_data, function (model) {
          return {
            id: model.model_id,
            display_name: model.display_name,
            enabled: false
          }
        });

        _.each(['action_vector', 'context_vector'], function (key) {

          var mappedKey = (key == 'action_vector') ? 'action_features' : 'context_features';

          _.each(res.data[mappedKey], function (item) {

            facet[key][item.feature] = {
              id: item.feature,
              all: true,
              visible: false,
              description: item.description,
              list: _.map(item.values, function (val) {
                return {
                  display_name: val,
                  enabled: false
                };
              })
            };

          });

        });

        predictorFacets[res.data.id] = facet;
      }

    }

    function getPredictorTypes() {
      /* [{
       display_name: "Agent Matching",
       description: "Predictor for matching agent against customer."
       }, {
       display_name: "Supervisor Alert",
       description: "Predictor for making decision on alert supervisor."
       }, {
       display_name: "Chat Offer",
       description: "Predictor for making decision on chat engagement."
       }] */
      var promise = $http({
        method: 'GET',
        url: '/predictors/default-template'
      }).then(function (res) {
        var types = res.data.template.types;
        if (res.data.template) {
          return _.map(res.data.template.types, function (type) {
            var item = _.find(res.data.template, function (e, key) {
              return e.predictor_type == type;
            });
            return {
              display_name: type,
              description: (item) ? item.description : '',
              enabled: false
            };
          });
        } else {
          return [];
        }
      });
      return promise;
    }

    function doClassifier(action, predictor_id) {
      if (action !== 'reset' && action !== 'retrain') {
        throw Error("Only actions 'reset' and 'retrain' supported. Given '" + action + "'");
      }
      var promise = $http({
        method: 'POST',
        url: '/predictors/command/' + action + '/' + predictor_id
      }).then(function (res) {
        return res.data;
      });
      return promise;
    }

  }
  PredictorService.$inject = ["$http", "$q"];
})();
(function () {
  'use strict';
  
  // TODO: SmartTags, SmartTag, SmartTagForm... just have one SmartTagsService

  angular
    .module('slr.services')
    .factory('SmartTags', SmartTags)
    .factory('MultiChannelTags', MultiChannelTags)
    .factory('SingleEventTags', SingleEventTags)
    .factory('GroupsService', GroupsService)
    .factory('GroupUserService', GroupUserService)
    .factory('SmartTag', SmartTag)
    .factory('SmartTagForm', SmartTagForm);
  
  /** @ngInject */
  function SmartTags($http) {
      var channel_url = "/smart_tags/json";
      var post_url = "/commands/assign_post_tag";
      var multi_post_url = "/commands/assign_tag_multi_post";
      var SmartTags = {
        fetch: function (channel_id, adaptive_learning_enabled) {
          var params = {channel: channel_id};
          if (adaptive_learning_enabled != undefined) {
            params['adaptive_learning_enabled'] = adaptive_learning_enabled;
          }
          var promise = $http({
            method: 'GET',
            url: channel_url,
            params: params
          }).then(function (res) {
            return _.sortBy(_.filter(res.data.list, function (tag) {
              return tag.status == 'Active'
            }), function (item) {
              return item.title.toLowerCase();
            });
          });
          return promise;
        },
        getIntentionsByLabel: function (intentions, selectIntentions) {
          var array = [];
          _.each(intentions, function (intentionLabel) {
            array.push(_.findWhere(selectIntentions, {label: intentionLabel}));
          });
          return _.uniq(array);
        },
        getPostTags: function (channel_id, post_id) {
          var promise = $http({
            method: 'GET',
            url: post_url,
            params: {channel: channel_id, post_id: post_id}
          }).then(function (res) {
            return _.filter(res.data.item, function (tag) {
              return tag.status == 'Active'
            });
          });
          return promise;
        },
        addTagMultiPost: function (channel_id, post_ids, tag_id) {
          var promise = $http({
            method: 'POST',
            url: multi_post_url,
            data: {channel: channel_id, posts: post_ids, tag: tag_id}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        removeTagMultiPost: function (channel_id, post_ids, tag_id) {
          var promise = $http({
            method: 'DELETE',
            url: multi_post_url,
            data: {channel: channel_id, posts: post_ids, tag: tag_id}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        addPostTags: function (channel_id, post_id, tags_ids) {
          var promise = $http({
            method: 'POST',
            url: post_url,
            data: {channel: channel_id, post_id: post_id, ids: tags_ids}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        removePostTags: function (channel_id, post_id, tags_ids, response_id) {
          var promise = $http({
            headers: {'Content-Type': 'mimetype=application/xml'},
            method: 'DELETE',
            url: post_url,
            params: {channel: channel_id, post_id: post_id, ids: tags_ids, response_id: response_id}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        getById: function (tag_id) {
          return $http({
            method: 'GET',
            url: channel_url,
            params: {id: tag_id}
          }).then(function (res) {
            return res.data.item;
          });
        },
        listAll: function (params) {
          return $http({
            method: 'GET',
            url: channel_url,
            params: params
          }).then(function (res) {

            return res.data
          });
        }
      }
      SmartTags.ON_POST_TAGS_REMOVED = 'on_post_tags_removed';
      SmartTags.ON_CONV_TAGS_REMOVED = 'on_conv_tags_removed';
      return SmartTags;
    }
    SmartTags.$inject = ["$http"];
  
  /** @ngInject */
  function MultiChannelTags($http) {
      var tags_url = "/multi_channel_tag/multi";
      var MultiChannelTags = {
        listAll: function (params) {
          return $http({
            method: 'GET',
            url: tags_url,
            params: params
          }).then(function (res) {
            return res.data
          });
        },
        getById: function (tag_id) {
          return $http({
            method: 'GET',
            url: tags_url + '?id=' + tag_id
          }).then(function (res) {
            return res.data.item;
          });
        },
        save: function (tag_data) {
          var promise = $http({
            method: 'POST',
            url: tags_url,
            data: tag_data
          }).then(function (res) {
            return res.data.item;
          });
          return promise;
        },
      }
      return MultiChannelTags;
    }
    MultiChannelTags.$inject = ["$http"];
  
  /** @ngInject */
  function SingleEventTags($http) {
      var tags_url = "/multi_channel_tag/single";
      var SingleEventTags = {
        listAll: function (params) {
          return $http({
            method: 'GET',
            url: tags_url,
            params: params
          }).then(function (res) {
            return res.data
          });
        },
        getById: function (tag_id) {
          return $http({
            method: 'GET',
            url: tags_url + '?id=' + tag_id
          }).then(function (res) {
            return res.data.item;
          });
        },
        save: function (tag_data) {
          var promise = $http({
            method: 'POST',
            url: tags_url,
            data: tag_data
          }).then(function (res) {
            return res.data.item;
          });
          return promise;
        },
      }
      return SingleEventTags;
    }
    SingleEventTags.$inject = ["$http"];
  
  /** @ngInject */  
  function GroupsService($resource) {
      return $resource('groups/json:groupId', {}, {
        query: {method: 'GET', isArray: false}
      });
    }
    GroupsService.$inject = ["$resource"];
    
  /** @ngInject */
  function GroupUserService($resource) {
      return $resource('groups/:action/json', {}, {
        fetchUsers: {method: 'POST', isArray: false, params: {action: 'get_users'}},
        updateUsers: {method: 'POST', params: {action: 'update_users'}}
      });
    }
    GroupUserService.$inject = ["$resource"];
    
  /** @ngInject */
  function SmartTag($resource) {
      var SmartTag = $resource('/smart_tags/:action/json', {}, {
        update: {method: 'POST', params: {action: 'update'}},
        delete: {method: 'POST', params: {action: 'delete'}},
        activate: {method: 'POST', params: {action: 'activate'}},
        deactivate: {method: 'POST', params: {action: 'deactivate'}}
      });
      SmartTag.ON_SMARTTAG_UPDATE = 'on_smarttag_update';
      SmartTag.LRU_TAG_CHANGED = 'on_lru_changed';

      return SmartTag;
    }
    SmartTag.$inject = ["$resource"];
    
  /** @ngInject */
  function SmartTagForm(FilterService, ContactLabelsRest, ChannelsService) {
    
    var ContactLabels = new ContactLabelsRest();
      var SmartTagForm = {};

      SmartTagForm.getIntentions = function () {
        return _.map(FilterService.getIntentions(), function (el) {
          return {display: el.display, label: el.label}
        })
      };
      SmartTagForm.getPostStatuses = function () {
        return _.map(['potential', 'actionable', 'rejected'], function (status) {
          return {display: status, label: status}
        });
      };
      SmartTagForm.getContactLabels = function () {
        return ContactLabels.list().success(function (d) {
          if (!d.list.length) return;
          return _.map(d.list, function (el) {
            return {display: el.title, label: el.id}
          })
        });
      };
      SmartTagForm.getChannels = function () {
        return ChannelsService.getAll('inbound', false, true);
      };
      SmartTagForm.getSmartTagDefaults = function () {
        return {
          influence_score: 0,
          intentions: [],
          keywords: [],
          labels: [],
          usernames: [],
          adaptive_learning_enabled: true,
          alarm_enabled: false,
          groups: [],
          users: [],
          alert: {
            is_active: false,
            posts_limit: 1,
            users: []
          }
        }
      };

      SmartTagForm.getFormTitle = function (form_mode) {
        return {
          'create': 'Create',
          'edit': 'Update'
        }[form_mode];
      };
      return SmartTagForm;
    }
    SmartTagForm.$inject = ["FilterService", "ContactLabelsRest", "ChannelsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory("Posts", Posts)
    .factory('PostsExport', PostsExport)
    .factory('PostFilter', PostFilter);

  /** @ngInject */
  function Posts($rootScope, $resource, ChannelsService, FilterService) {
    var Posts = $resource('/posts/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
    var posts = [];
    //var dateRange = FilterService.getDateRange();
    var search_tabs = [];
    var search_tab = {};
    var is_search = false;
    Posts.level = 'day';

    Posts.ON_DOT_POSTS_FETCHED = 'on_dot_posts_fetched';
    Posts.ON_TAB_POSTS_FETCHED = 'on_tab_posts_fetched';
    Posts.ON_POSTS_FAILED = 'on_posts_failed';
    Posts.ON_POSTS_FETCHED = 'on_posts_fetched';
    Posts.ON_POSTS_BEING_FETCHED = 'on_posts_being_fetched';
    Posts.ON_SEARCH_TAB_SELECTED = 'on_search_tab_selected';
    Posts.ON_SEARCH_PARAMS_UPDATED = 'on_search_params_updated';

    Posts.setLevel = function (level) {
      Posts.level = level;
    }
    Posts.getSearchState = function () {
      return is_search;
    };
    Posts.setSearchState = function (search) {
      is_search = search;
      $rootScope.$broadcast(Posts.ON_SEARCH_TAB_SELECTED);
    };
    Posts.getPosts = function () {
      return posts;
    };

    Posts.updateSearchTabs = function (newTabs) {
      search_tabs = newTabs;
    };
    Posts.getSearchTabs = function () {
      return search_tabs;
    };
    Posts.setCurrentTab = function (tab) {
      search_tab = tab;
      Posts.initExpandedSearchParams(tab);
      // $rootScope.$broadcast(Posts.ON_SEARCH_TAB_SELECTED);
    };
    Posts.getCurrentTab = function () {
      return search_tab;
    };

    Posts.initExpandedSearchParams = function (tab) {

      if (!tab.expandedSearchParams) {
        tab.expandedSearchParams = jQuery.extend(true, {}, tab.params);

        if (tab.expandedSearchParams.from == null) {

          var date = new Date(tab.expandedSearchParams.timestamp);
          var UTCdate = FilterService.getUTCDate(date);

          tab.expandedSearchParams.dateRange = {
            from: UTCdate.toString("MM/dd/yyyy"),
            to: UTCdate.add(1).days().toString("MM/dd/yyyy")
          }

        } else {

          tab.expandedSearchParams.dateRange = {
            from: tab.expandedSearchParams.from,
            to: tab.expandedSearchParams.to
          }

        }
      }

    };
    Posts.getExpandedSearchParams = function () {
      return search_tab.expandedSearchParams;
    };
    Posts.updateThresholds = function (thresholds) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.thresholds = thresholds;
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };
    Posts.updateSortBy = function (what) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.sort_by = what;
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };
    Posts.updateTerms = function (terms, init) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.terms = terms;
      if (!init) {
        $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
      }
    };
    Posts.updateIntentions = function (intentions) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.intentions = intentions;
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };
    Posts.updateDateRange = function (dateRange) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams.dateRange = {
        "from": (dateRange.from).toString("MM/dd/yyyy"),
        "to": (dateRange.to).toString("MM/dd/yyyy")
      };
      $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };

    Posts.filterChanged = function (filterName, value, refresh) {
      var tab = Posts.getCurrentTab();
      tab.expandedSearchParams[filterName] = value;
      if (refresh)
        $rootScope.$broadcast(Posts.ON_SEARCH_PARAMS_UPDATED);
    };

    Posts.has_more_posts = true;
    Posts.offset = 0;
    Posts.limit = 15;
    Posts.last_query_time = null;
    Posts.resetPaging = function () {
      Posts.offset = 0;
      Posts.limit = 15;
      Posts.last_query_time = null;
      Posts.has_more_posts = true;
      posts = [];
    };
    Posts.searchForPosts = function (params) {
      params.offset = Posts.offset;
      params.limit = Posts.limit;
      params.last_query_time = Posts.last_query_time;
      if (ChannelsService.getSelectedId() != null) {
        if (Posts.has_more_posts) {
          $rootScope.$broadcast(Posts.ON_POSTS_BEING_FETCHED);
          Posts.fetch({}, params, function (res) {
            var items = res.list;
            _.each(items, function (item) {
              posts.push(item);
            });
            Posts.has_more_posts = res.are_more_posts_available;
            Posts.offset = posts.length;
            Posts.last_query_time = res.last_query_time;
            $rootScope.$broadcast(Posts.ON_POSTS_FETCHED);
          }, function onError(res) {
            $rootScope.$broadcast(Posts.ON_POSTS_FAILED);
          });
        } else {
          console.log("HAS NO MORE POSTS");
          $rootScope.$broadcast(Posts.ON_NO_MORE_POSTS);
        }
      } else {
        posts = [];
        $rootScope.$broadcast(Posts.ON_POSTS_FETCHED);
      }
    };
    Posts.searchByGraph = function (item, params) {
      $rootScope.$apply(function () {
        Posts.setSearchState(true);
      });

      if (item) {
        Posts.searchForPosts(params);
      }

    };
    Posts.searchByTab = function (params) {
      Posts.setSearchState(true);
      Posts.searchForPosts(params);
    };

    $rootScope.$on("selectChanged", function ($scope, flag, id) {
      Posts.filterChanged(id, $scope.targetScope.params[id], (flag !== 'init'));
    });
    $rootScope.$on("thresholdsChanged", function ($scope) {
      Posts.updateThresholds($scope.targetScope.params.threshold);
    });

    return Posts;

  }
  Posts.$inject = ["$rootScope", "$resource", "ChannelsService", "FilterService"];

  /** @ngInject */
  function PostsExport($modal, $resource, AgentsService, ChannelsService, FilterService, SystemAlert) {
    var resource = $resource('/export/posts/json'),
      PostsExport = {
        "submit": dispatch('export'),
        "check": dispatch('check'),
        "exportPosts": exportPosts
      };

    function dispatch(action) {
      return function (params) {
        var postData = angular.copy(params);
        delete postData['smartTag'];
        postData.action = action;
        postData.all_selected = FilterService.facetsAllSelected();
        postData.limit = 1000;
        return resource.save(postData).$promise;
      };
    }

    function translate(facet, values) {
      var facets = {
        'intentions': {'junk': 'other'},
        'statuses': {'actual': 'replied'}
      };

      return _.map(values, function (val) {
        var facetMap = facets[facet];
        if (facetMap && facetMap[val]) {
          return facetMap[val];
        }
        return val;
      });
    }

    function exportPosts(params) {
      var SUCCESS = 7;  // constant from db/data_export.py

      function checkRunningTask() {
        return PostsExport.check(params).then(function (resp) {
          return resp.task && resp.task.state < SUCCESS;
        }, function onError() {
          return false;
        });
      }

      function submitExport() {
        return PostsExport.submit(params);
      }

      function makePopupViewModel(params) {
        var selectedChannel = ChannelsService.getSelected(),
          smartTag = params.smartTag,
          all = FilterService.isAllSelected,
          joined = function (lst) {
            if (Array.isArray(lst)) {
              return lst.join(', ');
            }
            return '';
          },
          reportName = function (pt) {
            if (!pt) {
              return '';
            }
            return {
              'top-topics': 'Trending Topics',
              'missed-posts': 'Missed Posts',
              'inbound-volume': 'Inbound Volume',
              'first-contact-resolution': 'First Contact Resolution',
              'work-done': 'Work Done',
              'response-time': 'Response Time',
              'response-volume': 'Response Volume',
              'sentiment': 'Sentiment'
            }[pt];
          },
          agentLabel = function (agentId) {
            return AgentsService.getLabel(agentId);
          },
          datePart = function (dateStr) {
            return dateStr.split(' ')[0];
          },
          dateRange = function (from, to) {
            from = datePart(from);
            to = datePart(to);
            if (from == to) {
              return from;
            }
            return from + " — " + to;
          };

        return {
          channel: selectedChannel,
          report_name: reportName(params.plot_type),
          date_range: dateRange(params.from, params.to),
          smart_tags: smartTag && smartTag.title,
          intentions: all('intentions') ? null :
            joined(translate('intentions', params.intentions)),
          sentiments: all('sentiments') ? null :
            joined(params.sentiments),
          status: all('statuses') ? null :
            joined(translate('statuses', params.statuses)),
          topics: joined(_.map(params.topics, function (item) {
            return item.topic;
          })),
          languages: all('languages') ? null :
            joined(params.languages),
          agents: joined(_.map(params.agents, agentLabel))
        };
      }

      function showConfirmPopup() {
        var d = $modal.open({
          backdrop: true,
          keyboard: true,
          templateUrl: '/partials/export/posts',
          controller: ["$scope", function ($scope) {
            var data = makePopupViewModel(params);
            $scope.data = data;
            $scope.table = _([
              ['Report Name', data.report_name],
              ['Date Range', data.date_range],
              ['Smart Tags', data.smart_tags],
              ['Intentions', data.intentions],
              ['Sentiments', data.sentiments],
              ['Posts Status', data.status],
              ['Topics, Keywords', data.topics],
              ['Languages', data.languages],
              ['Agents', data.agents]
            ]).filter(function (row) {
              return row[1];
            }).map(function (item) {
              return {title: item[0], value: item[1]};
            }).value();
            $scope.close = $scope.$close;
          }]
        });
        return d.result;
      }

      checkRunningTask().then(function (taskIsRunning) {
//           if (taskIsRunning) { return; }
        showConfirmPopup().then(function (dialogResult) {
          if (dialogResult === true) {
            return submitExport().then(function (resp) {
              SystemAlert.success(resp.message, 5000);
            });
          }
        });
      });
    }

    return PostsExport;
  }
  PostsExport.$inject = ["$modal", "$resource", "AgentsService", "ChannelsService", "FilterService", "SystemAlert"];

  /** @ngInject */
  function PostFilter($resource, ChannelsService) {
    var PostFilter = $resource('/commands/:action', {}, {
      reject: {method: 'POST', params: {action: "reject_post"}},
      star: {method: 'POST', params: {action: "star_post"}}
    });

    PostFilter.command = function (command, callback) {
      var actor = {
        star: {command: PostFilter.star, status: 'actionable'},
        reject: {command: PostFilter.reject, status: 'rejected'}
      }[command];
      return function (post_or_ids) {
        var params = {
          "posts": _.isArray(post_or_ids) ? post_or_ids : [post_or_ids.id_str],
          "channels": [ChannelsService.getSelectedId()]
        };
        actor.command(params, function () {
          callback(post_or_ids, actor.status);
        });
      };
    };

    return PostFilter;
  }
  PostFilter.$inject = ["$resource", "ChannelsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('DashboardService', DashboardService)
    .factory('WidgetService', WidgetService);

  /** @ngInject */
  function DashboardService($http, $q) {
    var dashboards = {
      'types': [],
      'list': {},
      'load': load,
      'loadSimple': loadSimple
    };
    return dashboards;

    function load() {
      var defer = $q.defer();
      $q.all([
        $http.get('/dashboards/type'),
        $http.get('/dashboards')
      ]).then(function (res) {
        dashboards.types = res[0].data.data;
        _.each(dashboards.types, function (type) {
          dashboards.list[type.id] = _.filter(res[1].data.data, {'type_id': type.id});
        });
        defer.resolve({
          'types': dashboards.types,
          'list': dashboards.list
        })
      }, function (err) {
        dashboards.types = [];
        dashboards.list = {};
        defer.reject('Failed to get dashboards!');
      });
      return defer.promise;
    }

    function loadSimple() {
      var defer = $q.defer();
      $q.all([
        $http.get('/dashboards/type'),
        $http.get('/dashboards')
      ]).then(function (res) {
        dashboards.types = _.map(res[0].data.data, _.partialRight(_.pick, ['id', 'display_name']));
        _.each(dashboards.types, function (type) {
          var list = _.filter(res[1].data.data, {'type_id': type.id});
          dashboards.list[type.id] = _.map(list, _.partialRight(_.omit, 'widgets'));
        });
        defer.resolve({
          'types': dashboards.types,
          'list': dashboards.list
        })
      }, function (err) {
        dashboards.types = [];
        dashboards.list = {};
        defer.reject('Failed to get dashboards!');
      });
      return defer.promise;
    }
  }
  DashboardService.$inject = ["$http", "$q"];

  /** @ngInject */
  function WidgetService($http, $location, $q, $rootScope, $timeout) {
    var current = null,
      CHANGED = 'WidgetService.CHANGED';

    function notify() {
      $rootScope.$broadcast(CHANGED, {widget: current});
    }

    return {
      CHANGED: CHANGED,
      getCurrent: function () {
        return current;
      },
      setCurrent: function (widget) {
        current = widget;
        notify();
      },
      load: function (wid) {
        var self = this;
        return $http({method: 'GET', url: '/dashboard/' + wid + '/widget'}).then(function (res) {
          self.setCurrent(res.data.item);
          return current;
        });
      },
      loadFromLocation: function () {
        var params = $location.search();
        if (params['wid']) {
          return this.load(params['wid']);
        } else {
          return $q.when(null);
        }
      },
      create: function (widget) {
        var fields = ['title', 'description', 'style', 'settings', 'extra_settings', 'dashboard_id'],
          data = _.pick(widget, fields),
          newWidgetURL = '/dashboard/new';
        return $http({method: 'POST', url: newWidgetURL, data: data});
      },
      update: function (widget) {
        var updateWidgetURL = "/dashboard/" + widget.id + "/update",
          self = this;
        return $http({method: 'POST', url: updateWidgetURL, data: widget}).then(function (res) {
          self.setCurrent(res.data.item);
        });
      },

      makeRemove: function (lock, lockParam) {
        var self = this;
        return function () {
          lock[lockParam] = true;
          $timeout(function () {
            $location.search('wid', null);
            $timeout(function () {
              lock[lockParam] = false;
            }, 10);
          }, 0);

          self.setCurrent(null);
        };
      }
    }
  }
  WidgetService.$inject = ["$http", "$location", "$q", "$rootScope", "$timeout"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('popOver', popOver);

  // TODO:??????????????????????
  /** @ngInject */
  function popOver() {
    var pop;
    return {
      get: function () {
        return pop;
      },
      set: function (obj) {
        pop = obj
      }
    }
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .filter('check_label', check_label);

  /** @ngInject */
  function check_label(FilterService) {
    var labels = FilterService.getIntentions();
    return function (input) {
      if (!input) return input;
      return _.find(labels, function (el) {
        return el.label == input.toLowerCase()
      })['display']
    };
  }
  check_label.$inject = ["FilterService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .filter('markTopics', markTopics);

  // TODO: very specific filter, should be moved out of here
  function markTopics() {
    var quote = function (str) {
      return (str + '').replace(/([.?*+^$[\]\\(){}|-])/g, "\\$1");
    };
    RegExp.escape = function (s) {
      return s.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')
    };
    return function (text, filter, sa) {
      if (filter === undefined) {
        return text;
      } else {
        var topic, topics = _.pluck(filter, "content");
        var vote = filter[0].vote;
        var label_class = vote == 0 ? 'label' : vote == 1 ? 'label-voted-up' : 'label-voted-down';
        //var escaped_text = quote(text);
        topics = _.map(topics, function (el) {
          return RegExp.escape(el)
        });
        topic = topics.join("|");

        return text.replace(new RegExp('(' + topic + ')', 'img'),
          '<span sa_id=\"' + sa.speech_act_id + '\" class=\"' + label_class + " " + sa.type + '\">$&</span>');
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .directive('intentionLabels', intentionLabels);

  // watch todo
  /** @ngInject */
  function intentionLabels($filter, popOver, $resource, FilterService) {
    var btnUp = $("<button class='btn btn-success btn-vote-up'><i class='icon-thumbs-up'></i> vote up</button>");
    var btnDown = $("<button class='btn btn-danger btn-vote-down'><i class='icon-thumbs-down'></i> vote down</button>");
    var close = "<button class='close'>&times;</button>";


    var highlight = function (node, intention, position) {
      var attr = '[intention="' + intention + '"]';
      var pos = '[position="' + position + '"]';
      var el = node.find(attr).filter(pos);
      var cl = "int-" + intention + " ilbl";
      //node.find('[intention]').removeClass();
      $(el).addClass(cl);
    };

    var deHighLight = function (textNode) {
      textNode.find('[intention]').removeClass();
    };
    var doVote = function (label, direction) {
      $(label).addClass('label-voted-' + direction);
      $(label).popover("destroy");
    };

    var Feedback = $resource('/feedback/json', {}, {
      intention: {method: 'POST', isArray: false}
    });
    return {
      restrict: 'A',
      replace: true,
      link: function (scope, element, attrs) {
        var tel, post, modal_body, intention, position;
        $(element).on('click', '.label', function (e) {
          tel = angular.element(this);
          post = tel.scope()['item']['post'] || tel.scope()['item'];
          modal_body = tel.parents("tr").next().find('.post-content');
          intention = tel.attr('intention');
          position = tel.attr('position');


          if (popOver.get()) {
            if (this !== popOver.get()) {
              $('.popover .close').trigger('click');
              $(this).popover('show');
              popOver.set(this);
            }
          } else {
            $(this).popover('show');
            popOver.set(this);
          }

          highlight(modal_body, intention, position);
        });

        $(element).on('click', '.close', function () {
          modal_body.find('[intention]').removeClass();
          $(popOver.get()).popover("hide");
          popOver.set(null);
        });

        $(element).on('click', '.btn-vote-down', function () {
          Feedback.intention({
            'post_id': post.id_str,
            'intention': intention,
            'speech_act_id': position,
            'vote': -1
          }, function () {
            doVote(popOver.get(), 'down');
            deHighLight(modal_body);
          }, function onError() {
            $(popOver.get()).popover("hide");
          });
        });
        $(element).on('click', '.btn-vote-up', function () {
          Feedback.intention({
            'post_id': post.id_str,
            'intention': intention,
            'speech_act_id': position,
            'vote': 1
          }, function () {
            doVote(popOver.get(), 'up');
            deHighLight(modal_body);
          }, function onError() {
            $(popOver.get()).popover("hide");
          });
        });


        scope.$watch(attrs.intentionLabels, function (newVal, oldVal) {
          var intentions = FilterService.getSelectedIntentions();
          _.each(newVal, function (v, i) {
            var el = angular.element('<span class="label"></span>');
            el.addClass(v.type);
            el.attr('position', i);
            //el.text($filter('check_label')(v.type) + " : " + v.score);
            el.text($filter('check_label')(v.type));
            el.attr('intention', v.type);
            if (intentions.length > 0 && _.contains(intentions, $filter('check_label')(v.type))) {
              el.addClass('hg');
            }

            el.popover({
              'title': '&nbsp;' + close,
              'trigger': 'manual',
              'content': function () {
                return btnUp.add(btnDown)
              },
              //'container' : 'body',
              'placement': 'top',
              'html': true,
              'index': i
            });

            if (newVal[i].vote != 0) {
              if (newVal[i].vote == -1) {
                doVote(el, "down");
              } else {
                doVote(el, "up");
              }
            }
            element.append(el);
          }); //each
        }); //watch
      } // link
    }; //return
  }
  intentionLabels.$inject = ["$filter", "popOver", "$resource", "FilterService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .directive('voteTopics', voteTopics);

  /** @ngInject */
  function voteTopics($filter, $resource, popOver, MyTopics) {
    var Feedback = $resource('/feedback/json', {}, {
      intention: {method: 'POST', isArray: false}
    });
    var doVote = function (label, direction) {
      $(label).removeClass('label');
      $(label).addClass('label-voted-' + direction);
      $(label).popover("destroy");
    };

    var normaliseText = function (content) {
      //remove space before punctuations
      var cnt = content.replace(/\s?([,!?])\s?/g, "$1 ");
      //no spaces around apostrophe
      cnt = cnt.replace(/\s*(['’])\s*/g, "$1");
      //space before only
      cnt = cnt.replace(/\s*([@#$])\s*/g, " $1");
      return cnt
    };
    var getTopics = function (el, topics, highlight) {
      //return (str+'').replace(/([.?*+^$[\]\\(){}|-])/g, "\\$1");
      var content = $filter('linky2')(el.content);

      if (topics.length > 0 && highlight) {
        return normaliseText($filter('markTopics')(content, topics, el));
      } else {
        return normaliseText(content);
      }
    };

    var btnUp, btnDown, close;
    btnUp = $("<button class='btn btn-success topic-vote-up'><i class='icon-thumbs-up'></i> vote up</button>");
    btnDown = $("<button class='btn btn-danger topic-vote-down' style='margin-left:10px'><i class='icon-thumbs-down'></i> vote down</button>");
    close = '<button class="close">&times;</button>';

    var preparePostText = function (rawPost, selected, highlight) {
      var text = '';
      _.each(rawPost.intentions, function (el, index) {
        var topics = _.filter(rawPost.topics, function (topic) {
          return topic.speech_act_id == el.speech_act_id
        });
        if (selected) {
          //console.log(selected);
          topics = _.filter(topics, function (topic) {
            return _.find(selected, function (el) {
              return topic.content.indexOf(el.topic) != -1
            })
          });
        }
        text += '<span position=\"' + index + '\" intention=\"' + el.type + '\">'
          + getTopics(el, topics, highlight)
          + '</span>';
      });
      return text;
    };
    var voteHandler = function (vote, el, post, s_id) {
      Feedback.intention({
        'post_id': post.id_str,
        'topic': el.text(),
        'speech_act_id': s_id,
        'vote': vote
      }, function (res) {
        doVote(popOver.get(), vote == -1 ? 'down' : 'up')
      }, function onError() {
        $(popOver.get()).popover("hide");
      });
    };
    return {
      link: function (scope, element, attrs) {
        scope.$watch(attrs.voteTopics, function (oldVal, newVal) {
          var myTopics = MyTopics.getSelected();
          if (myTopics.length == 0) {
            element.html(preparePostText(newVal, null, false));
          } else {
            element.html(preparePostText(newVal, MyTopics.getSelected(), true));
          }

          element.find('.label').popover({
            'trigger': 'manual',
            'title': '&nbsp;' + close,
            'content': function () {
              return btnUp.add(btnDown)
            },
            'placement': 'top',
            'html': true
          });
          var el, post, s_id;
          element.on('click', '.label', function () {
            el = angular.element(this);
            post = el.scope()['item']['post'] || el.scope()['item'];
            s_id = el.attr('sa_id');
            if (popOver.get()) {
              if (this !== popOver.get()) {
                $('.popover .close').trigger('click');
                $(this).popover('show');
                popOver.set(this);
              }
            } else {
              $(this).popover('show');
              popOver.set(this);
            }
          });
          element.on('click', '.close', function () {
            $(popOver.get()).popover("hide");
            popOver.set(null);
          });

          /*
           var voteDown = voteHandler(-1, el, post, s_id);
           var voteUp   = voteHandler(1, el, post, s_id);
           */
          //element.on('click', '.topic-vote-down', {vote:-1,el:el,post:post,s_id:s_id}, voteHandler);
          element.on('click', '.topic-vote-down', function () {
            voteHandler(-1, el, post, s_id);
          });
          element.on('click', '.topic-vote-up', function () {
            voteHandler(1, el, post, s_id);
          });

        }); // watch
      }
    }
  }
  voteTopics.$inject = ["$filter", "$resource", "popOver", "MyTopics"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('ACLService', ACLService);

  /** @ngInject */
  function ACLService($http) {
    var sharedService = {};
    var URL = '/acl/json';

    sharedService.getUsersAndPerms = function (data, callback) {
      data.a = 'get';
      return $http.post(URL, data).success(function (data) {
        callback(data.result);
      }).error(function () {
        callback(false);
      });
    };

    sharedService.shareAndSave = function (data, callback) {
      data.a = 'share';
      return $http.post(URL, data).success(function (data) {
        callback(data);
      }).error(function () {
        callback(false);
      });
    };

    return sharedService;
  }
  ACLService.$inject = ["$http"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('Confirm', Confirm);

  /** @ngInject */
  function Confirm($q, $rootScope, PopupService) {
    var popupOptions = {closeAfterAction: true};

    return function (attrs) {
      if (angular.isString(attrs)) {
        attrs = {actionText: attrs};
      }

      var defaults = {
        title: '',
        actionText: 'Are you sure?',
        actionButtonText: 'Yes',
        cancelButtonText: 'No'
      };
      attrs = angular.extend(defaults, attrs);

      var deferred = $q.defer(),
        scope = $rootScope.$new(),
        actionFnName = '__confirmActionFunction',
        cancelFnName = '__confirmCancelFunction';
      scope[actionFnName] = function () {
        deferred.notify({action: 'confirm'});
        deferred.resolve();
      };
      scope[cancelFnName] = function () {
        deferred.notify({action: 'cancel'});
        deferred.reject();
        PopupService.close();
      };

      PopupService.confirm(attrs["title"], attrs["actionText"],
        attrs["actionButtonText"], actionFnName + "()",
        attrs["cancelButtonText"], cancelFnName + "()",
        scope, popupOptions);
      return deferred.promise;
    }
  }
  Confirm.$inject = ["$q", "$rootScope", "PopupService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('PopupService', ["$http", "$compile", function ($http, $compile) {
      var popupService = {};

      // Get the popup
      popupService.getPopup = function (create) {
        if (!popupService.popupElement && create) {
          popupService.popupElement = $('<div class="modal"></div>');
          popupService.popupElement.appendTo('BODY');
        }

        return popupService.popupElement;
      };

      popupService.compileAndRunPopup = function (popup, scope, options) {
        $compile(popup)(scope);
        popup.modal(options);
      };

      // Is it ok to have the html here? should all this go in the directives? Is there another way
      // get the html out of here?
      popupService.alert = function (title, text, buttonText, alertFunction, scope, options) {
        text = (text) ? text : "Alert";
        buttonText = (buttonText) ? buttonText : "Ok";
        var alertHTML = "<div class=\"modal-dialog\"><div class=\"modal-content\">";
        if (title) {
          alertHTML += "<div class=\"modal-header\"><h1>" + title + "</h1></div>";
        }
        alertHTML += "<div class=\"modal-body\">" + text + "</div>"
          + "<div class=\"modal-footer\">";
        if (alertFunction) {
          alertHTML += "<button class=\"btn btn-default\" ng-click=\"" + alertFunction + "\">" + buttonText + "</button>";
        }
        else {
          alertHTML += "<button class=\"btn btn-default\">" + buttonText + "</button>";
        }
        alertHTML += "</div></div></div>";
        var popup = popupService.getPopup(true);
        popup.html(alertHTML);
        if (!alertFunction) {
          popup.find(".btn").click(function () {
            popupService.close();
          });
        }

        popupService.compileAndRunPopup(popup, scope, options);
      };

      // Is it ok to have the html here? should all this go in the directives? Is there another way
      // get the html out of here?
      popupService.confirm = function (title, actionText, actionButtonText, actionFunction, cancelButtonText, cancelFunction, scope, options) {
        actionText = (actionText) ? actionText : "Are you sure?";
        actionButtonText = (actionButtonText) ? actionButtonText : "Ok";
        cancelButtonText = (cancelButtonText) ? cancelButtonText : "Cancel";

        var popup = popupService.getPopup(true);
        var confirmHTML = "<div class=\"modal-dialog\"><div class=\"modal-content\">";
        if (title) {
          confirmHTML += "<div class=\"modal-header\"><h1>" + title + "</h1></div>";
        }
        confirmHTML += "<div class=\"modal-body\">" + actionText + "</div>"
          + "<div class=\"modal-footer\">";
        if (cancelFunction) {
          confirmHTML += "<button class=\"btn btn-cancel\" ng-click=\"" + cancelFunction + "\">" + cancelButtonText + "</button>";
        }
        else {
          confirmHTML += "<button class=\"btn btn-cancel\">" + cancelButtonText + "</button>";
        }
        if (actionFunction) {
          confirmHTML += "<button class=\"btn btn-primary\" ng-click=\"" + actionFunction + "\">" + actionButtonText + "</button>";
        }
        else {
          confirmHTML += "<button class=\"btn btn-primary\">" + actionButtonText + "</button>";
        }
        confirmHTML += "</div></div></div>";
        popup.html(confirmHTML);
        if (!actionFunction || options.closeAfterAction) {
          popup.find(".btn-primary").click(function () {
            popupService.close();
          });
        }
        if (!cancelFunction) {
          popup.find(".btn-cancel").click(function () {
            popupService.close();
          });
        }
        popupService.compileAndRunPopup(popup, scope, options);

      };

      // Loads the popup
      popupService.load = function (url, scope, options) {
        $http.get(url).success(function (data) {
          var popup = popupService.getPopup(true);
          popup.html(data);
          popupService.compileAndRunPopup(popup, scope, options);
        });
      };

      popupService.close = function () {
        var popup = popupService.getPopup();
        if (popup) {
          popup.modal('hide');
        }
      };

      return popupService;
    }]); 
})();
(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('DynamicFacetsService', DynamicFacetsService);

  /**@ngInject */
  function DynamicFacetsService($http, $q) {

    var facets = {};

    var factory = {
      getFacetsBySection: getFacetsBySection,
      dynamic_facets: facets
    };

    return factory;
    /////////////////////////////////////

    /*
    /facet-filters/customer
    /facet-filters/agent
    /facet-filters/journey/<journey-type-name>
    */

    function getFacetsBySection(section, id, params) {

      if (typeof params === 'undefined') {
        params = {}
      }

      //for some entities we first need to pass type_id(name) to load facets
      var type_id = _.isUndefined(id) ? '' : '/' + id;

      var url = '/facet-filters/' + section + type_id;

      var promise = $http({
        method: 'GET',
        url: url,
        params: params
      }).then(processFacet);

      return promise;
      ///////////////

      function processFacet(res) {
        //if (!res.data) return;
        var dynamic = {
          facets: [],
          metrics: [{type: 'count', value: 'count', active: true, label: 'count'}],
          group_by : [],
          sankey_group_by : [{type: 'All', value: null, active: true}]
        };

        _.each(['filters', 'group_by', 'metrics'], function (key) {
          _.each(res.data[key], function (item) {
            if (key == 'filters') {
              if(item.values && item.values.length > 0) {
                dynamic.facets.push(
                  {
                    id: item.name,
                    all: true,
                    visible: false,
                    description: item.name + ":" + item.type + ":" + item.cardinality,
                    list: _.map(item.values, function (val) {
                      return {
                        display_name: val || 'N/A',
                        enabled: false
                      };
                    })
                  }
                );
              }

            } else if(key == 'metrics') {
              dynamic.metrics.push(
                {type: item, value: item, active: false, label: item}
              )
            } else if(key == 'group_by') {
              dynamic.group_by.push(
                {type: item, value: item, active: false}
              );
              dynamic.sankey_group_by.push(
                {type: item, value: item, active: false}
              )
            }
          });
        });

        dynamic.group_by.push({type: 'all', value: null, active: false});

        return(dynamic);
        //predictorFacets[res.data.id] = facet;
      }

    }





  }
  DynamicFacetsService.$inject = ["$http", "$q"];
})();
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
  AnalysisService.$inject = ["AnalysisRest", "$q"];
})();
(function() {
  'use strict';

  angular
    .module('slr.components', [
      'slr.services',
      'slr.analysis',
      'slr.chart',
      'slr.horizontal-timeline',
      'slr.smart-tags-modal',
      'slr.date-range-dropdown',
      'slr.accounts-list',
      'slr.widget-dialog',
      'slr.facet-panel',
      'slr.ng-confirm'
    ]);

  angular.module('components', [
    'infinite-scroll',
  ]);

})();
(function () {
  'use strict';
  
  angular
    .module('slr.accounts-list', [
            
    ]);
})();
(function () {
  'use strict';

  angular
    .module('slr.accounts-list')
    .directive('slrAccountsList', slrAccountsList);

  /** @ngInject */
  function slrAccountsList($rootScope, AccountsService) {
    return {
      restrict: 'EA',
      scope : {
        user : '='
      },
      replace: true,
      template: '<ul class="dropdown-menu" style="overflow-y: auto; max-height: 768px">' +
                '<li role="presentation" class="dropdown-header">Actions</li>' +
                '<li ng-if="(cur_account.is_admin) || (cur_account.is_analyst) || (cur_account.is_staff) || (cur_account.is_superuser)">' +
                '<a href="/configure#/channels">Settings</a></li>' +
                '<li ng-if="cur_account.is_only_agent && !cur_account.is_superuser">' +
                  '<a href="/users/{{ user.email }}/password">Settings</a></li>' +
                '<li class="divider"></li>' +
                '<li role="presentation" class="dropdown-header">Accounts</li>' +
                '<li ng-repeat="acct in accounts | orderBy:\'name\'"' +
                    'ng-class="{active: acct.is_current}">' +
                    '<a ng-href="/accounts/switch/{{acct.id}}"' +
                    'ng-bind="acct.name"></a>' +
                '</li>' +
                '<li class="divider"></li>' +
                '<li role="presentation" class="dropdown-header">Selected app</li>' +
                '<li ng-repeat="app_name in cur_account.configured_apps" ' +
                    'ng-class="{active: cur_account.selected_app === app_name}">' +
                  '<a href="/account_app/switch/{{ app_name }}">{{ app_name }}</a>' +
                '</li></ul>',
      link: function(scope) {
        $rootScope.$on(AccountsService.ACCOUNTS_EVENT, function () {
          scope.accounts    = AccountsService.getList();
          scope.cur_account = AccountsService.getCurrent();
        });

        AccountsService.query();        
      }
    }
  }
  slrAccountsList.$inject = ["$rootScope", "AccountsService"];
})();
(function() {
  'use strict';

  angular
    .module('slr.analysis', [
      'ark-components',
      'ui.bootstrap-slider',
      'ngAnimate',
      'ui.slimscroll',
      'infinite-scroll'
    ]);
})();
(function () {
  'use strict';

  angular.module('slr.analysis')
    .factory('AnalysisClassification', AnalysisClassification);

  /** @ngInject */
  function AnalysisClassification(Utils, $timeout) {

    var getPositions = function (cr, buckets) {
      var positions = [];
      var keys = _.keys(cr.value); // bucket index
      var values = _.values(cr.value); // % percentages

      _.each(buckets, function (buck, buckIndex) {
        _.each(keys, function (k, i) {
          if (buckIndex.toString() === k) {
            positions.push({
              key: cr.key,
              bucket: buck.trim(),
              value: Math.round(values[i])
            });
          }
        });
      });

      if (_.has(cr.value, '-1')) {
        var key = cr.key == 'None' ? '0' : cr.key;

        positions.push({
          key: key,
          bucket: 'N/A',
          value: Math.round(cr.value['-1'])
        });
      }

      return positions;
    };

    var getTrendData = function (timerange, buckets) {
      var data = [];

      _.each(timerange, function (t) {
        var foundBucket = buckets[t.class_key];
        if (angular.isDefined(foundBucket)) {
          data.push({
            label: foundBucket,
            data: t.timerange
          });
        }
      });

      return data;
    };

    var getDataForBar = function (crosstab_results, buckets) {
      var barData = [];
      var all = [];

      _.each(crosstab_results, function (cr) {
        var positions = getPositions(cr, buckets);
        all.push(positions);
      });

      var flatten = _.flatten(all);
      var allBuckets = _.uniq(_.pluck(flatten, 'bucket'));

      _.each(allBuckets, function (b) {
        if (['n/a'].indexOf(b.toLowerCase()) >= 0) return;  // '0 - 0 '
        var founds = _.where(flatten, {bucket: b});
        var values = [];

        _.each(founds, function (f) {
          values.push({
            x: f.key,
            y: Math.round(f.value)
          });
        });

        barData.push({
          key: b,
          values: values
        });
      });

      return barData;
    };

    var getDataForPie = function (crosstab_results, buckets) {
      var pieData = [];
      var all = [];

      _.each(crosstab_results, function (cr) {
        var positions = getPositions(cr, buckets);
        all.push(positions);
      });

      var flattenAll = _.flatten(all);
      var allBuckets = _.uniq(_.pluck(flattenAll, 'bucket'));

      _.each(allBuckets, function (b) {
        //if (b == '0 - 0') return;
        var foundVals = _.where(flattenAll, {bucket: b});
        var sum = 0;

        _.each(foundVals, function (fv) {
          sum += fv.value;
        });

        pieData.push({
          label: b,
          value: {
            sum: sum,
            data: _.without(foundVals, 'bucket')
          }
        });
      });

      return pieData;
    };

    var getSelectedFeatureData = function (data, callback) {
      var report = data.report;
      var metricData = data.metricData;
      var flags = data.flags;
      var feature = data.feature;
      var charts = [];
      var feature_order;

      report.buckets = report.metric_values.toString().split(',');

      if (feature === 'Overall') {
        var timerange = getTrendData(report.timerange_results, report.buckets);
        buildTable(report.parsedResults, report.buckets);

        if (timerange.length) {
          flags.showTrend = true;
          charts.push({
            data: timerange,
            settings: {
              chart_type: 'LINE',
              yAxisLabel: 'Count',
              yAxisFormat: '.f',
              height: '400px',
              level: report.level,
              visible: flags.showTrend
            },
            header: report.parsed_analyzed_metric + ' Trends',
            width: !_.isEmpty(metricData) ? 65 : 100
          });
        }

        if (!_.isEmpty(metricData)) {
          var pieData = getDataForPie(metricData.value.crosstab_results, report.buckets);

          flags.showPie = true;
          charts.push({
            data: pieData,
            settings: {
              isMetric: true,
              chart_type: 'PIE',
              height: '400px',
              visible: flags.showPie
            },
            class: 'pull-right',
            header: 'Pie chart',
            width: 33
          });
        }

      } else {
        /** Other Features */
        var filtered = [];

        _.each(report.parsedResults, function (pr) {
          if (pr.key === feature) {
            filtered.push(pr);
          }
        });

        if (filtered[0].value.crosstab_results.length > 30) {
          var _pieData = getDataForPie(filtered[0].value.crosstab_results, report.buckets);
          var pieProcessedData = [];

          _.each(_pieData, function(each) {
            var values = _.pluck(each.value.data, 'key');

            pieProcessedData.push({
              label: each.label,
              value: each.value.data.length, // count
              avg_val: Utils.mean(values)
            });
          });

          flags.showPie = true;
          charts.push({
            data: pieProcessedData,
            settings: {
              isMetric: true,
              tooltipSpecialKey: {label: 'Mean value', key: 'avg_val'},
              labelType: 'count',
              valueFormat: '.f',
              chart_type: 'PIE',
              height: '400px',
              visible: flags.showPie
            },
            class: 'pull-right',
            header: 'Pie chart',
            width: 100
          });
        } else {
          flags.showBar = true;
          var barData = getDataForBar(filtered[0].value.crosstab_results, report.buckets);

          charts.push({
            data: barData,
            settings: {
              chart_type: 'BAR',
              stacked: true,
              height: '400px',
              isMetric: true,
              yAxisLabel: 'Percentage',
              xAxisLabel: filtered.key,
              visible: flags.showBar
            },
            header: 'Bar chart',
            width: 100
          });
        }


        if (filtered[0].value.discriminative_weight) {
          feature_order = Utils.roundUpTo2precision(filtered[0].value.discriminative_weight);
        }

        buildTable(filtered, report.buckets);
      }

      callback({
        flags: flags,
        feature_order: feature_order,
        charts: _.map(charts, function (c) {
          return _.extend(c, {chart_id: Math.floor((1 + Math.random()) * 0x10000).toString(16)});
        })
      });
    };

    // special cross-table for classification
    function buildTable(parsedResults, buckets) {
      angular.element('#table-results > table').remove();

      var table = document.createElement('table'),
        thead = document.createElement('thead'),
        tbody = document.createElement('tbody');

      table.className = 'table table-default';

      var trHead = document.createElement('tr');
      var emptyHead = document.createElement('th');

      if (parsedResults.length > 1) {
        emptyHead.setAttribute('colspan', 2);
      } else {
        emptyHead.innerHTML = 'Value';
      }

      emptyHead.setAttribute('width', '20%');
      trHead.appendChild(emptyHead);

      // thead
      _.each(buckets, function (el) {
        var th = document.createElement('th');
        th.innerHTML = el;
        trHead.appendChild(th);
      });

      var lastHead = document.createElement('th');
      lastHead.innerHTML = 'N / A';
      trHead.appendChild(lastHead);

      thead.appendChild(trHead);
      table.appendChild(thead);

      /** tbody */
      _.each(parsedResults, function (pr) {

        _.each(pr.value.crosstab_results, function (cr, index) {
          var tr = document.createElement('tr');

          // label
          if (index === 0 && parsedResults.length > 1) {
            var tdLabel = document.createElement('td');
            tdLabel.setAttribute('rowspan', pr.value.crosstab_results.length);
            tdLabel.style.fontWeight = 'bold';

            var span = document.createElement('span');
            var space = document.createElement('br');
            span.className = 'badge';

            if (parsedResults.length > 1) {
              var weight = pr.value.discriminative_weight;
              if (weight >= 0.7) {
                span.style.backgroundColor = '#4AC764';
              } else if (weight <= 0.5) {
                span.style.backgroundColor = '#EA4F6B';
              }
              span.innerHTML = Utils.roundUpTo2precision(weight);
            }

            tdLabel.innerHTML = pr.key.replace(/_/g, ' ');
            tdLabel.appendChild(space);
            tdLabel.appendChild(span);
            tr.appendChild(tdLabel);
          }

          // key
          if (cr.key === 'null') {
            cr.key = 'n/a';
          }
          var td = document.createElement('td');
          td.setAttribute('colspan', 1);
          td.innerHTML = cr.key;
          tr.appendChild(td);

          var values = _.values(cr.value); // % percentages
          _.each(buckets, function (buck, buckIndex) {
            var tdValue = document.createElement('td');
            tdValue.setAttribute('colspan', 1);

            tdValue.innerHTML = Math.round(parseFloat(values[buckIndex])) + ' %';

            tr.appendChild(tdValue);
            //}
          });

          if (_.has(cr.value, '-1')) {
            var tdNA = document.createElement('td');
            tdNA.setAttribute('colspan', 1);
            tdNA.innerHTML = Math.round(cr.value['-1']) + ' %';
            tr.appendChild(tdNA);
          }

          tbody.appendChild(tr);
        });
      });

      table.appendChild(tbody);

      $timeout(function() {
        angular.element('#table-results').append(table);
      });
    }

    return {
      buildTable: buildTable,
      getSelectedFeatureData: getSelectedFeatureData,
      getDataForPie: getDataForPie,
      getDataForBar: getDataForBar,
      getTrendData: getTrendData,
      getPositions: getPositions
    }
  }
  AnalysisClassification.$inject = ["Utils", "$timeout"];
}());
(function () {
  'use strict';

  angular.module('slr.analysis')
    .factory('AnalysisRegression', AnalysisRegression);

  /** @ngInject */
  function AnalysisRegression(Utils, $timeout) {

    function buildModeStatement(list) {
      var mode = Utils.roundUpTo2precision(list[0]), repeat = list[1], res = '';
      if (repeat > 1 && !isNaN(repeat) && !isNaN(mode)) {
        res += mode + ' (Repeats ' + repeat + ' times)';
      } else {
        res = mode;
      }
      return res;
    }

    var getSelectedFeatureData = function (data, callback) {
      // TODO[sabr]: Add eager objects initialization - $scope.charts for example
      var charts = [];
      var feature = data.feature;
      var flags = data.flags;
      var report = data.report;
      var score;
      var table;

      var integer = '.0f';

      if (feature == 'Overall') {
        flags.showMultichart = true;
        var lineBarChart = _.map(report.timerange_results, function (each, index) {
          var isMetric = each.label !== report.analyzed_metric;
          return {
            key: each.label,
            bar: isMetric,
            color: isMetric ? '#4AC764' : '#EA4F6B',
            values: each.data
          };
        });

        charts.push({
          data: lineBarChart,
          header: "Overall",
          settings: {
            chart_type: 'LINEBAR',
            charts_settings: [
              { type: 'bar', color: '#4AC764', yAxis: 1 }, // count
              { type: 'line', color: '#EA4F6B', yAxis: 2 } // metric
            ],
            height: '400px',
            yAxisFormat: integer,
            level: report.level,
            isMetric: true,
            yAxisLabel: report.analyzed_metric,
            yAxis2Label: lineBarChart[1].key,
            visible: flags.showMultichart
          }
        });

        table = {
          thWidths: ['45px', '48%', '48%'],
          th: ['Rank', 'Feature', 'Feature Score'],
          tr: _.map(report.parsedResults, function (pr) {
            return {td: [pr.value.rank, pr.key, Utils.roundUpTo2precision(pr.value.score)]};
          })
        };

      } else {
        var filtered = _.find(report.parsedResults, {key: feature}).value;
        var _data, _full_data = [], page = 0;
        score = Utils.roundUpTo2precision(filtered.score);

        if (filtered.value_type === 'Label') {
          // categorical feature
          var cat_descriptive_analysis = [];
          _.each(filtered.boxplot, function (cr) {
            var values = cr.values || cr.value;
            cat_descriptive_analysis.push({
              feature_value: cr.label,
              mean: Utils.roundUpTo2precision(values.mean),
              mode: buildModeStatement(values.mode),
              median: Utils.roundUpTo2precision(values['Q2'])
            });
          });

          if (filtered.boxplot.length > 40) {
            _full_data = filtered.boxplot;
            _data = filtered.boxplot.slice(0, 40);
            page = 1;
          } else {
            _data = filtered.boxplot;
          }

          flags.showBoxChart = true;
          // flags.showPie = true;
          charts.push({
            data: _data,
            full_data: _full_data,
            header: "Box plot",
            width: 100, // %
            offset: _full_data.length ? 40 : 0,
            page: page,
            settings: {
              chart_type: 'BOXPLOT',
              isMetric: true,
              height: '400px',
              yDomain: report.metric_values_range,
              yAxisFormat: integer,
              yAxisLabel: report.parsed_analyzed_metric || 'Metric',
              xAxisLabel: feature,
              showXAxis: _data.length <= 10,
              visible: flags.showBoxChart
            }
          });

          // charts.push({
          //   data: filtered.pie,
          //   header: "Pie chart",
          //   width: 33,
          //   class: 'pull-right',
          //   settings: {
          //     chart_type: 'PIE',
          //     height: '400px',
          //     valueFormat: integer,
          //     visible: flags.showPie
          //   }
          // });

          table = {
            thWidths: ['120px', '30%', '30%', '30%'],
            th: ['Feature Value', 'Mean', 'Median', 'Mode'],
            tr: _.map(cat_descriptive_analysis, function (ua) {
              return {td: [ua['feature_value'], ua['mean'], ua['median'], ua['mode']]}
            })
          };
        } else {
          // continuous feature
          var cont_cat_descriptive_analysis = _.map(filtered.boxplot, function (ua) {
            return {
              feature_value: ua.label,
              mean: Utils.roundUpTo2precision(ua.values.mean),
              mode: buildModeStatement(ua.values.mode),
              median: Utils.roundUpTo2precision(ua.values['Q2'])
            };
          });

          /** Scatter */
          // if (filtered.scatter.length > 40) {
          //   _full_data = filtered.scatter;
          //   _data = filtered.scatter.slice(0, 40);
          //   page = 1;
          // } else {
          //   _data = filtered.scatter;
          // }

          /** Boxplot */
          var boxplot = [], _boxplot;
          if (filtered.boxplot.length > 40) {
            boxplot = filtered.boxplot;
            _boxplot = filtered.boxplot.slice(0, 40);
            page = 1;
          } else {
            _boxplot = filtered.boxplot;
          }

          flags.showBoxChart = true;
          charts.push({
            data: _boxplot,
            full_data: boxplot,
            header: "Box plot",
            width: 100, // %
            offset: boxplot.length ? 40 : 0,
            page: page,
            settings: {
              chart_type: 'BOXPLOT',
              isMetric: true,
              height: '400px',
              yDomain: report.metric_values_range,
              showXAxis: true,
              xAxisFormat: integer,
              yAxisFormat: integer,
              yAxisLabel: report.parsed_analyzed_metric || 'Metric',
              xAxisLabel: feature,
              visible: flags.showBoxChart
            }
          });

          /** Scatter plot */
          // flags.showScatter = true;
          // charts.push({
          //   data: _data,
          //   full_data: _full_data,
          //   offset: _full_data.length ? 40 : 0,
          //   page: page,
          //   header: "Scatter plot",
          //   settings: {
          //     chart_type: 'SCATTER',
          //     width: 100,
          //     isMetric: true,
          //     categorized: false, // need to check if Feature Values has labels
          //     height: '400px',
          //     yDomain: report.metric_values_range,
          //     yAxisLabel: report.parsed_analyzed_metric || 'Metric',
          //     xAxisLabel: feature,
          //     visible: flags.showScatter
          //   }
          // });

          /** Bar chart */
          var barData = [], _barData;
          if (filtered.bar.length > 40) {
            _barData = filtered.bar.slice(0, 40);
          } else {
            _barData = filtered.bar;
          }

          _barData[0].metric = report.parsed_analyzed_metric;

          flags.showBar = false;
          flags.showSwitchBtns = true;
          charts.push({
            data: _barData,
            full_data: barData,
            offset: barData.length ? 40 : 0,
            page: page,
            settings: {
              chart_type: 'BAR',
              stacked: false,
              height: '400px',
              yAxisFormat: integer,
              xAxisFormat: integer,
              yDomain: report.metric_values_range,
              yAxisLabel: 'Count',
              xAxisLabel: '', // TODO[sabr]: until Feature value has categories
              visible: flags.showBar
            },
            header: 'Bar chart',
            width: 100
          });

          /** Table */
          table = {
            thWidths: ['100px', '30%', '30%', '30%'],
            th: ['Feature', 'Mean', 'Median', 'Mode'],
            tr: _.map(cont_cat_descriptive_analysis, function (ua) {
              return {td: [ua['feature_value'], ua['mean'], ua['median'], ua['mode']]}
            })
          };
        }
      }

      buildTable(table);

      callback({
        feature_order: score,
        table: table,
        flags: flags,
        charts: _.map(charts, function (c) {
          return _.extend(c, {chart_id: Math.floor((1 + Math.random()) * 0x10000).toString(16)});
        })
      });
    };

    function buildTable(tableData) {
      angular.element('#table-results > table').remove();

      var table = document.createElement('table'),
        thead = document.createElement('thead'),
        tbody = document.createElement('tbody');

      table.className = 'table table-default';

      var trHead = document.createElement('tr');

      // head
      _.each(tableData.th, function(th, i) {
        var emptyHead = document.createElement('th');
        emptyHead.setAttribute('style', 'width: ' + tableData.thWidths[i]);
        emptyHead.innerHTML = th;
        trHead.appendChild(emptyHead);
      });

      // body
      _.each(tableData.tr, function(tr) {
        var emptyRow = document.createElement('tr');
        _.each(tr.td, function(td) {
          var emptyCell = document.createElement('td');
          emptyCell.innerHTML = td;
          emptyRow.appendChild(emptyCell);
        });
        tbody.appendChild(emptyRow);
      });

      thead.appendChild(trHead);
      table.appendChild(thead);
      table.appendChild(tbody);
      $timeout(function() {
        angular.element('#table-results').append(table);
      });
    }

    return {
      getSelectedFeatureData: getSelectedFeatureData,
      buildTable: buildTable
    }
  }
  AnalysisRegression.$inject = ["Utils", "$timeout"];
}());
(function () {
  'use strict';

  angular.module('slr.analysis')
    .factory('AnalysisReport', AnalysisReport);

  /** @ngInject*/
  function AnalysisReport(Utils,
                          $window,
                          AnalysisService,
                          AnalysisClassification,
                          AnalysisRegression,
                          AnalysisRest) {
    var Analysis = new AnalysisRest();

    var getParsedSemantics = function (results) {
      _.each(results, function (r, rI) {
        results[rI].key = (r.key.replace(/[_:]/g, ' '));
      });

      return results;
    };

    var disableFlags = function () {
      return {
        showBar: false, showPie: false,
        showScatter: false, showTrend: false,
        showBoxPlot: false, showSwitchBtns: false,
        showTable: false, showCharts: true, showMultichart: false
      }
    };

    var deleteReport = function (report, callback) {
      Analysis.remove(report.id)
        .success(function (res) {
          callback(res);
        });
    };

    var buildReport = function (report, callback) {
      var metricData;
      var tabs = [];

      if (_.has(report.filters, 'facets')) {
        _.extend(report, {dynFacets: report.filters.facets});
        delete report.filters.facets;
      }

      _.extend(report, {
        parsedFilters: Utils.objToArray(report.filters),
        parsedResults: _.sortBy(Utils.objToArray(report.results), function (r) {
            return r.value.discriminative_weight || r.value.score;
          }).reverse()
      });

      var arr = [];
      _.each(report.parsedResults, function (r, index) {
        if (report.analysis_type === 'classification') {
          report.parsedResults[index].value.crosstab_results = Utils.objToArray(r.value.crosstab_results);
        }

        if (r.key === report.analyzed_metric) {
          metricData = report.parsedResults[index];
        } else {
          arr.push(report.parsedResults[index]);
        }
      });

      report.parsedResults = getParsedSemantics(arr);

      report.parsedFilters.forEach(function (obj) {
        if (['from', 'to'].indexOf(obj.key) >= 0) {
          obj.value = moment.utc(obj.value).local().format('lll');
        }
      });

      var diff = Utils.compareArrays(report.metric_values, report.metric_values_range);

      if (report.analysis_type == 'classification' ||
        (report.metric_values && report.metric_values.length > 1 && diff)) {
      }

      _.extend(report, {parsed_analyzed_metric: report.analyzed_metric});

      _.each(report.parsedResults, function (r) {
        if (r.value.values.length) {
          tabs.push({
            name: r.key,
            active: false
          });
        }
      });

      report.width = $window.innerWidth - 500;

      delete report.results;

      AnalysisService.setAsBuilt();  // this marks the flag as true, and already built (pre-processed) reports won't be built again

      callback({
        report: report,
        metricData: metricData,
        tabs: tabs
      });
    };

    var exportTable = function (report, selectedFeature) {
      var blob = new Blob([document.getElementById('table-results').innerHTML], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8"
      });
      saveAs(blob, report.title + ' - ' + selectedFeature + ".xls");
    };

    var selectFeature = function (data, callback) {
      var report = data.report;
      var analysis_type = report.analysis_type;

      if (_.isUndefined(analysis_type) || analysis_type == null) {
        analysis_type = (report.metric_values.length > 1 && report.metric_values !== ['0', '10'])
          ? 'classification' : 'regression';
      }

      if (analysis_type == 'classification') {
        AnalysisClassification.getSelectedFeatureData(data, function (rep) {
          callback(rep);
        });
      } else if (analysis_type == 'regression') {
        AnalysisRegression.getSelectedFeatureData(data, function (rep) {
          callback(rep);
        });
      }
    };

    var paginate = function (direction, charts, chart) {
      _.each(charts, function (c) {
        if (chart.chart_id === c.chart_id) {
          var rS = c.offset * c.page, rE = c.offset * (c.page + 1);
          var lS = c.offset * (c.page - 2), lE = c.offset * (c.page - 1);

          if (direction === 'right' && c.page + 1 <= Math.ceil(c.full_data.length / c.offset)) {
            if (chart.settings.chart_type === 'BAR') {
              c.data = c.full_data;
              c.data[0].values = c.full_data[0].values.slice(rS, rE);
            } else {
              c.data = c.full_data.slice(rS, rE);
            }
            c.page++;
          } else if (direction === 'left' && c.page - 1 >= 1) {
            if (chart.settings.chart_type === 'BAR') {
              c.data = c.full_data;
              c.data[0].values = c.full_data[0].values.slice(lS, lE);
            } else {
              c.data = c.full_data.slice(lS, lE);
            }
            c.page--;
          }
        }
      });

      return charts;
    };

    return {
      buildReport: buildReport,
      selectFeature: selectFeature,
      exportTable: exportTable,
      disableFlags: disableFlags,
      deleteReport: deleteReport,
      paginate: paginate,
      getParsedSemantics: getParsedSemantics
    }
  }
  AnalysisReport.$inject = ["Utils", "$window", "AnalysisService", "AnalysisClassification", "AnalysisRegression", "AnalysisRest"];
}());
(function () {
  'use strict';

  angular
    .module('slr.analysis')
    .directive('analysisPanel', analysisPanel);

  /** @ngInject */
  function analysisPanel(AnalysisRest, AnalysisReport, $state, $rootScope, SystemAlert, MetadataService, Utils, $timeout, AnalysisService, toaster) {
    return {
      restrict: 'EA',
      scope: {
        analysisFilters: '=',
        analysisExtraParams: '='
      },
      templateUrl: '/static/assets/js/app/_components/analysis/directives/components.analysis-panel.html',
      link: function (scope) {
        var Apps = MetadataService.getApps();
        var Analysis = new AnalysisRest();

        var extraParams;
        var filters;
        var reportId;

        var conversionLabels = [
          // ordering is important to match the colors/legend-ordering
          // between funnel view and generated report
          {name: 'converted', checked: true},
          {name: 'abandoned', checked: true},
          {name: 'stuck', checked: true}
        ];

        var ja_standard_metrics = [
          {
            name: 'Conversion',
            selected: false,
            metric: 'conversion',
            metric_values: conversionLabels,
            metric_type: 'Label'
          },
          {
            name: 'Stage Paths',
            selected: false,
            metric: 'stage-paths',
            metric_values: null,
            metric_type: 'Label'
          },
          {
            name: 'Paths',
            selected: false,
            metric: 'paths-comparison',
            metric_values: null,
            metric_type: 'Boolean'
          }
        ];

        var initParams = function (analysisFilters) {
          try {
            scope.flags = resetFlags();
            extraParams = scope.analysisExtraParams;
            filters = analysisFilters || scope.analysisFilters;
            init();
          } catch (e) {
            console.error(e);
            scope.analyzing = false;
          }
        };

        var init = function () {
          scope.funnelData = {};
          scope.selectedNodes = null;

          scope.analyzing = false;
          scope.results = {};
          scope.labels = [];
          scope.sliderValue = [];
          scope.resultMetric ='';

          resetAnalysisParams();

          scope.builtReports = AnalysisService.getReports();

          scope.showLimit = 3;

          scope.exclude(scope.selectedMetric);
        };

        function resetAnalysisParams() {
          scope.metrics = extraParams.metrics;

          if (extraParams.application === Apps.JA) {
            scope.metrics = scope.metrics.concat(ja_standard_metrics);
          }
          scope.selectedMetric = scope.metrics[0];
          scope.reportName = scope.selectedMetric.metric + '_Report';

          if (scope.selectedMetric.metric_type === 'Numeric') {
            scope.selectedMetric.step = getStep();
          }
          scope.updateBuckets(scope.selectedMetric.metric_values_range);
        }

        function getStep() {
          return Math.floor(scope.selectedMetric.metric_values_range[1] / 20) <= 1 ? 1 : 10;
        }

        function pushToReports(res) {
          scope.analyzing = false;
          var report = _.extend(res.item, {
            name: res.item.title,
            type: 'report',
            sref: extraParams.sref + '(' + JSON.stringify({id: res.item.id}) + ')'
          });

          AnalysisReport.buildReport(report, function (rep) {
            report = rep.report;
            report.tabs = rep.tabs;
            report.metric_buckets = rep.report.metric_values;

            if (rep.metricData) {
              report.metricData = rep.metricData;
            }

            AnalysisService.unshiftReport(report);  // to show reports in Analysis Reports
          });
        }

        function analyze(params) {
          new AnalysisRest().run(params)
            .success(function (res) {
              reportId = res.item.id;
              if (_.isEmpty(res.item.results)) {
                getReport(res.item.id);
              } else {
                pushToReports(res);
              }
            }).error(function (err) {
            scope.analyzing = false;
          })
        }

        function getReport(id) {
          if (!scope.analyzing) return;
          Analysis.getOne(id)
            .success(function (res) {
              if (_.isEmpty(res.item.results)) {
                if (res.item.status[0] === 'error') {
                  SystemAlert.error(res.item.status_message);
                  Analysis.remove(res.item.id).then(loadReports);
                  scope.analyzing = false;
                  return;
                }
                if (scope.analyzing) {
                  var debounce = _.debounce(function () {
                    getReport(id);
                  }, 2000); // each 2 secs
                  debounce();
                }
              } else {
                pushToReports(res);
              }
            });
        }

        function resetFlags() {
          return {
            showLabels: false,
            showSlider: false
          }
        }

        function showMessage(res) {
          var msg = res.message || (res.data && res.data.message) || (res.item && res.item.message);
          SystemAlert.success(msg);
          return res;
        }

        scope.stop = function () {
          Analysis.stop(reportId)
            .success(function (res) {
              scope.analyzing = false;
              Analysis.remove(reportId).then(showMessage).then(loadReports);
            })
        };

        scope.analyze = function () {
          scope.analyzing = true;

          if (angular.isDefined(scope.selectedMetric)) {
            scope.selectedMetric.metric_values = getMetricValues();

            if (!scope.selectedMetric.metric_values || !scope.selectedMetric.metric_values.length) {
              return;
            }

            var params = {
              filters: filters,
              analyzed_metric: scope.selectedMetric.metric,
              metric_type: scope.selectedMetric.metric_type,
              metric_values: scope.selectedMetric.metric_values,
              metric_values_range: scope.selectedMetric.metric_values_range,
              title: scope.reportName,
              application: extraParams.application,
              analysis_type: getAnalysisType()
            };

            var from = filters.from,
              to = filters.to;

            if (extraParams.application == Apps.JA) {
              from = moment(filters.from).format('YYYY-MM-DD HH:mm:ss');
              to = moment(filters.to).format('YYYY-MM-DD HH:mm:ss')
            } else {
              from = moment(filters.from).format('L');
              to = moment(filters.to).format('L')
            }

            _.extend(params.filters, {
              from: from,
              to: to,
              timerange: [moment(from).unix(), moment(to).unix()]
            });

            if (scope.selectedMetric.metric === 'stage-paths') {
              _.extend(params.filters, {
                labeling_strategy: extraParams.labelStrategy
              })
            }

            if (scope.selectedMetric.metric === 'conversion' && scope.funnelData) {
              params.filters['funnel_id'] = scope.funnelData.funnel_id;
              params.filters['stage_id'] = scope.funnelData.stage_id;
            }

            // params.filters['level'] = FilterService.getSelectedLevel();
            analyze(params);
          }
        };

        scope.openReportPage = function (reportId) {
          $state.go(extraParams.sref, {id: reportId});
        };

        scope.$on('DELETE_BUILT_REPORTS', function (e, report) {
          if (report) {
            _.remove(scope.builtReports, {id: report.id});
          }
        });

        scope.$on('FACETS_CHANGED', function () {
          initParams();
        });

        scope.$on("OnNodesSelected", function (data, obj) {
          scope.selectedNodes = obj;
          scope.selectedMetric = _.find(scope.metrics, {metric: 'stage-paths'});
          scope.exclude(scope.selectedMetric);
        });

        $rootScope.$on('OnPathsSelected', function (e, paths) {
          angular.element('#analysis').show('fast');
          scope.selectedPaths = _.map(paths, function (p) {
            var node_events = [];
            var metric_value;

            _.each(p.stages, function(s) {
              node_events.push(_.pluck(s.nodes, 'name'));
            });

            if (p.group_by === 'most_common_path') {
              metric_value = p.metrics.percentage.value;
            } else {
              metric_value = p.metrics[p.group_by].value;
            }

            var metrics = [];
            _.each(_.keys(p.metrics), function (k) {
              var v = p.metrics[k].value;
              if (v !== 0) {
                metrics.push(_.object([k], [v]));
              }
            });

            return {
              metrics: _.flatten(metrics),
              path: p.group_by,
              metric_value: parseFloat(metric_value),
              measure: p.measure || 'max'
            };
          });
          scope.selectedMetric = _.find(scope.metrics, {metric: 'paths-comparison'});
          scope.exclude(scope.selectedMetric);
        });

        scope.$on('ANALYSIS_FUNNEL_SELECTED', function (obj, data) {
          scope.selectedMetric = _.find(scope.metrics, {metric: 'conversion'});
          scope.funnelData = data.funnelData;
          scope.exclude(scope.selectedMetric);
        });

        scope.exclude = function (selected) {
          scope.flags = resetFlags();
          scope.resultMetric = null;

          $timeout(function () {
            scope.selectedMetric = selected;
            if (selected.metric_type === 'Numeric') {
              scope.flags.showSlider = true;
              scope.selectedMetric.step = getStep();
              scope.updateBuckets(scope.selectedMetric.metric_values_range);
            } else if (selected.metric_type === 'Label') {
              if (selected.metric === 'stage-paths') {
                scope.flags.showPathsSelection = true;
                scope.labels = [];
              } else if (selected.metric === 'paths-comparison') {
                scope.labels = [];
              } else if (selected.metric === 'conversion') {
                scope.flags.showLabels = true;
                scope.flags.showConversionSelection = true;
                scope.labels = conversionLabels;
              } else {
                scope.flags.showLabels = true;
                scope.labels = _.map(selected.metric_values, function (m) {
                  return {name: m, checked: true};
                });
              }
            }
            scope.reportName = selected.metric + '_Report';
          }, 100);
        };

        scope.updateBuckets = function (metric_values) {
          var min = scope.selectedMetric.metric_values_range[0],
            max = scope.selectedMetric.metric_values_range[1],
            step = scope.selectedMetric.step;

          scope.sliderValue = metric_values;
          var nVal = metric_values;
          var result = '';

          // TODO[sabr]: This should be moved out to the service
          if (nVal[0] !== min) {
            result += min + ' - ' + nVal[0] + ' | ';
            if (_.uniq(nVal).length !== 1) {
              result += (nVal[0] + step) + ' - ' + nVal[1];
            }
          } else {
            result += nVal[0] + ' - ' + nVal[1];
          }

          if (nVal[1] !== max) {
            if ((nVal[1] + step) !== max) {
              result += ' | ' + (nVal[1] + step) + ' - ' + max;
            } else {
              result += ' | ' + max;
            }
          }

          scope.selectedMetric.metric_values = nVal;
          scope.resultMetric = result;
        };

        function validatePath() {
          return (scope.selectedPaths && scope.selectedPaths.length === 2 && _.pluck(scope.selectedPaths, 'measure').length === 2);
        }

        function getMetricValues() {
          if (scope.selectedMetric.metric === 'paths-comparison') {
            var validation = validatePath();
            if (!validation) {
              toaster.pop('error', 'No selection to compare: please select at least 2 paths for running comparative analysis');
              scope.analyzing = false;
              return;
            }
            return scope.selectedPaths;
          } else if (scope.selectedMetric.metric === 'stage-paths') {
            if (!scope.selectedNodes || _.isEmpty(scope.selectedNodes)) {
              toaster.pop('error', 'No selection to compare: please select at least 2 stages for running comparative analysis');
              scope.analyzing = false;
              return;
            }
            return scope.selectedNodes;
          } else if (scope.selectedMetric.metric === 'conversion') {
            if (_.every(scope.labels, function (l) { return !l.checked; })) {
              toaster.pop('error', 'No labels selected: please select at least 1 label');
              scope.analyzing = false;
              return;
            }
            return _.pluck(_.where(scope.labels, {checked: true}), 'name');
          } else if (scope.selectedMetric.metric_type === 'Boolean') {
            return ['true', 'false'];
          } else if (scope.selectedMetric.metric_type === 'Numeric') {
            return scope.sliderValue.toString().split(',')
          } else if (scope.selectedMetric.metric_type === 'Label') {
            return _.pluck(_.where(scope.labels, {checked: true}), 'name');
          }
        }

        function getAnalysisType() {
          var CLASSIFICATION = 'classification',
            REGRESSION = 'regression';

          if (scope.flags.showSlider) {
            var diff = Utils.compareArrays(scope.sliderValue, scope.selectedMetric.metric_values_range);
            if (diff) {
              return REGRESSION;
            } else {
              return CLASSIFICATION;
            }
          } else {
            return CLASSIFICATION;
          }
        }

        initParams();

        scope.$watch('analysisFilters', function (nVal) {
          if (!nVal) return;
          filters = nVal;
        }, true);

        scope.$on('ANALYSIS_PARAMS_CHANGED', function (e, data) {
          extraParams = data;
          resetAnalysisParams();
        });
      }
    }
  }
  analysisPanel.$inject = ["AnalysisRest", "AnalysisReport", "$state", "$rootScope", "SystemAlert", "MetadataService", "Utils", "$timeout", "AnalysisService", "toaster"];
})();

(function() {
  'use strict';

  angular
    .module('slr.chart', [
      'ark-components',
      'ngAnimate'
    ]);
})();
(function () {
  'use strict';

  angular
    .module('slr.chart')
    .factory('ChartFactory', ChartFactory);

  /** @ngInject */
  function ChartFactory(Utils) {

    // ------------------------------------------
    // Parse "Metrics" data response for Predictors
    //
    var parseMetricsData = function (response) {
      return _.map(response, function (item) {
        return {
          'key': item.label,
          'values': item.data
        };
      });
    };

    var d3Call = function (dom, data, chart, callback) {
      try {
        d3.select(dom)
          .datum(data)
          .transition().duration(350)
          .call(chart);
      } catch (e) {
        console.error(e);
        callback(true);
      }
    };

    // -----------------------------------------
    // Parse "Trends" data
    //
    var parseTrendsData = function (response) {
      var plot_d3_data = _.map(response, function (item) {
        return {key: item.label.toLowerCase(), values: item.data}
      });

      // Unify the timestamps for all stacks in case of multiple stacks
      // Add 0 values for missing timestamps
      // Number of data points may vary per stacks which results in d3 error
      if (plot_d3_data.length > 1) {
        var timestamps = [];
        _.each(plot_d3_data, function (series) {
          _.each(series.values, function (point) {
            timestamps.push(point[0]);
          })
        });
        timestamps = _.chain(timestamps)
          .uniq()
          .sortBy(function (n) {
            return n;
          })
          .value();

        _.each(plot_d3_data, function (series) {
          var newValues = [];
          _.each(timestamps, function (time) {
            var newPoint = _.find(series.values, function (point) {
              return point[0] == time;
            });
            if (!newPoint) newPoint = [time, 0];
            newValues.push(newPoint);
          });
          series.values = newValues;
        });
      }

      return plot_d3_data;
    };

    var setXAxisTimeFormat = function (chart, level) {
      switch (level) {
        case('hour'):
          chart.xAxis.tickFormat(function (d) {
            return d3.time.format('%a, %I %p')(new Date(d))
          });
          break;
        case('day'):
          chart.xAxis.tickFormat(function (d) {
            return d3.time.format('%d %b')(new Date(d))
          });
          break;
        case('month'):
          chart.xAxis.tickFormat(function (d) {
            return d3.time.format('%B')(new Date(d))
          });
          break;
        default:
          chart.xAxis.tickFormat(function (d) {
            return moment(d).calendar();
          });
      }
    };

    // -----------------------------------------
    // Colors
    //
    var genesysColors = ["#2E69DB", "#5E99FF", "#9BBCE0", "#5A6B8C", "#0F6A51", "#569180", "#14819C",
      "#7EC0C2", "#AFD6D2", "#584FB3", "#7272E0", "#B9B9F0", "#575746", "#827C75", "#C9C4B7", "#8C6542",
      "#8A4D67", "#C48C88", "#EBC8BE", "#724787", "#B07EC2", "#D1B4D9"];
    var ordinalColors = ['#4AC764', '#EA4F6B', '#F8A740', '#203B73'].concat(genesysColors); // green, red, orange, blue

    var getDefinedColors = function (d, i) {
      var k = d.label || d.key;

      var nps = ["promoter", "passive", "detractor"];
      var status = ["converted", "stuck", "abandoned"];
      var process = ["finished", "ongoing", "abandoned"];
      var sentiments = ["positive", "neutral", "negative"];

      function getColor(arr, value) {
        var colors = d3.scale.ordinal()
          .domain(arr)
          .range(['#4AC764', '#F8A740', '#EA4F6B']); // green, orange, red
        return colors(value);
      }

      if (nps.indexOf(k) >= 0) {
        return getColor(nps, k);
      } else if (status.indexOf(k) >= 0) {
        return getColor(status, k);
      } else if (process.indexOf(k) >=0){
        return getColor(process, k);
      } else if (sentiments.indexOf(k) >= 0) {
        return getColor(sentiments, k);
      } else {
        return ordinalColors[i] || '#'+(Math.random()*0xFFFFFF<<0).toString(16);
      }
    };

    var getGenesysColors = function () {
      return genesysColors;
    };

    var getOrdinalColors = function () {
      return ordinalColors;
    };

    var setTimeTooltip = function(chart, yFormat) {
      chart.interactiveLayer.tooltip.contentGenerator(function (data) {
        var series = data.series;
        var tpl = '<h5 style="padding-left: 5px;"><b>' + moment(data.value).calendar() + '</b></h5>';
        tpl += '<table><tbody>';
        var percentage = '';
        if (!yFormat) {
          percentage = '%';
        }

        _.each(series, function (d, i) {
          tpl += '<tr>' +
            '<td class="legend-color-guide"><div style="background-color:' + getDefinedColors(d, i) + ';"></div></td>' +
            '<td class="key">' + d.key + '</td>' +
            '<td class="value">' + Utils.roundUpTo2precision(d.value) + percentage + '</td>' +
            '</tr>'
        });

        tpl += '</tbody></table>';
        return tpl;
      });
    };

    var getFilterValue = function (chart, scope, timestamp, mouseY) {
      console.log('scope.chartData', scope.chartData);
      console.log('scope.level', scope.level);
      console.log('scope.settings', scope.settings);
      console.log('timestamp', timestamp);
      console.log('mouseY', mouseY);

      var yScale = chart.yAxis.scale();
      var pointYValue = yScale.invert(mouseY);
      console.log('pointYValue', pointYValue);

      // find the index of clicked point in the x-axis data
      var xIndex = -1;
      var verticalGapSecond = scope.level === 'day' ? 24 * 3600 * 1000 : 3600 * 1000;
      console.log('verticalGapSecond', verticalGapSecond);

      _.each(scope.chartData[0].data, function (data, idx) {
        if (Math.abs(data[0] - timestamp) < verticalGapSecond) {
          xIndex = idx;
          return false;
        }
      });

      if (xIndex === -1) {
        console.log("xIndex not found.");
        return;
      }
      console.log('xIndex', xIndex);

      // find active legends to match with series label name in chartData
      // use case-insensitive matching
      var selectedLegends = angular.element('svg g.nv-legendWrap g.nv-series')
        .has('circle[style*="fill-opacity: 1"]')
        .map(function (idx, series) {
          var elm = angular.element(series);
          var legend = elm.find('title');
          if (!legend.length) {
            legend = elm.find('text');
          }
          return legend.text().toLowerCase();
        })
        .toArray();
      console.log('selectedLegends', selectedLegends);

      // find the y-values at the point of click (same as seen on tooltip)
      var clickedVerticalLineValues = _.chain(scope.chartData)
        .filter(function (series) {
          return selectedLegends.indexOf(series.label.toLowerCase()) >= 0;
        })
        .map(function (series) {
          return series.data[xIndex][1];
        })
        .value();
      console.log('clickedVerticalLineValues', clickedVerticalLineValues);

      var hotspotYCoordinates = [];
      var chartType = scope.settings.chart_type;
      if (chartType === 'LINE') {
        hotspotYCoordinates = clickedVerticalLineValues;
      } else if (chartType === 'STACKED') {
        var base = 0;
        hotspotYCoordinates = _.map(clickedVerticalLineValues, function (y) {
          base += y;
          return base;
        });
      } else {
          throw Error("Couldn't compute filter value for chart type '" + scope.settings.chart_type + "'.");
      }
      console.log('hotspotYCoordinates', hotspotYCoordinates);

      // find the height of the current graph in the same unit as that of y-axis
      var highestYCoordinates = [];
      var rowVectors = _.chain(scope.chartData)
        .filter(function (series) {
          return selectedLegends.indexOf(series.label.toLowerCase()) >= 0;
        })
        .map(function (series) {
          return _.map(series.data, function (elm) {
            return elm[1];
          });
        })
        .value();
      console.log('rowVectors', rowVectors);

      _.each(rowVectors, function (vector) {
        if (!highestYCoordinates.length) {
          highestYCoordinates = vector;
        } else {
          for (var i = 0; i < vector.length; i++) {
            if (chartType === 'LINE') {
              highestYCoordinates[i] = Math.max(highestYCoordinates[i], vector[i]);
            } else if (chartType === 'STACKED') {
              highestYCoordinates[i] += vector[i];
            }
          }
        }
      });
      console.log('highestYCoordinates', highestYCoordinates);

      var graphHeight = Math.max.apply(Math, highestYCoordinates);
      console.log('graphHeight', graphHeight);
      // find the radius of the hotspot circle ~ 6px
      var hotspotRadius = graphHeight - yScale.invert(6);
      console.log('hotspotRadius', hotspotRadius);

      var legendIndex = -1;
      _.each(hotspotYCoordinates, function (y, i) {
        // tooltip won't show highlighting, so treat whole data point as same region
        // if highlighting would work (as with data with 3 or more series),
        // north hemisphere of data point would lie in upper region, while south one in lower region
        var tolerance = selectedLegends.length <= 2 ? hotspotRadius : 0;
        if (pointYValue - y <= tolerance) {
          legendIndex = i;
          return false;
        }
      });
      console.log('legendIndex', legendIndex);

      if (legendIndex === -1) {
        // Regard click on the hotspot circle at the top most data series as the
        // click on data point, though highlighting in tooltip will not 'highlight' the series label
        if (pointYValue - hotspotYCoordinates[hotspotYCoordinates.length - 1] <= hotspotRadius) {
          legendIndex = clickedVerticalLineValues.length - 1;
        } else {
          console.log("Couldn't detect the series.");
          return;
        }
      }
      console.log('legendIndex', legendIndex);

      var legend = selectedLegends[legendIndex];
      console.log('legend', legend);

      var chartDataSeries = _.find(scope.chartData, function (series) {
        if (legend === series.label.toLowerCase()) {
          return series;
        }
      });
      console.log('chartDataSeries', chartDataSeries);

      var filterValue = chartDataSeries._internalLabel || chartDataSeries.label;
      console.log('filterValue', filterValue);
      return filterValue;
    };

    return {
      parseTrendsData: parseTrendsData,
      parseMetricsData: parseMetricsData,
      getGenesysColors: getGenesysColors,
      getOrdinalColors: getOrdinalColors,
      getDefinedColors: getDefinedColors,
      d3Call: d3Call,
      setXAxisTimeFormat: setXAxisTimeFormat,
      setTimeTooltip: setTimeTooltip,
      getFilterValue: getFilterValue
    }
  }
  ChartFactory.$inject = ["Utils"];
})();

(function () {
  'use strict';

  angular
    .module('slr.chart')
    .factory("PlotTypes", PlotTypes);

  // Move out from here $rootScope
  function PlotTypes($rootScope, MetadataService) {
    var PlotTypes = {};

    var getPlotFiltersVisibility = function () {
      return {
        "inbound": {time: ['intention', 'topic', 'status'], share: ['intention', 'topic', 'status']},
        "outbound": {time: ['intention', 'topic', 'agent'], share: ['intention', 'topic', 'agent']},
        "response-time": {time: ['agent'], share: ['agent']},
        "response-volume": {time: ['agent'], share: ['agent']},
        "sentiment": {time: ['sentiment'], share: ['sentiment']},
        "missed-posts": {time: [], share: []},
        "inbound-volume": {time: [], share: []},
        "top-topics": {time: ['topic'], share: ['topic']},
        "customers": {share: ['segment', 'industry', 'Status', 'location', 'gender']},
        "agents": {share: ['location', 'gender']},
        "predictors": {time: ['Mean Error', 'Mean Latency', 'Mean Reward']}
      };
    };

    var plot_filters = MetadataService.getPlotFilters();

    // plot types
    var plot_types = [
      {type: 'time', enabled: true, label: 'Trends'},
      {type: 'share', enabled: false, label: 'Distribution'}
    ];
    var plot_stats_type = "";
    var plot_location = "inbound";

    PlotTypes.ON_PLOT_TYPE_CHANGE = 'on_plot_type_change';
    PlotTypes.ON_PLOT_GET_ACTIVE = 'on_plot_get_active';
    PlotTypes.ON_PLOT_FILTER_CHANGE = 'on_plot_filter_change';
    PlotTypes.ON_PLOT_REPORT_CHANGE = 'on_plot_report_change';

    var setPlotTypeOrFilter = function (which, type, silent) {
      var list = which == 'plot' ? plot_types : plot_filters;
      var plot_event = which == 'plot' ? PlotTypes.ON_PLOT_TYPE_CHANGE : PlotTypes.ON_PLOT_FILTER_CHANGE;
      angular.forEach(list, function (val) {
        val.enabled = (val.type === type);
      });
      if (typeof silent === 'undefined') {
        $rootScope.$broadcast(plot_event)
      }
    };

    PlotTypes.setType = function (type, silent) {
      setPlotTypeOrFilter('plot', type, silent);
    };

    PlotTypes.setFilter = function (type, silent) {
      setPlotTypeOrFilter('filter', type, silent);
    };

    PlotTypes.resetPlotFilters = function () {
      _.each(plot_filters, function (item) {
        item.enabled = false
      });
    };

    PlotTypes.updatePlotTypes = function (newTypes) {
      if (newTypes)
        plot_types = newTypes;
    };

    PlotTypes.setPlotTypes = function (plotTypes) {
      plot_types = plotTypes;
      return plot_types;
    };

    PlotTypes.getActiveType = function () {
      return _.filter(plot_types, function (el) {
        return el.enabled == true
      })[0]['type'];
    };

    PlotTypes.getActiveFilter = function () {
      var active_filter = _.filter(plot_filters, function (el) {
        return el.enabled == true
      });
      return active_filter.length > 0 ? active_filter[0]['type'] : null;
    };

    PlotTypes.getList = function () {
      return plot_types;
    };

    PlotTypes.getPage = function () {
      return plot_location;
    };

    PlotTypes.setPage = function (page) {
      plot_location = page;
      $rootScope.$broadcast(PlotTypes.ON_PLOT_REPORT_CHANGE);
    };

    PlotTypes.getYAxisLabel = function (page) {
      var section = page ? page : PlotTypes.getPage();
      var label = {
        'inbound': 'Posts',
        'outbound': 'Responses',
        'response-time': 'Response Time',
        'response-volume': 'Responses',
        'sentiment': 'Posts',
        'inbound-volume': 'Posts',
        'top-topics': 'Posts',
        'missed-posts': 'Posts'
      }[section];
      return label;
    };

    PlotTypes.getDefaultLegendLabel = function (page) {
      var section = page ? page : PlotTypes.getPage();
      var label = {
        'inbound': 'Posts',
        'outbound': 'Responses',
        'response-time': 'Average Response Time',
        'response-volume': 'All Responses',
        'sentiment': 'Number of Posts',
        'inbound-volume': 'Number of Posts',
        'top-topics': 'Number of Posts',
        'missed-posts': 'Number of Posts'
      }[section];
      return label;
    };

    PlotTypes.getFilters = function (plot_type) {
      var page = PlotTypes.getPage();
      plot_type = PlotTypes.getActiveType();
      if (!page || !plot_type) return [];

      var visibility = getPlotFiltersVisibility();
      return _.filter(plot_filters, function (item) {
        return _.contains(visibility[page][plot_type], item.type);
      });
    };

    PlotTypes.setPlotStatsType = function (type) {
      //return termStats or channelStats to indicate which plot is currently shown
      plot_stats_type = type
    };

    PlotTypes.getPlotStatsType = function () {
      return plot_stats_type
    };

    PlotTypes.isAverageTimeReport = function () {
      return PlotTypes.getActiveType() == 'time' && PlotTypes.getPage() == 'response-time';
    };

    return PlotTypes
  }
  PlotTypes.$inject = ["$rootScope", "MetadataService"];
})();
(function () {
  'use strict';
  angular
    .module('slr.chart')
    .directive('chart', chart);

  // TODO: 1) sankey requires some flexibility, it is very tied to Journeys
  //       2) funnels should be placed here too from omni...funnels.js with flexibile data structure
  //       3) drilldowns should be flexible too - they are tied to the specific event name

  /**
   * Settings may include:
   * @chart_type: PIE / STACKED / LINE / SANKEY / SCATTER / BOXPLOT / BAR / MULTICHART / DISCRETEBAR / LINEBAR
   * @yAxisFormat: String
   * @yAxisLabel: String
   * @xAxisFormat: String
   * @xAxisLabel: String
   * @valueFormat: String
   * @isMetric: Boolean
   * @level: hour / day / month
   * @xAxisLabel: String
   * @target: OMNI_CUSTOMERS / OMNI / OMNI_AGENTS / ANALYTICS / REPORTS / PREDICTORS
   * @drilldownEnabled: Boolean
   * @labelType: String
   * @active_filter: Object
   * @stacked: Boolean
   * @computed_metric: csat
   */

  /** @ngInject */
  function chart($rootScope, $window, ChartFactory, Utils, PlotTypes, FilterService) {
    return {
      restrict: 'E',
      replace: false,
      scope: {
        chartData: '=',
        settings: '='
      },
      template: '<svg ng-show="chartData.length || chartData.links.length"></svg>' +
      '<div class="alert alert-info text-center" ng-hide="chartData.length || chartData.links.length">' +
      '<i class=\'icon-alert-triangle\'></i> ' + '{{settings.noDataMsg || "No Data Available"}}' +
      '</div>',
      link: function (scope, element) {

        scope.$watch('chartData', function (newData) {
          if (!newData) return;

          var chartType;

          if (scope.settings) {
            chartType = scope.settings.chart_type;
          }

          switch (chartType) {
            case('PIE'):
              drawPieChart();
              break;
            case('STACKED'):
              drawStackedChart();
              break;
            case('LINE'):
              drawLineChart();
              break;
            case('SANKEY'):
              drawSankeyChart();
              break;
            case('SCATTER'):
              drawScatterChart();
              break;
            case('BOXPLOT'):
              drawBoxChart();
              break;
            case('BAR'):
              drawBarChart();
              break;
            case('MULTICHART'):
              drawMultiChart();
              break;
            case('DISCRETEBAR'):
              drawDiscreteBar();
              break;
            case('LINEBAR'):
              drawLineBar();
              break;
          }
        });

        var drilldown = function (type, params, target) {
          if (target == 'REPORTS') {
            var group_by = PlotTypes.getActiveFilter();
            if (group_by) {
              params.filterName = group_by + 's';
            }
            scope.$emit('reports.details.' + type, params);
          } else if (target == 'ANALYTICS') {
            scope.$emit('analytics.details.' + type, params);
          } else if (target == 'OMNI') {
            params.drilldown = true;
            scope.$apply();
            scope.$emit('journeys.details.' + type, params);
          } else if (target == 'OMNI_CUSTOMERS') {
            scope.$emit('customers.details.' + type, params);
          } else if (target == 'OMNI_AGENTS') {
            scope.$emit('agents.details.' + type, params);
          } else if (target == 'PREDICTORS') {
            scope.$emit('predictors.details.' + type, params);
          }
        };

        function drawLineBar() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var yFormat = scope.settings.yAxisFormat;
            var chart = nv.models.linePlusBarChart()
                .margin({right: 50, bottom: 85, top: 50})
                .options({focusEnable: false})
                //We can set x data accessor to use index. Reason? So the bars all appear evenly spaced.
                .x(function (d, i) { return i })
                .y(function (d, i) { return d[1] });

            if (scope.settings.isMetric) {
              var Yvalues = [];
              _.each(scope.chartData, function (p) {
                if (!_.has(p, 'values')) return;
                _.each(p.values, function (v) {
                  Yvalues.push(v[1]);
                });
              });
              chart.y1Axis.ticks([_.min(Yvalues), _.max(Yvalues)]);
            }

            if (yFormat) {
              chart.y1Axis.tickFormat(d3.format(yFormat));
              chart.y2Axis.tickFormat(d3.format(yFormat));
            }

            // TODO: moveout this
            function convertTime(dx) {
              switch (scope.settings.level) {
                case('hour'):
                  return d3.time.format('%a, %I %p')(new Date(dx));
                  break;
                case('day'):
                  return d3.time.format('%d %b')(new Date(dx));
                  break;
                case('month'):
                  return d3.time.format('%B')(new Date(dx));
                  break;
                default:
                  return moment(dx).calendar();
              }
            }

            chart.xAxis.tickFormat(function (d) {
              var dx = scope.chartData[0].values[d] && scope.chartData[0].values[d][0] || 0;
              return convertTime(dx);
            });

            chart.bars.forceY([0]);

            chart.y1Axis.axisLabel('Count');

            chart.tooltip.contentGenerator(function (data) {
              var series = data.series;
              var time;
              var value;
              var color;

              if (data.data && data.data.length) {
                time = data.data[0];
                value = data.data[1];
                color = data.color;
              } else {
                time = data.point[0];
                value = data.point[1];
              }

              var tpl = '<h5 style="padding-left: 5px;"><b>' + convertTime(time) + '</b></h5>';
              tpl += '<table><tbody>';
              var percentage = '';
              if (!yFormat) {
                percentage = '%';
              }

              _.each(series, function (d, i) {
                var key;
                if (_.has(d, 'key')) {
                  key = d.key;
                } else if ((d.originalKey && 'count' in d.originalKey.toLowerCase()) || !_.has(d.key)) {
                  key = 'Count';
                }
                tpl += '<tr>' +
                  '<td class="legend-color-guide"><div style="background-color:' + d.color + ';"></div></td>' +
                  '<td class="key">' + key + '</td>' +
                  '<td class="value">' + Utils.roundUpTo2precision(d.value) + percentage + '</td>' +
                  '</tr>'
              });

              tpl += '</tbody></table>';
              return tpl;
            });

            d3.selectAll('.nvtooltip').remove();


            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);
            return chart;
          });
        }

        function drawDiscreteBar() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var parsedData;
            if (!_.has(scope.chartData[0], 'data')) {
              parsedData = [{key: 'Discrete Bar', values: scope.chartData}];
            } else {
              parsedData = ChartFactory.parseMetricsData(scope.chartData);
            }

            var chart = nv.models.discreteBarChart()
              .x(function (d) {
                return d.label;
              })
              .y(function (d) {
                return d.value;
              })
              .staggerLabels(true)
              .color(ChartFactory.getOrdinalColors())
              .showValues(true);

            if (scope.settings.valueFormat) {
              chart.valueFormat(d3.format(scope.settings.valueFormat));
            } else {
              chart.valueFormat(function (d) {
                return d + '%';
              });
            }

            if (scope.chartData.length > 10) {
              chart.showLegend(false);
            }

            chart.discretebar.dispatch.on("elementClick", function (e) {
              if (!scope.settings.drilldownEnabled) return;
              var active_filter = scope.settings.active_filter;
              var target = scope.settings.target;
              var params = {
                  filterName: active_filter,
                  filterValue: e.data._internalLabel || e.data.label
              };

              if (typeof nv.tooltip.cleanup == 'function') {
                nv.tooltip.cleanup();
              }



              d3.selectAll('.nvtooltip').remove(); // workaround for now to cleanup tooltips
              drilldown('distribution', params, target);
            });

            d3.selectAll('.nvtooltip').remove();

            ChartFactory.d3Call(dom, parsedData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);
            return chart;
          });
        }

        function drawMultiChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var parsedData = ChartFactory.parseMetricsData(scope.chartData);
            var yFormat = scope.settings.yAxisFormat;

            _.each(parsedData, function(d, i) {
              _.extend(parsedData[i], scope.settings.charts_settings[i]);
            });

            var chart = nv.models.multiChart()
              .useInteractiveGuideline(true)
              .x(function (d) { return d[0] || d['x']; })   //We can modify the data accessor functions...
              .y(function (d) { return d[1] })   //...in case your data is formatted differently.
              .margin({right: 85, bottom: 85});

            if (scope.settings.isMetric) {
              var Yvalues = [];
              _.each(scope.chartData, function (p) {
                if (!_.has(p, 'values')) return;
                _.each(p.values, function (v) {
                  Yvalues.push(v[1]);
                });
              });
              chart.yAxis1.ticks([_.min(Yvalues), _.max(Yvalues)]);
              chart.yAxis2.ticks([_.min(Yvalues), _.max(Yvalues)]);
            }

            if (yFormat) {
              chart.yAxis1.tickFormat(d3.format(yFormat));
              chart.yAxis2.tickFormat(d3.format(yFormat));
            }

            ChartFactory.setXAxisTimeFormat(chart, scope.settings.level);
            ChartFactory.setTimeTooltip(chart, yFormat);

            chart.yAxis1
              .axisLabel(scope.settings.yAxisLabel);
            chart.yAxis2
              .axisLabel(scope.settings.yAxis2Label);


            d3.selectAll('.nvtooltip').remove();

            ChartFactory.d3Call(dom, parsedData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);
            return chart;
          });
        }

        function drawLineChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var parsedData = ChartFactory.parseMetricsData(scope.chartData);
            var yFormat = scope.settings.yAxisFormat;

            var chart = nv.models.lineChart()
              .useInteractiveGuideline(true)    //Tooltips which show all data points. Very nice!
              .x(function (d) {
                return d[0];
              })   //We can modify the data accessor functions...
              .y(function (d) {
                return d[1]
              })   //...in case your data is formatted differently.
              .margin({right: 50, bottom: 85})
              .showXAxis(true)
              .showYAxis(true)
              .clipEdge(false)
              // .yDomain(scope.settings.yDomain)
              .color(function (d, i) {
                return ChartFactory.getDefinedColors(d, i)
              });

            if (scope.settings.isMetric) {
              var Yvalues = [], Xvalues = [];
              _.each(scope.chartData, function (p) {
                var values = p.values || p.data;
                if (!values) return;
                _.each(values, function (v) {
                  Yvalues.push(v[1]);
                  Xvalues.push(v[0] || v['x']);
                });
              });
              var ymin = _.min(Yvalues), ymax = _.max(Yvalues);
              chart.yAxis.ticks([ymin, ymax]);
              if (Xvalues.length > 20) {
                var xmin = _.min(Xvalues), xmax = _.max(Xvalues);
                var xmean = (xmin + xmax) * 0.5;
                chart.xAxis.tickValues([xmin, xmean, xmax]);
              }
            }

            if (yFormat && yFormat !== 's') {
              chart.yAxis.tickFormat(d3.format(yFormat))
            } else if (yFormat === 's') {
              chart.yAxis.tickFormat(function(d) {
                var format = d3.format('s');
                return format(Math.ceil(d/100)*100);
              });
            } else {
              chart.yAxis.tickFormat(function(d) {
                return d + '%';
              });
            }

            ChartFactory.setXAxisTimeFormat(chart, scope.settings.level);
            ChartFactory.setTimeTooltip(chart, yFormat);

            chart.xScale(d3.time.scale.utc());  // Align x-axis ticks exactly with actual data points

            chart.yAxis
              .axisLabel(scope.settings.yAxisLabel);

            chart.duration(0);
            d3.selectAll('.nvtooltip').remove();

            ChartFactory.d3Call(dom, parsedData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);

            return chart;
          }, function (chart) {
            chart.interactiveLayer.dispatch.on('elementClick', function (point) {
              if (!scope.settings.drilldownEnabled) return;

              var level = FilterService.getSelectedGraphLevel();
              scope.level = level;

              var start = moment.utc(point.pointXValue).startOf(level).valueOf();
              var end = moment.utc(point.pointXValue).startOf(level).add(level, 1).valueOf();
              var timestamp = moment.utc(point.pointXValue).valueOf();

              // The x-axis timestamp differs slightly form the original value
              // So select the most nearest timestamp
              if (end - timestamp > timestamp - start) {
                timestamp = start;
              } else {
                timestamp = end;
              }

              var filterValue = ChartFactory.getFilterValue(chart, scope, timestamp, point.mouseY);
              if (!filterValue) {
                return;
              }

              var target = scope.settings.target;
              var params = {
                timestamp: timestamp,
                filterName: scope.settings.active_filter,
                filterValue: filterValue
              };

              drilldown('trends', params, target);
            });
          });
        }

        function drawScatterChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var chart = nv.models.scatterChart()
              .x(function(d) { return d.x || d[0] })
              .y(function(d) { return d.y || d[1] })
              .showDistX(false)    //showDist, when true, will display those little distribution lines on the axis.
              .showDistY(false)
              .margin({bottom: 100})
              .yDomain(scope.settings.yDomain)
              .pointRange([45,50]);

            chart.tooltip.contentGenerator(function (point) {
              var header = '<h5 style="padding-left: 5px;">' + scope.settings.yAxisLabel + ': ' + point.point.y + '</h5>';
              var tpl = header + '<table><tbody>';

              tpl += '<tr>' +
                '<td class="legend-color-guide"><div style="background-color:' + point.point.color + ';"></div></td>' +
                '<td class="key">' + point.series[0].key + '</td>' +
                '<td class="value">' + Utils.roundUpTo2precision(point.point.x) + '</td>' +
                '</tr>';
              tpl += '</tbody></table>';
              return tpl;
            });

            if (scope.settings.isMetric) {
            }

            if (scope.settings.categorized) {
              chart.color(function (d, i) {
                return ChartFactory.getOrdinalColors()[i];
              });
            } else {
              chart.color(['#203B73']); // all points/bubbles are blue color
            }

            if (scope.chartData.length > 10) {
              chart.showLegend(false);
            }

            //Axis settings
            chart.xAxis.tickFormat(d3.format('.0f'))
              .axisLabel(scope.settings.xAxisLabel);
            chart.yAxis.axisLabel(scope.settings.yAxisLabel);

            chart.duration(0);

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            return chart;
          });
        }

        function drawBoxChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var chart = nv.models.boxPlotChart()
              .x(function (d) {
                return d.label || d.key;
              })
              .margin({bottom: 100})
              .staggerLabels(true)
              .showXAxis(false)
              .maxBoxWidth(75) // prevent boxes from being incredibly wide
              .yDomain(scope.settings.yDomain)
              ;

            if (scope.settings.isMetric) {
              chart.yAxis.tickFormat(d3.format(scope.settings.yAxisFormat));
            }

            if (scope.settings.categorized) {
              chart.color(function (d, i) {
                return ChartFactory.getOrdinalColors()[i];
              });
            } else {
              chart.color(['#203B73']); // all points/bubbles are blue color
            }

            chart.yAxis.axisLabel(scope.settings.yAxisLabel);

            if (scope.settings.showXAxis) {
              if (scope.chartData.length > 40) {
                chart.showXAxis(false);
              } else {
                chart.showXAxis(true);
              }
            }

            if (scope.settings.xAxisFormat) {
              chart.xAxis.tickFormat(d3.format(scope.settings.xAxisFormat));
            }

            chart.duration(0);

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            return chart;
          });
        }

        // -------------------------
        // Draw "Distribution" chart
        //
        function drawPieChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          var target = scope.settings.target;

          nv.addGraph(function () {
            var chart = nv.models.pieChart()
              .x(function (d) {
                if (_.has(d, 'label')) {
                  return d.label.toLowerCase();
                } else {
                  return d.key.toLowerCase();
                }
              })
              .y(function (d) {
                var value = 0;
                if (!_.has(d, 'value')) {
                  return d.data[0][1];
                }
                if (d.value) {
                  if (_.has(d.value, 'sum')) {
                    return d.value.sum;
                  } else {
                    return d.value;
                  }
                } else if (d.data && angular.isArray(d.data)) {
                  value = d.data[0][1];
                }
                return value;
              })
              .margin({bottom: 100})
              .showLabels(true)     //Display pie labels
              .labelsOutside(true)
              .labelThreshold(.05)  //Configure the minimum slice size for labels to show up
              // .labelType('percent') //Configure what type of data to show in the label. Can be "key", "value" or "percent"
              .color(ChartFactory.getOrdinalColors())
              .legendPosition('top');

            chart.labelType(scope.settings.labelType || 'percent');

            if (scope.settings.valueFormat) {
              chart.valueFormat(d3.format(scope.settings.valueFormat));
            } else {
              chart.valueFormat(function (d) {
                return d + '%';
              });
            }

            if (scope.chartData.length > 10) {
              chart.showLegend(false);
            }

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            // if (scope.settings.tooltipSpecialKey) {
            //   chart.tooltip.contentGenerator(function (point) {
            //     var header = '<h5 style="padding-left: 5px;">' + point.data.label + '</h5>';
            //     var tpl = header + '<table><tbody>';
            //
            //     tpl += '<tr>' +
            //       '<td class="legend-color-guide"><div style="background-color:' + point.color + ';"></div></td>' +
            //       '<td class="key">' + scope.settings.tooltipSpecialKey.label + ': ' + '</td>' +
            //       '<td class="value">' + Utils.roundUpTo2precision(point.data[scope.settings.tooltipSpecialKey.key]) + '</td>' +
            //       '</tr>';
            //     tpl += '</tbody></table>';
            //     return tpl;
            //   });
            // }

            // DRILLDOWN
            chart.pie.dispatch.on("elementClick", function (e) {
              if (!scope.settings.drilldownEnabled) return;
              var active_filter = scope.settings.active_filter;
              var params = {
                  filterName: active_filter,
                  filterValue: e.data._internalLabel || e.data.label
              };

              if (typeof nv.tooltip.cleanup == 'function') {
                nv.tooltip.cleanup();
              }

              d3.selectAll('.nvtooltip').remove(); // workaround for now to cleanup tooltips

              drilldown('distribution', params, target);
            });

            // Disable grow on hover of a slice
            // @ https://github.com/novus/nvd3/issues/884
            chart.growOnHover(false);
            return chart;
          });
        }

        function drawBarChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;


          nv.addGraph(function () {
            var chart = nv.models.multiBarChart()
              .reduceXTicks(false)   //If 'false', every single x-axis tick label will be rendered.
              .showXAxis(true)
              .rotateLabels(0)      //Angle to rotate x-axis labels.
              .showControls(scope.settings.stacked)   //Allow user to switch between 'Grouped' and 'Stacked' mode.
              .stacked(scope.settings.stacked)
              // .interpolate("linear") // don't smooth out the lines
              .groupSpacing(0.5)    //Distance between each group of bars.
              .margin({bottom: 100})
              ;

            if (!scope.settings.stacked) {
              chart.x(function(d) { return d.label});
              chart.y(function(d) { return d.count});
            }

            if (scope.chartData[0] && scope.chartData[0].values.length > 10 && scope.chartData[0].values.length <= 20) {
              chart.margin({bottom: 130});
              // chart.showLegend(false);
              d3.selectAll("g.tick.zero text")
                .style("text-anchor", "end")
                .attr("dx", "-.8em")
                .attr("dy", ".15em")
                .attr("font-size", "12px")
                .attr("transform", "rotate(-45)");
            } else if (scope.chartData[0].values.length > 20) {
              // chart.showLegend(false);
              chart.showXAxis(false);
            } else if (scope.chartData.length === 1) {
              chart.showLegend(false);
            } else {
              chart.margin({bottom: 100});
            }

            chart.color(function (d, i) {
              return ChartFactory.getDefinedColors(d, i);
            });

            if (scope.settings.isMetric) {
              var Xvalues = [], Yvalues = [];
              _.each(scope.chartData, function (p) {
                if (!_.has(p, 'values')) return;
                _.each(p.values, function (v) {
                  Xvalues.push(v['x'] || v[0]);
                  Yvalues.push(v['y'] || v[1]);
                });
              });
              chart.xAxis.ticks([_.min(Xvalues), _.max(Xvalues)]);
              chart.yAxis.ticks([_.min(Yvalues), _.max(Yvalues)]);
            }

            if (scope.settings.yAxisFormat) {
              chart.yAxis.tickFormat(d3.format(scope.settings.yAxisFormat))
            } else {
              chart.yAxis.tickFormat(function (d) {
                return d + '%'
              });
            }

            if (scope.settings.xAxisFormat) {
              chart.xAxis.tickFormat(d3.format(scope.settings.xAxisFormat));
            }

            chart.yAxis.axisLabel(scope.settings.yAxisLabel);
            chart.xAxis.axisLabel(scope.settings.xAxisLabel);

            chart.duration(0);

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });
            return chart;
          });
        }

        // -------------------
        // Draw "Stacked Area" chart
        //
        function drawStackedChart() {
          var stackedChartViewMode = 'stack';
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          var parsedData;
          var target = scope.settings.target;
          if (target == 'OMNI') {
            parsedData = ChartFactory.parseTrendsData(scope.chartData);
          } else if (['ANALYTICS', 'PREDICTORS', 'REPORTS', 'JOBS'].indexOf(target) >= 0) {
            parsedData = ChartFactory.parseMetricsData(scope.chartData);
          }

          nv.addGraph({
            generate: function () {
              var chart = nv.models.stackedAreaChart()
                .useInteractiveGuideline(true)    //Tooltips which show all data points. Very nice!
                .margin({right: 50})
                .x(function (d) {
                  return d[0]
                })   //We can modify the data accessor functions...
                .y(function (d) {
                  return d[1]
                })   //...in case your data is formatted differently.
                .showXAxis(true)
                .showYAxis(true)
                .clipEdge(false)
                .style(stackedChartViewMode)
                .color(function (d, i) {
                  return ChartFactory.getDefinedColors(d, i)
                });

              chart.showControls(false);  // hide controls and display only Stacked graph
              //chart._options.controlOptions = ['Stacked'];  // hide 'Stream' and 'Expanded' options

              //Format x-axis labels with custom function.
              //chart.xAxis
              //  .showMaxMin(false)
              //.tickValues(d3.range(chart.xAxis.scale().domain()[1], chart.xAxis.scale().domain()[1]));

              ChartFactory.setXAxisTimeFormat(chart, scope.settings.level);

              chart.xScale(d3.time.scale.utc());  // Align x-axis ticks exactly with actual data points

              chart.yAxis
                .axisLabel(scope.settings.yAxisLabel);

              var yAxisFormat = scope.settings.yAxisFormat;

              if (!yAxisFormat) {
                if (_.has(scope.settings, 'computed_metric')) {
                  yAxisFormat = ',.1f';
                } else {
                  yAxisFormat = ',.0d';
                }
              }

              chart.yAxis.tickFormat(d3.format(yAxisFormat));

              d3.select(dom).selectAll('*').remove();
              d3.selectAll('.nvtooltip').remove();

              ChartFactory.d3Call(dom, parsedData, chart, function (res) {
                if (res) {
                  scope.chartData = [];
                }
              });

              if (!scope.chartData.length) {
                d3.select('.nvd3').remove();
              }

              function disableAreaClick() {
                chart.stacked.dispatch.on("areaClick.toggle", null);

                if (chart.update) {
                  var originalUpdate = chart.update;

                  chart.update = function () {
                    originalUpdate();
                    disableAreaClick();
                  };
                }
              }

              disableAreaClick();

              nv.utils.windowResize(chart.update);

              return chart;
            },
            callback: function (chart) {
              chart.dispatch.on('stateChange', function (e) {
                stackedChartViewMode = e.style;
              });

              chart.interactiveLayer.dispatch.on('elementClick', function (point) {
                if (!scope.settings.drilldownEnabled) return;

                var level = FilterService.getSelectedGraphLevel();
                scope.level = level;

                var start = moment.utc(point.pointXValue).startOf(level).valueOf();
                var end = moment.utc(point.pointXValue).startOf(level).add(level, 1).valueOf();
                var timestamp = moment.utc(point.pointXValue).valueOf();

                // The x-axis timestamp differs slightly form the original value
                // So select the most nearest timestamp
                if (end - timestamp > timestamp - start) {
                  timestamp = start;
                } else {
                  timestamp = end;
                }

                var filterValue = ChartFactory.getFilterValue(chart, scope, timestamp, point.mouseY);
                if (!filterValue) {
                  return;
                }

                var target = scope.settings.target;
                var params = {
                  timestamp: timestamp,
                  filterName: scope.settings.active_filter,
                  filterValue: filterValue
                };

                drilldown('trends', params, target);
              });
            }
          });
        }

        // -------------------
        // Draw "Sankey" chart
        //
        function drawSankeyChart() {
          d3.selectAll('svg > *').remove();

          var dom = angular.element(element).children('svg')[0];

          var container = angular.element(element).parent().get(0);

          if (!dom) return;

          if (!scope.chartData.links) return;

          var graph = scope.chartData;  // same variable name as in journeys module
          var units = "Journeys";

          var steps = _.last(graph.nodes)['xPos'];

          var stepWithMaxNodes = _.chain(graph.nodes)
            .flatten()
            .groupBy('xPos')
            .map(function (value, key) {
              return {'step': key, 'value': value.length}
            })
            .max(function (step) {
              return step.value;
            })
            .value();

          var nodesWidth = steps > 4 ? 100 : 150;
          var nodePadding = 50; //steps > 4 ? 50 : 80;

          var widthConst = steps <= 3 ? steps * (nodesWidth * 3) : steps * (nodesWidth * 2);
          var heightConst = stepWithMaxNodes.value <= 4 ? $window.innerHeight-350 : $window.innerHeight;

          var margin = {top: 10, right: 10, bottom: 100, left: 10},
            width = widthConst - margin.left - margin.right,
            height = heightConst - margin.top - margin.bottom;

          var formatNumber = d3.format(",.0f"),    // zero decimal places
            format = function (d) {
              return formatNumber(d) + " " + units;
            },
            color = d3.scale.category20(),

            groupColor = d3.scale.ordinal()
              .domain(["Promoter", "Passive", "Detractor", "Not Present", "All"])
              .range(["green", "orange", "red", "grey", "#5E99FF"]);

          // append the svg canvas to the page
          var svg;
          if (dom) {
            svg = d3.select(dom);
          } else {
            svg = d3.select(element).append('svg');
          }
          svg
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .attr("transform",
              "translate(" + margin.left + "," + margin.top + ")");

          // Set the sankey diagram properties
          var sankey = d3.sankey()
            .nodeWidth(nodesWidth)
            .nodePadding(nodePadding)
            .size([width, height])
            .sinksRight(false);
          var path = sankey.link();

          sankey
            .nodes(graph.nodes)
            .links(graph.links)
            .layout(32);

          // add in the links
          var link = svg.append("g").selectAll(".link")
            .data(graph.links)
            .enter()
            .append("path")
            .attr("class", "link")
            .attr("d", path)
            .attr("id", function (d, i) {
              d.id = i;
              return "link-" + i;
            })
            .style("stroke-width", function (d) {
              return Math.max(1, Math.sqrt(d.dy));
              //return Math.max(1, d.dy);
            })
            .style("stroke", function (d) {
              return groupColor(d.group_name);
            })
            .style("stroke-opacity", 0.4)
            .sort(function (a, b) {
              return b.dy - a.dy;
              //return b.y - a.y;
            });

          // add the link titles
          link.append("title")
            .text(function (d) {
              var group_by = d.group_name ? d.group_name : "All"
              var label = d.source.name + " > " +
              d.target.name + "\n" + format(d.value);
              return label + "\n" + "GROUP BY: " + group_by;
            });

          // add in the nodes
          var node = svg.append("g").selectAll(".node")
            .data(graph.nodes)
            .enter().append("g")
            .attr("class", "node")
            .attr("id", makeId('node'))
            .attr("step", function (d) {
              return d.xPos;
            })
            .attr("data-clicked", 0)
            .attr("transform", function (d) {
              return "translate(" + d.x + "," + d.y + ")";
            });

          // add the rectangles for the nodes
          node.append("rect")
            .attr("y", 20)
            .attr("height", function (d) {
              if (d.dy < 20) {
                return 20
              } else {
                return d.dy;
              }
            })
            .attr("class", "stage")
            .attr("width", sankey.nodeWidth())
            .style("fill", function (d, i) {
              return d.color = '#f5f5f5'
            })
            .style("stroke", function (d) {
              return "#999"
            })
            .append("title")
            .text(function (d) {
              return d.name + "\n" + formatNumber(d.count);
            });

          //title rectangle
          node.append("rect")
            .attr("y", 0)
            .attr("height", function (d) {
              return 20
            })
            .attr("width", sankey.nodeWidth())
            .style("fill", function (d, i) {
              return d.color = d3.rgb(color(d.name.replace(/ .*/, ""))).darker(1)
            })
            .style("stroke", function (d) {
              return d3.rgb(d.color).darker(2);
            });

          // add in the title for the nodes
          node.append("text")
            .attr("class", "nodeLabel");

          node.selectAll("text.nodeLabel")
            .attr("x", 6)
            .attr("y", function (d) {
              return 10;
            })
            .attr("dy", ".35em")
            .attr("text-anchor", "start")
            .attr("transform", null)
            .text(function (d) {
              return d.name.split(":")[0]
            });

          node.append("text")
            .attr("class", "nodeValue")
            .text(function (d) {
              return d.name /* + "\n" + format(d.value)*/;
            });

          node.selectAll("text.nodeValue")
            .attr("x", 6)
            .attr("y", function (d) {
              return 32;
            })
            .attr("dy", ".35em")
            .attr("text-anchor", "start")
            .attr("transform", null)
            .text(function (d) {
              var sansStage = d.name.split(":");
              sansStage.shift();
              return sansStage.length > 0 ? sansStage.join(":") + ":" + formatNumber(d.count) : formatNumber(d.count);
            });

          // add the rectangles for the nodes
          node.append("rect")
            .filter(
              function(d,i) {
                var droppedOff = _.find(d.sourceLinks, function(item) {
                  //truthy
                  return ~item.target.name.indexOf('Abandon');
                })
                return !_.isEmpty(droppedOff);
              }
            )
            .attr("y", function(d) {
              return d.dy
            })
            .attr("x", function(d) {
              return d.dx-20
            })
            .attr("height", function (d) {
              return 20
            })
            .attr("class", "abandon")
            .attr("width", 20)
            .style("fill", function (d, i) {
              return 'red'
            })
            .append("title")
            .text(function (d) {
              return "Drop-Off";
            });

          node.append("text")
            .filter(
              function(d,i) {
                var droppedOff = _.find(d.sourceLinks, function(item) {
                  //truthy
                  return ~item.target.name.indexOf('Abandon');
                })
                return !_.isEmpty(droppedOff);
              }
            )
            .attr("class", "abandonValue");

          node.selectAll("text.abandonValue")
            .attr("y", function(d) {
              return d.dy + 15;
            })
            .attr("x", function(d) {
              return d.dx-20;
            })
            .attr("dx", ".36em")
            .attr("text-anchor", "start")
            .attr("transform", null)
            .style("fill", function (d, i) {
              return 'white'
            })
            .text(function (d) {
              return d.sourceLinks[0].target.count
            });



          var selected = {};
          var selectedData = {};
          var step = -1;

          function selectNodesToCompare(ctx, el) {
            var node = d3.select(ctx);
            var littleRect = node.select(".stage");

            if (node.classed('dimmed')) {
              return
            }

            var translation = d3.transform(node.attr("transform")).translate;

            var origWidth = parseInt(littleRect.attr("width"));
            var origHeight = parseInt(littleRect.attr("height"));


            var allNodesCount = svg.selectAll(".node")[0].length - 1;
            var lastStepNode = svg.selectAll(".node")[0][allNodesCount];
            var lastStep = d3.select(lastStepNode).attr('step');

            var allButSelected = null;


            if (node.attr("step") == lastStep || node.datum().sourceLinks.length == 0) {
              //don't select end nodes if the clicked one is in last step
              allButSelected = svg.selectAll(".node:not([step='" + node.attr("step") + "'])")
                .filter(function (d) {
                  return d.sourceLinks.length > 0
                })
            } else {
              allButSelected = svg.selectAll(".node:not([step='" + node.attr("step") + "'])");
            }

            allButSelected.classed("dimmed", true);

            //deselect selected
            if (node.attr("data-clicked") == "1") {
              svg.select('#selected' + node.attr("id")).remove();
              var prop = 'selected' + node.attr("id");
              delete selected[prop];
              delete selectedData[prop];
            } else {
              if (!node.classed('dimmed')) {
                var stageNode = svg.append("rect")
                  .attr("x", translation[0] - 5)
                  .attr("y", translation[1] - 5)
                  .attr("id", "selected" + node.attr("id"))
                  .attr("width", origWidth + 10)
                  .attr("height", origHeight + 30)
                  .style('stroke', 'red')
                  .style('stroke-width', '2')
                  .style('stroke-dasharray', '10 5')
                  .style('fill', 'none')
                selected[stageNode.attr('id')] = stageNode;
                selectedData[stageNode.attr('id')] = node.datum();
                step = node.attr("step");
              }

              if (_.keys(selected).length > 2) {
                var theKey = _.keys(selected)[0];
                var theId = selected[theKey].attr('id').replace('selected', '');
                //un-highlight the links
                var n = svg.select("#" + theId);
                highlight_node_links(n[0][0], n.datum());
                //remove highlight
                selected[theKey].remove();
                //remove the highlight rect
                delete selected[theKey]
                delete selectedData[theKey]
              }
            }


            if (_.keys(selected) == 0) {
              //allButSelected.classed("dimmed", false);
              svg.selectAll(".node").classed("dimmed", false);
            }


            var clicked = svg.selectAll("[data-clicked='1']");
            var analysisPanel = jQuery('#analysis');


            if (_.keys(selected).length == 2) {

              if (analysisPanel.is(':hidden')) {
                analysisPanel.show('fast');
              }

              var data = _.map(selectedData, function (d) {
                return {'stage': d.name, 'step': d.xPos}
              })
              $rootScope.$broadcast("OnNodesSelected", _.values(data))
            } else {

              if (analysisPanel.is(':visible')) {
                analysisPanel.hide('fast');
              }

            }

            highlight_node_links(ctx, el)
          }

          var currentObject = null;
          var drillDownMode = false;

          d3.selectAll(".link")
            .on("click", function (d) {
              var flow_params = {
                sourceName: d.source.name,
                targetName: d.target.name,
                step: d.source.xPos,
                filterValue: d.group_name,
              };
              $rootScope.$emit('journeys.details.flow.link', flow_params)
            })

          d3.selectAll(".node")
            .on("click", function (el) {
              if (drillDownMode) {
                var flow_params = {
                  stage: el.name,
                  step: el.xPos
                };
                $rootScope.$emit('journeys.details.flow.stage', flow_params)
              } else {
                d3.select(this).select(".stage").classed('highlight', false);
                selectNodesToCompare(this, el);
              }
            })

          d3.select('body').on('keydown', function (e) {
            if (d3.event.keyCode == 16) {
              drillDownMode = true;
              $rootScope.$broadcast("DRILL_DOWN_MODE", true)
            }
          })

          d3.select('body').on('keyup', function (e) {
            drillDownMode = false;
            $rootScope.$broadcast("DRILL_DOWN_MODE", false)
          })


          d3.selectAll(".link")
            .on("mouseover", function (d) {
              select_links_path(this, d)
            })
            .on("mouseout", function (d) {

              d3.selectAll('.link').classed('link-selected', false)
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.4);
            });

          d3.selectAll(".stage")
            .on("mouseover", function (d) {
              var parent = d3.select(this.parentNode);
              if (!parent.classed('dimmed')) {
                d3.select(this).classed('highlight', true);
                currentObject = this;
                highlight_node_links(this, d)
              }
            })
            .on("mouseout", function (d) {
              var parent = d3.select(this.parentNode);
              if (!parent.classed('dimmed')) {
                d3.select(this).classed('highlight', false);
                currentObject = null;
                highlight_node_links(this, d)
              }

            });

          function highlight_node_links(el, node) {

            var remainingNodes = [],
              nextNodes = [];

            var stroke_opacity = 0;
            if (d3.select(el).attr("data-clicked") == "1") {
              d3.select(el).attr("data-clicked", "0");
              stroke_opacity = 0;

            } else {
              d3.select(el).attr("data-clicked", "1");
              stroke_opacity = 1;
            }

            var traverse = [{
              linkType: "sourceLinks",
              nodeType: "target"
            }, {
              linkType: "targetLinks",
              nodeType: "source"
            }];


            var groupings = _.chain(node.sourceLinks.concat(node.targetLinks))
              .flatten()
              .pluck('group_name')
              .value();

            traverse.forEach(function (step) {
              node[step.linkType].forEach(function (link) {
                if (_.indexOf(groupings, link.group_name) > -1) {
                  remainingNodes.push(link[step.nodeType]);
                  highlight_link(link.id, stroke_opacity);
                }

              });

              while (remainingNodes.length) {
                nextNodes = [];
                remainingNodes.forEach(function (node) {
                  node[step.linkType].forEach(function (link) {
                    if (_.indexOf(groupings, link.group_name) > -1) {
                      nextNodes.push(link[step.nodeType]);
                      highlight_link(link.id, stroke_opacity);
                    }
                  });
                });
                remainingNodes = nextNodes;
              }

            });
            var selected = d3.select(el).classed('highlight');
            if (selected) {
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.1);
            } else {
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.4);
            }
          }

          function highlight_link(id, opacity) {
            //d3.select("#link-"+id).style("stroke-opacity", opacity);
            if (opacity > 0) {
              d3.select("#link-" + id).classed("link-selected", true);
            } else {
              d3.select("#link-" + id).classed("link-selected", false);
            }
          }

          function select_links_path(el, path) {
            var remainingNodes = [],
              nextNodes = [];

            var traverse = [{
              linkType: "sourceLinks",
              nodeType: "target"
            }, {
              linkType: "targetLinks",
              nodeType: "source"
            }];

            var grouping = path.group_name;

            remainingNodes.push(path);
            highlight_link(path.id, 1);

            traverse.forEach(function (step) {
              path[step.nodeType][step.linkType].forEach(function (link) {
                if (link.group_name == grouping) {
                  remainingNodes.push(link);
                  highlight_link(link.id, 1);
                }
              });

              while (remainingNodes.length) {
                nextNodes = [];
                remainingNodes.forEach(function (node) {
                  node[step.nodeType][step.linkType].forEach(function (link) {
                    if (link.group_name == grouping) {
                      nextNodes.push(link);
                      highlight_link(link.id, 1);
                    }
                  });
                });
                remainingNodes = nextNodes;
              }
            });

            var selected = d3.select(el).classed('link-selected');
            if (selected) {
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.1);
            }
          }

          function makeId(prefix) {
            prefix || (prefix = '');
            //return prefix + (Math.random() * 1e16).toFixed(0);
            var id = (function () {
              var a = 0;
              return function () {
                return prefix + a++
              }
            })();
            return id;
          }
        }
      }
    }
  }
  chart.$inject = ["$rootScope", "$window", "ChartFactory", "Utils", "PlotTypes", "FilterService"];
})();

(function () {
  'use strict';
  
  angular
    .module('slr.date-range-dropdown', [
      
    ]);
})();
(function () {
  'use strict';

  angular
    .module('slr.date-range-dropdown')
    .directive('dateRangeDropdown', dateRangeDropdown);

  /** @ngInject */
  function dateRangeDropdown($rootScope, FilterService, WidgetService, AccountsService) {
    return {
      restrict: 'E',
      templateUrl: "/static/assets/js/app/_components/date-range-dropdown/components.date-range-dropdown.directive.html",
      scope: {
        currentDate: '=?',
        isAllOptionsShown: '=',
        onChange: '&'
      },
      link: function (scope, element, attrs) {
        var widget = WidgetService.getCurrent();
        //scope.dateRangeButtons = FilterService.getDateRangeButtons('Past 3 Months');
        scope.btnType = null;
        scope.currentAlias = amplify.store('current_date_alias') || FilterService.getSelectedDateRangeAlias();
        scope.currentDate = amplify.store('current_date_range') || FilterService.getSelectedDateRangeName();
        //scope.isAllOptionsShown  = false;
        scope.cDate = scope.currentDate || FilterService.getSelectedDateRangeName();
        scope.setDateRange = function (range) {
          FilterService.setDateRange(range);
          scope.cDate = FilterService.getSelectedDateRangeName();
          if (scope.currentDate) {
            scope.currentDate = FilterService.getSelectedDateRangeName();
          }
        };
        attrs.$observe('type', function (v) {
          if (v && v == 'compact') {
            scope.btnType = 'btn-sm'
          }
        });
        var acc = null;
        scope.$watch('isAllOptionsShown', function (nVal) {
          if (nVal === true) {
            if (acc && acc.name !== 'BlueSkyAirTrans') {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Demo Date Range']);

            }
            else if (acc && acc.name !== 'epicAcc') {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Epic Date Range']);
            }
            else {
              scope.dateRangeButtons = FilterService.getDateRangeButtons();
            }
          } else {
            if (acc && acc.name !== 'BlueSkyAirTrans') {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Demo Date Range', 'Past 3 Months']);
            } else {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Past 3 Months']);
            }
          }
          scope.currentDate = amplify.store('current_date_range') || scope.currentDate;
        });

        // only show Demo Date Range for accounts with name BlueSkyAirTrans
        $rootScope.$on(AccountsService.ACCOUNTS_EVENT, function () {
          acc = AccountsService.getCurrent();
          if (acc.name == 'BlueSkyAirTrans') {
            scope.dateRangeButtons = scope.isAllOptionsShown ? FilterService.getDateRangeButtons() :
              FilterService.getDateRangeButtons(['Past 3 Months']);
          } else {
            scope.dateRangeButtons = scope.isAllOptionsShown ? FilterService.getDateRangeButtons(['Demo Date Range']) :
              FilterService.getDateRangeButtons(['Demo Date Range', 'Past 3 Months']);
          }
        });

        scope.$watch('currentDate', function (newVal, oldVal) {
          if (newVal !== oldVal) {
            scope.cDate = scope.currentDate;
          }
        }, true);

        scope.$watch('cDate', function (newVal, oldVal) {
          //console.log("Try to persist daterange");
          if (newVal !== oldVal || widget) {
            if (FilterService.getSelectedDateRangeAlias() != 'past_3_months') {
              //persist chosen daterange
              // don't store if current url is /dashboard
              if (location.pathname !== "/dashboard") {
                amplify.store('current_date_range',
                  FilterService.getSelectedDateRangeName(),
                  {expires: 86400000});
                amplify.store('current_date_alias',
                  FilterService.getSelectedDateRangeAlias(),
                  {expires: 86400000});
              }
              scope.onChange({dates: FilterService.getDateRange()});
            }
          }
        }, true);

        if (scope.currentAlias && !widget) {
          //console.log("Set DateRange Alias as: " + scope.currentAlias);
          FilterService.setDateRangeByAlias(scope.currentAlias);
        } else if (widget) {
          //console.log("Setting date from widget!");
          FilterService.setDateRange(widget.extra_settings.range_type);
          scope.cDate = FilterService.getSelectedDateRangeName();
        }
      }
    }
  }
  dateRangeDropdown.$inject = ["$rootScope", "FilterService", "WidgetService", "AccountsService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.horizontal-timeline', [
      'ark-components',
      'angular-timeline'
    ])
})();
(function () {
  'use strict';

  angular
    .module('slr.horizontal-timeline')
    .directive('horizontalTimeline', horizontalTimeline);

  /** @ngInject */
  function horizontalTimeline($timeout) {
    return {
      template: '<div id="timelineModal"></div>',
      restrict: 'E',
      scope: {
        source: '=',
        width: '@',
        height: '@',
        startZoomAdjust: '@',
        startAtEnd: '@',
        startAtSlide: '@',
        hashBookmark: '@',
        font: '@',
        lang: '@',
        thumbnailUrl: '@',
        state: '=',
        debug: '@',
        dayEvents: '=',
        showData: '&'
      },
      link: function postLink(scope, iElement, iAttrs) {

        var timeline;

        //////////////////////
        // Required config  //
        //////////////////////

        var width = (scope.width === undefined) ? '960' : scope.width;
        var height = (scope.height === undefined) ? '540' : scope.height;
        var timeline_conf = {
          source: scope.source
        };

        //////////////////////
        // Optional config  //
        //////////////////////

        // What are other types? not documented in TimelineJS
        // Not yet available for change to user
        if (scope.type) timeline_conf["type"] = scope.type;

        // is this used? First glance did not see effect of change
        // I don't think it is useful when passing id in object instantiation as below
        // Not yet available for change to user
        if (scope.embedId) timeline_conf["embed_id"] = scope.embedId;

        // First glance did not see the effect?
        // Not yet available for change to user
        if (scope.embed) timeline_conf["embed"] = scope.embed;

        if (scope.startAtEnd === 'true')
          timeline_conf["start_at_end"] = true;
        timeline_conf["start_at_end"] = false;

        if (scope.startZoomAdjust) timeline_conf["start_zoom_adjust"] = scope.startZoomAdjust;

        // Still need to observe how slide and startAtSlide with behave together
        // in practice. For now, put the burden on the programmer to use both correctly
        // startAtSlide should only be used to instantiate and slide
        // should only be used to reload.

        if (scope.startAtSlide) timeline_conf["start_at_slide"] = scope.startAtSlide;

        // working, but how to integrate with Angular routing?! Something to ponder
        (scope.hashBookmark === 'true') ? timeline_conf["hash_bookmark"] = true :
          timeline_conf["hash_bookmark"] = false;

        if (scope.font) timeline_conf["font"] = scope.font;
        if (scope.thumbnailUrl) timeline_conf["thumbnail_url"] = scope.thumbnailUrl;

        (scope.debug === 'true') ? VMM.debug = true : VMM.debug = false;

        /////////////////////////////
        // Custom Timeline Config  //
        /////////////////////////////

        scope.$watch('state.modal_open', function (newVal, oldVal) {
          // When timeline is loaded check if a CRUD modal is open for editing
          if (timeline && newVal !== oldVal) {
            timeline.set_config_item("modal_open", newVal);
          }
        });

        /////////////////////////
        // Rendering Timeline  //
        /////////////////////////

        var render = function (s) {
          // Source arrived but not yet init'ed VMM.Timelines
          if (s && !timeline) {
            timeline_conf["source"] = s;
            timeline = new VMM.Timeline('timelineModal', width, height);
            timeline.init(timeline_conf);
          } else if (s && timeline) {
            if (typeof scope.state !== 'undefined' && scope.state.index) {
              timeline.reload(s, scope.state.index);
            } else {
              timeline.reload(s);
            }
          }
        };

        // Async cases (when source data coming from services or other async call)
        scope.$watch('source', function (newSource, oldSource) {
          // Source not ready (maybe waiting on service or other async call)
          if (newSource !== oldSource) {

          }
        });

        // Non-async cases (when source data is already on scope)
        render(scope.source);

        // When changing the current slide *from the controller* without changing the
        // source data.
        scope.$watch('state.index', function (newState, oldState) {
          if (!newState == 'undefined') {
            return;
          }
          if (timeline && newState !== oldState) {
            timeline.get_config().current_slide = newState;
          }
        });

        /////////////////////////
        // Events of Interest  //
        /////////////////////////

        var updateState = function (e, callback) {
          // For some reason I have not investigated when using
          // 'keydown' events the current_slide is not yet
          // updated in the TimelineJS config. This is why
          // I delay the scope.state.index binding through
          // a simple $timeout callback with 0 delay.
          // Funny enough this does not manifest itself
          // with 'click' events.
          return $timeout(function () {
            if (typeof scope.state !== 'undefined') {
              scope.state.index = timeline.get_config().current_slide;
            }
          });
        };

        // set up index to the element
        var flags = angular.element('.marker .flag').toArray();
        _.each(scope.dayEvents, function (day, index) {
          angular.element(flags[index]).attr('data-day-index', index);
        });

        angular.element('.nav-next').on("click", function (e) {
          updateState(e);
          var index = angular.element('.marker.active').find('.flag').attr('data-day-index');
          scope.showData({index: index});
        });

        angular.element('.nav-previous').on("click", function (e) {
          updateState(e);
          var index = angular.element('.marker.active').find('.flag').attr('data-day-index');
          scope.showData({index: index});
        });

        iElement.on("click", ".marker", function (e) {
          var index = angular.element(this).find('.flag').attr('data-day-index');
          scope.showData({index: index});
          updateState(e);
        });

        var bodyElement = angular.element(document.body);
        bodyElement.on("keydown", function (e) {
          // On what keys to update current slide state
          // Might be missing some, touch keys?!?
          // Using object mapping for clarity
          var keys = {
            33: "PgUp",
            34: "PgDn",
            37: "Left",
            39: "Right",
            36: "Home",
            35: "End"
          };
          var keysProps = Object.getOwnPropertyNames(keys);
          if (keysProps.indexOf(e.keyCode + '') != -1) {
            updateState(e);
          }
        });

      }
    };
  }
  horizontalTimeline.$inject = ["$timeout"];
})();
(function () {
  'use strict';

  angular
    .module('slr.smart-tags-modal', [
      'ark-ui-bootstrap',
      'ui.select'
    ])
})();
(function () {
  'use strict';

  angular
    .module('slr.smart-tags-modal')
    .directive('slrSmartTagsModal', slrSmartTagsModal);

  /** @ngInject */
  function slrSmartTagsModal($modal, $http, SmartTag, SmartTags, SmartTagForm, GroupUserService) {
    return {
      restrict: 'E',
      template: "<button ng-show= 'smartTag'"
      + "ng-click='openDialog()' "
      + "class='btn btn-md btn-link' "
      + "data-original-title='Click to see tag settings' "
      + "data-placement='bottom'"
      + "ui-jq='tooltip'>Edit</button>",
      scope: {
        smartTag: '='
      },
      link: function (scope, elm, attrs, ctrl) {
        scope.openDialog = function () {
          $modal.open({
            backdrop: true,
            keyboard: true,
            backdropClick: true,
            templateUrl: '/partials/tags/tagModal',
            resolve: {
              tag: function () {
                return angular.copy(scope.smartTag)
              }
            },
            controller: ["$scope", "tag", function ($scope, tag) {
              $scope.tagItem = tag;
              $scope.tagItemDefaults = SmartTagForm.getSmartTagDefaults();
              $scope.usersEmails = [];
              $scope.alertCandidateEmails = [];
              $scope.changingSTIntentionLabels = [];
              $scope.chosenSTIntenions = [];
              $scope.selected_users_emails = {
                users: $scope.tagItem.alert.emails
              };
              $scope.allUsersLoaded = false;
              $scope.groupCounter = 0;


              $http.get('/alert_user_candidates', {}).success(function (data) {
                $scope.alertCandidateEmails = data.list;
              });

              //Get all the available users for
              var goodGroups = _.filter($scope.tagItem.groups, function (group) {
                return group.indexOf(":") == -1
              });
              var tempUsers = [];
              for (var i = 0; i < goodGroups.length; i++) {
                var group_id = goodGroups[i];
                //Query the users for each group in the group list
                GroupUserService.fetchUsers({id: group_id}, function (res) {
                  $scope.groupCounter++;
                  if ($scope.groupCounter == goodGroups.length) {
                    $scope.allUsersLoaded = true;
                  }
                  _.each(res.users, function (user) {
                    tempUsers.push(user);
                  })
                });
              }

              $scope.$watch('allUsersLoaded', function (nVal, oVal) {
                if (nVal == true) {
                  $scope.usersEmails = _.map(_.groupBy(tempUsers, function (doc) {
                    return doc.id;
                  }), function (grouped) {
                    return grouped[0];
                  });
                }
              });

              $scope.smart_tag_restored = true;
              $scope.selectOptions = {
                intentions: SmartTagForm.getIntentions(),
                postCreationStatuses: SmartTagForm.getPostStatuses()
              };
              SmartTagForm.getChannels().then(function (data) {
                $scope.selectOptions.channels = data;
              });
              SmartTagForm.getContactLabels().then(function (data) {
                $scope.selectOptions.labels = data;
              });

              /** INTENTIONS */
              $scope.chosenSTIntenions = SmartTags.getIntentionsByLabel($scope.tagItem.intentions, $scope.selectOptions.intentions);
              $scope.changingSTIntentionLabels = _.pluck($scope.chosenSTIntenions, 'label');
              $scope.addSTIntenion = function (intention) {
                $scope.changingSTIntentionLabels.push(intention.label);
              };
              $scope.removeSTIntenion = function (intention) {
                $scope.changingSTIntentionLabels.splice($scope.changingSTIntentionLabels.indexOf(intention.label), 1);
              };
              /** END */

              $scope.formState = {
                isSaved: false,
                isError: false
              };
              $scope.mode = "edit";
              $scope.is_modal = true;


              $scope.isAdvancedState = false;
              //Advanced options
              $scope.evaluate = function () {
                return $scope.isAdvancedState;
              }
              $scope.evaluateIcon = function () {
                if ($scope.isAdvancedState) {
                  return "icon-expand-down";
                }
                else {
                  return "icon-expand-right";
                }
              };
              $scope.changeStatus = function () {
                $scope.isAdvancedState = !$scope.isAdvancedState;
              };
              $scope.save = function () {
                $scope.formState.isSaved = false;

                $scope.tagItem.intentions = _.uniq($scope.changingSTIntentionLabels);

                var selectedUsers = [];
                _.each($scope.selected_users_emails.users, function (email) {
                  selectedUsers.push(
                    _.find($scope.usersEmails, function (u) {
                      return u.email == email
                    })
                  )
                });
                //$scope.tagItem.alert.users  = _.pluck(selectedUsers, 'id');
                //$scope.tagItem.alert.emails = $scope.selected_users_emails.users;
                SmartTag.update($scope.tagItem, function (res) {
                  $scope.$parent.$broadcast(SmartTag.ON_SMARTTAG_UPDATE);
                  $scope.formState.isSaved = true;
                });
              };
              $scope.usersRequired = function () {
                if (typeof $scope.tagItem != 'undefined' && typeof $scope.tagItem.alert.is_active != 'undefined' && $scope.selected_users_emails.users != 'undefined') {
                  if ($scope.tagItem.alert.is_active == true && $scope.selected_users_emails.users.length > 0)
                    return false;
                  else
                    return true;
                }
                else
                  return false;
              };
              $scope.formValid = function () {
                if (typeof $scope.tagItem != 'undefined' && typeof $scope.tagItem.title != 'undefined' && typeof $scope.tagItem.description != 'undefined') {
                  if ($scope.tagItem.title.length > 0 && $scope.tagItem.description.length > 0) {
                    if ($scope.tagItem.alert.is_active) {
                      if ($scope.selected_users_emails.users.length > 0)
                        return false;
                      else
                        return true;
                    }
                    else
                      return false;
                  }
                  else
                    return true;
                }
                else
                  return true;
              };
              $scope.close = function (result) {
                $scope.$close(result);
              };

            }]
          });
        }
      }
    };
  }
  slrSmartTagsModal.$inject = ["$modal", "$http", "SmartTag", "SmartTags", "SmartTagForm", "GroupUserService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.widget-dialog', [
      'ark-dashboard'
    ]);
})();
(function () {
  'use strict';

  angular
    .module('slr.widget-dialog')
    .directive('widgetDialog', widgetDialog);

  /** @ngInject */
  function widgetDialog($modal, $timeout, SystemAlert, WidgetService, DashboardService) {
    return {
      scope: {
        sourceWidget: '=widget',
        settings: '&'
      },
      link: function (scope, elm, attrs) {
        elm.on('click', function () {
          scope.openDialog();
        });

        var dashboards = {
          'types': [],
          'list': {}
        }
        DashboardService.loadSimple()
          .then(function (data) {
            dashboards = data;
          });

        scope.openDialog = function () {
          var source_widget = scope.sourceWidget,
            settings = scope.settings();

          $modal.open({
            backdrop: true,
            keyboard: true,
            backdropClick: true,
            templateUrl: '/static/assets/js/app/_components/widget-dialog/components.widget-dialog.directive.html',
            resolve: {
              'dashboards': function () {
                return dashboards;
              }
            },

            controller: ["$scope", "dashboards", function ($scope, dashboards) {
              $scope.dashboards = dashboards;
              $scope.dashboardTypeId = _.result(_.find($scope.dashboards.types, {'display_name': 'Blank dashboard type'}), 'id');
              $scope.dashboardList = $scope.dashboards.list[$scope.dashboardTypeId];

              $scope.dashboardTypeSelect = function () {
                $scope.dashboardList = $scope.dashboards.list[$scope.dashboardTypeId];
              };

              $scope.widget = {
                id: source_widget ? source_widget.id : null,
                title: source_widget ? source_widget.title : '',
                description: source_widget ? source_widget.description : '',
                style: source_widget ? source_widget.style : {width: '33%'},
                settings: settings.settings,
                extra_settings: settings.extra_settings,
                dashboard_id: null
              };
              $scope.save = function () {
                if ($scope.widget.title.length > 0) {
                  var isNew = !source_widget,
                    save = isNew ? WidgetService.create : WidgetService.update;
                  save.bind(WidgetService)($scope.widget).then(function (res) {
                    if (isNew) {
                      SystemAlert.success("Widget '" + res.data.item.title + "' has been added to dashboard", 5000);
                    }
                    $scope.$close();
                  });
                }
              };
              $scope.close = $scope.$close;

              $scope.init = function () {
                $timeout(function () {
                  angular.element('#widgetTitle').focus();
                });
              };
              $scope.init();
            }]
          });
        }
      }
    }
  }
  widgetDialog.$inject = ["$modal", "$timeout", "SystemAlert", "WidgetService", "DashboardService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.facet-panel', [])
})();
(function () {
  'use strict';

  angular
    .module('slr.facet-panel')
    .directive('facetPanel', facetPanel);

  /** @ngInject */
  function facetPanel($timeout) {
    return {
      scope: {
        facetTitle: '@',
        facetTooltip: '@',
        facetOptions: '=',
        isAllChecked: '=facetIsAll',
        facetIsMulti: '=',
        facetSelected: '=',
        facetUpdateAction: '=',
        isOpen: '@',
        facetIsHidden: '='
      },
      restrict: 'E',
      templateUrl: '/static/assets/js/app/_components/facet-panel/components.facet-panel.html',
      link: function (scope, element, attrs, ngModel) {
        scope.facet = {
          selected: scope.facetSelected
        }
        scope.$watch('facet.selected', function (nVal, oVal) {
          if (nVal === oVal) return;
          scope.isAllChecked = !nVal;
          $timeout(function () {
            scope.facetSelected = nVal;
            scope.$apply();
            scope.facetUpdateAction();
          }, 0)
        }, true);

        scope.$watch('facetSelected', function (nVal, oVal) {
          if (nVal) {
            scope.facet.selected = nVal;
          }
        })

        scope.$watch('facetIsHidden', function (nVal, oVal) {
          if (nVal) {
            scope.isAllChecked = true;
          }
        })

        scope.$watch('facetOptions', function () {
          scope.updateFacet();
        }, true);

        scope.updateFacet = function () {
          if (scope.facetIsMulti) {
            var selected = _.filter(scope.facetOptions, function (item) {
              return item.enabled == true
            });
            selected.length > 0 ? scope.isAllChecked = false : scope.isAllChecked = true;
            scope.facetUpdateAction();

            if (scope.facetOptions && scope.facetOptions.length === selected.length && scope.facetOptions.length > 1) {
             scope.isAllChecked = true;
            }
          }

        };
        scope.$watch('isAllChecked', function (newVal) {
          if (newVal) {
            _.each(scope.facetOptions, function (item) {
              item.enabled = false;
            });

            if (!scope.facetIsMulti) {
              scope.facet.selected = null;
            } else {
              scope.facetUpdateAction();
            }

          } else {
            $timeout(function() {
              scope.isOpen = true
            }, 0);
          }
        })
      }
    };
  }
  facetPanel.$inject = ["$timeout"];
})();

(function () {
  'use strict';
  
  angular
    .module('slr.ng-confirm', []);
})();
(function () {
  'use strict';

  angular
    .module('slr.ng-confirm')
    .directive('ngConfirm', ngConfirm);

  /** @ngInject */
  function ngConfirm(PopupService) {
    return {
      restrict: 'EA',
      link: function postLink(scope, element, attrs) {
        // Could have custom or boostrap modal options here
        var popupOptions = {closeAfterAction: true};
        element.bind("click", function () {
          var showFn = function () {
              return scope.$eval(attrs["showIf"])
            },
            actionFn = function () {
              return scope.$eval(attrs["actionFunction"])
            },
            show = showFn();
          if (show === true || show === undefined) {
            PopupService.confirm(attrs["title"], attrs["actionText"],
              attrs["actionButtonText"], attrs["actionFunction"],
              attrs["cancelButtonText"], attrs["cancelFunction"],
              scope, popupOptions);
          } else {
            angular.isFunction(actionFn) && actionFn();
          }
        });
      }
    };
  }
  ngConfirm.$inject = ["PopupService"];
})();