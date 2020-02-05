'use strict';

var ChannelTypes = function () {

    var addChannelTypeBtn = element(by.css('a[href="#/channel_types/edit/new"]'));
    var channelTypeNameField = element(by.css("#entity_name"));

    this.navigateToChannelTypes = function () {
        element(by.css('.nav-side-tabs')).element(by.linkText('Channel Types')).click();
    };

    this.verifyChannelTypesPageOpen = function () {
        expect(element(by.tagName('h1')).getText()).toEqual('Channel Types');
    };

    this.clickAddChannelTypeBtn = function () {
         addChannelTypeBtn.click();
    };

    this.verifyNewChannelTypePageOpen = function () {
         expect(element(by.tagName('h3')).getText()).toEqual('New Channel Type');
    };

    this.addChannelTypeName = function (name) {
         channelTypeNameField.sendKeys(name);
    };

    this.clickCreateBtn = function () {
        element(by.buttonText('Create')).click();
    };

    this.waitChannelTypeCreatedSuccessfully = function (name) {
        var e = element(by.xpath("//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]".replace('%s', name)));
        browser.wait(EC.presenceOf(e), 100000);
        expect(e.isPresent()).toBeTruthy();
    };

};

module.exports = ChannelTypes;
