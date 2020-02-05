'use strict';

var _ = require('lodash');
var Q = require('q');
var request = require('superagent');

function UserService(options) {

    var superUser = {
        username: 'super_user@solariat.com',
        password: 'password'
    };

    this.options    = options || {};
    this.user       = options.superUser || superUser;
    this.agents     = [];

    var apiVersion = this.options.apiVersion || 'v2.0';
    var URL = 'http://{{HOST_DOMAIN}}/api/{{API_VERSION}}';
    URL = URL.replace('{{HOST_DOMAIN}}', this.options.HOST_DOMAIN).replace('{{API_VERSION}}', apiVersion);

    this.URL = URL;
}

function authenticate() {

    var deferred = Q.defer();
    var _this = this;

    request
        .post(_this.URL + '/authenticate')
        .send({
            username: _this.user.username,
            password: _this.user.password
        })
        .end(function(err, res) {
            if (res && res.ok) {
                console.log('---------- Success! (Super user authentication) ----------');
                _this.token = res.body.token;
                deferred.resolve(_this.token);
            } else {
                console.log('---------- Error! (Super user authentication) ----------');
                deferred.reject(err);
            }
        });

    return deferred.promise;
}

function fetchAllAgents() {

    var deferred = Q.defer();
    var _this = this;

    request
        .get(_this.URL + '/agents')
        .query({
            token: _this.token
        })
        .end(function(err, res) {
            if (res && res.ok) {
                console.log('---------- Success! (Fetch all agents) ----------');
                _this.agents = res.body.list;
                deferred.resolve(_this.agents);
            } else {
                console.log('---------- Error! (Fetch all agents) ----------');
                deferred.resolve([]);
            }
        });

    return deferred.promise;
}

function fetchCustomerById(customerId) {

    var deferred = Q.defer();
    var _this = this;

    request
        .get(_this.URL + '/customers?id=' + customerId)
        .query({
            token: _this.token
        })
        .end(function(err, res) {
            if (res && res.ok) {
                console.log('---------- Success! (Fetch one customer) ----------');
                deferred.resolve(res.body.item);
            } else {
                console.log('---------- Error! (Fetch one customer) ----------');
                deferred.reject(err);
            }
        });

    return deferred.promise;
}

function getAuthToken() {
    return this.token;
}

function getAllAgents() {
    return this.agents;
}

UserService.prototype.authenticate = authenticate;
UserService.prototype.fetchAllAgents = fetchAllAgents;
UserService.prototype.fetchCustomerById = fetchCustomerById;
UserService.prototype.getAuthToken = getAuthToken;
UserService.prototype.getAllAgents = getAllAgents;

module.exports = UserService;
