var _ = require('lodash');
var async = require('async');
var unirest = require('unirest');
var config = require('./config');

var getCustomerById = function(customerId, callback){
    var self = this;

    async.waterfall([
        function(cb) {
            var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/authenticate').replace("{{HOST_DOMAIN}}", config.HOST_DOMAIN);
            unirest.post(apiUrl)
                .query({
                    username: 'super_user@solariat.com',
                    password: 'password'
                })
                .end(function(response) {
                    if (response.statusCode && response.statusCode === 200) {
                        cb(null, response.body.token);
                    } else{
                        cb('Error while authentication!');
                    }
                });
        },
        function(userToken, cb) {
            var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/customers?id=' + customerId).replace("{{HOST_DOMAIN}}", config.HOST_DOMAIN);
            unirest.get(apiUrl)
                .query({
                    token: userToken
                })
                .end(function(response) {
                    if (response.statusCode && response.statusCode === 200 && response.body.item !== undefined) {
                        var customer = response.body.item;
                        customer.name = customer.first_name + ' ' + customer.last_name;
                        cb(null, customer);
                    } else {
                        cb('Error while fetching customer detail!');
                    }
                });
        }
    ], function(err, result) {
        if(err) {
            console.log('/api/v2.0/customers?id=' + customerId + ' ........... ERROR!!!');
            console.log(err);
            callback(err);
        } else {
            console.log('/api/v2.0/customers?id=' + customerId + ' ........... SUCESS!!!');
            callback(null, result);
        }
    });
};

module.exports.getCustomerById = getCustomerById;