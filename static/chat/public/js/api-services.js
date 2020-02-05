'use strict';
angular.module('journey.services', [])

angular.module('journey.services')
  .service('AuthService', ['$http', '$q', function($http, $q) {

  this.authenticate = function(authData) {
    console.log('[Authentication Service] - Retrieving access token...');

    var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/authenticate').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);

    return $http.post(apiUrl, authData);

  };
}])

  .service('AgentService', ['$http', '$q', function($http, $q) {

    this.getAll = function(userToken) {
      console.log('[Agent Service] - Retrieving list of agents...');

      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/agents').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);

      return $http.get(apiUrl, { params:{token: userToken} })
    };

    this.getById = function(userToken, agentId) {
      console.log('[Agent Service] - Retrieving of agent info...');

      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/agents').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);

      return $http.get(apiUrl, { params:{token: userToken, id: agentId} })
    }
  }])

  .service('CustomerService', ['$http', '$q', function($http, $q) {

    this.getAll = function(userToken) {
      console.log('[Customer Service] - Retrieving list of customers...');

      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/customers').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);

      return $http.get(apiUrl, { params:{token: userToken} })
    };

    this.getById = function(userToken, customerId) {
      console.log('[Customer Service] - Retrieving of customer info...');

      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/customers').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);

      return $http.get(apiUrl, { params:{token: userToken, id: customerId} })
    }
  }])

  .service('PredictorService', ['$http', function($http) {
    this.getAll = function(userToken) {
      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/predictors').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);

      return $http.get(apiUrl, { params:{token: userToken} })
    };

    this.score = function(predictor, params) {
      var apiUrl = 'http://' + HOST_DOMAIN + '/api/v2.0/predictors/' + predictor.id + '/score';

      return $http.post(apiUrl, params);
    };
  }])


  .service('SessionsService', ['$http', function($http) {
    this.getByCustomer = function(userToken, customerId, channelId) {
      console.log('[Current Sessions] - Retrieving sessions info...');
      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/chat/sessions').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
      return $http.get(apiUrl, {
        params: {
          token: userToken,
          customer_profile_id: customerId,
          service_channel_id: channelId
        }
      })
    }
  }])

  .service('ChannelsService', ['$http', function($http) {
    var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/channels').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
    this.getAll = function(userToken) {
      console.log('[All Channels] - Retrieving channels info...');
      return $http.get(apiUrl, {params: {token: userToken}})
    };
    this.getByPlatform = function(userToken, platform) {
      console.log('[Platform Channels] - Retrieving channels for platform ', platform);
      var apiPlatformUrl = apiUrl + "/" + platform;
      return $http.get(apiPlatformUrl, {params: {token: userToken}})
    }
  }])

  .service('ChatSummaryService', ['$http', function($http) {
    this.getById = function(userToken, conversationId) {
      console.log('[Chat Summary] - Retrieving conversations info...');

      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/chat/summary').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);

      return $http.get(apiUrl, {
        params: {
          token: userToken,
          conversation_id: conversationId
        }
      })
    }
  }])


  .service('EventsService', ['$http', function($http) {
    this.postEvent = function(postData) {
      console.log('[Posting chat event]...');

      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/events').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
      return $http.post(apiUrl, postData)
    }
  }]);