'use strict';

var CustomerProfile = function () {

    this.navigateToCustomerProfile = function () {
        element(by.css('.nav-side-tabs')).element(by.linkText('Customer Profile')).click();
    };

    this.verifyCustomerProfilePageOpen = function () {
        expect(element(by.tagName('h1')).getText()).toEqual('Customer Profile');
    };

};

module.exports = CustomerProfile;
