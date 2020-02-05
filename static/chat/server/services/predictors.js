'use strict';

var _ = require('lodash');
var Q = require('q');
var request = require('superagent');

function PredictorService(options) {

    this.options = options || {};
    this.list = [];
    this.agentRouter = null;

    var apiVersion = this.options.apiVersion || 'v2.0';
    var URL = 'http://{{HOST_DOMAIN}}/api/{{API_VERSION}}/predictors';
    URL = URL.replace('{{HOST_DOMAIN}}', this.options.HOST_DOMAIN).replace('{{API_VERSION}}', apiVersion);

    this.URL = URL;
}

function fetchAll() {

    var deferred = Q.defer();
    var _this = this;

    request
        .get(_this.URL)
        .query({
            token: _this.token
        })
        .end(function(err, res) {
            if (res && res.ok) {
                console.log('---------- Success! (Fetch all predictors) ----------');
                _this.list = res.body.list;
                _this.agentRouter = _.find(_this.list, {type: 'Agent Matching'})
                    || _.find(_this.list, {name: 'Agent Matching Predictor'});
                deferred.resolve(_this.list);
            } else {
                console.log('---------- Error! (Fetch all predictors) ----------');
                deferred.reject(err);
            }
        });

    return deferred.promise;
}

function score(params) {

    var deferred = Q.defer();
    var _this = this;

    if (!_this.agentRouter) {
        throw 'No Agent Router';
    }

    console.log(_this.URL + '/' + _this.agentRouter.id + '/score');

    request
        .post(_this.URL + '/' + _this.agentRouter.id + '/score')
        .send(params)
        .end(function(err, res) {
            if (res && res.ok) {
                console.log('---------- Success! (Predictor Scoring) ----------');
                deferred.resolve(res.body);
            } else {
                console.log('---------- Error! (Predictor Scoring) ----------');
                deferred.reject(err);
            }
        });

    return deferred.promise;
}

function getAgentRouterId() {
    if (this.agentRouter) {
        return this.agentRouter.id;
    }
    return null;
}

function setAuthToken(token) {
    this.token = token;
}

PredictorService.prototype.fetchAll = fetchAll;
PredictorService.prototype.score = score;
PredictorService.prototype.setAuthToken = setAuthToken;
PredictorService.prototype.getAgentRouterId = getAgentRouterId;

module.exports = PredictorService;
