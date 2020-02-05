'use strict';

var Channels = function () {

    var addChannelBtn = element(by.css('a[href="#/channel_types/edit/new"]'));
    var channelNameField = element(by.id("input01"));
    var importDataBtn = element(by.partialButtonText("Import data"));
    var sourceFile = element(by.partialButtonText("Select File"));
    var separator = element(by.id('separator'));
    var uploadBtnModal = element(by.xpath("//div[@class='modal-dialog']//button[contains(., 'Upload')]"));
    var sourceFile = element(by.xpath("//input[@tooltip='Import']"));
    var updateChannelBtn = element(by.partialButtonText("Update"));

    this.navigateToChannelsPage = function () {
        element(by.css('.nav-side-tabs')).element(by.linkText('Channels')).click();
    };

    this.verifyNewChannelFormOpen = function () {
      //when there are no channels - New Channel form opens:
        expect(element(by.xpath("//h3[contains(.,'New Channel')]")).getText()).toEqual('New Channel');
    };

    this.addChannelType = function () {
        var select = element(by.id('channel_type'));
        select.$("[value='0']").click();
    };

    this.addChannelName = function (label) {
        channelNameField.sendKeys(label);
    };

    this.clickCreateBtn = function () {
        element(by.partialButtonText('Create')).click();
        expect(importDataBtn.isPresent()).toBeTruthy();
    };

    this.invokeImportEventDataModal = function () {
        importDataBtn.click();
        expect(element(by.xpath("//h3[contains(.,'Import Event Data')]")).getText()).toEqual('Import Event Data');
    };

    this.selectSourceFile = function (filename) {
        var path = require('path');
        var fileToUpload = '../recources/' + filename,
            absolutePath = path.resolve(__dirname, fileToUpload);
        sourceFile.sendKeys(absolutePath);
    };

    this.setSeparator = function (separatorType) {
        separator.click();
        element(by.cssContainingText('option', separatorType)).click();
    };

    this.selectEventType = function () {
        var select = element(by.id("event_type"));
        select.$("[value='0']").click();
    };

    this.clickUploadButtonModal = function () {
      uploadBtnModal.click();
      expect(updateChannelBtn.isPresent()).toBeTruthy();
    };

    this.waitChannelCreatedSuccessfully = function (name) {
        var EC = protractor.ExpectedConditions;
        var e = element(by.xpath("//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]".replace('%s', name)));
        browser.wait(EC.presenceOf(e), 100000);
        expect(e.isPresent()).toBeTruthy();
    };

    this.clickUpdateChannelButton = function () {
      updateChannelBtn.click();
    };

    this.clickAllChannelsButton = function () {
      element(by.xpath("//button[@tooltip='All Channels']")).click()
    };

};

module.exports = Channels;
