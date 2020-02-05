'use strict';

var EventType = function () {

    var addEventTypeBtn = element(by.xpath("//a[@href='#/event_types/edit/new']"));
    var eventTypeNameFld = element(by.id('entity_name'));
    var channelTypeSelect = element(by.id('channel_type'));
    var createEventTypeBtn = element(by.xpath("//button[@ng-click='onCreateEntity()']"));
    var DATASET_ROW = "//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]//ancestor::tr[1]";
    var STATUS_CELL = DATASET_ROW + "//td[2]/span";
    var uploadFileBtn = element(by.xpath("//button[contains(.,'Upload File')]"));
    var discoverEventSchemaModalTitle = element(by.xpath("//h3[text()='Discover Schema']"));
    var schemaStatus = element(by.css(".topright-status"));
    var createSchemaBtn = element(by.xpath("//*[@ng-click='showUploadDialog(false)']"));
    var syncSchemaBtn = element(by.buttonText('Sync Schema'));
    var saveSchemaBtn = element(by.buttonText('Save Schema'));
    var separator = element(by.id('separator'));
    var sourceFile = element(by.xpath("//input[@tooltip='Import']"));
    var acceptSchemaBtn = element(by.buttonText('Accept Schema'));
    var labelTextInputFld = element(by.xpath("//input[@type='search']"));
    var typeDropown = element(by.model('field.type'));
    var expressionInputFld = element(by.id('expression_builder'));


    this.navigateToEventTypesPage = function () {
        element(by.css('.nav-side-tabs')).element(by.linkText('Event Types')).click();
    };

    this.verifyEventTypesPageOpen = function () {
        expect(element(by.tagName('h1')).getText()).toEqual('Event Types');
    };

    this.clickAddEventTypeBtn = function () {
         addEventTypeBtn.click();
    };

    this.verifyNewEventTypePageOpen = function () {
         expect(element(by.tagName('h3')).getText()).toEqual('New Event Type');
    };

    this.addEventTypeName = function (eventTypeName) {
         eventTypeNameFld.sendKeys(eventTypeName);
    };

    this.addChannelType = function (channelTypeName) {
         var select = channelTypeSelect.click();
         element(by.cssContainingText('option', channelTypeName)).click();
    };

    this.clickCreateEventTypeBtn = function () {
        createEventTypeBtn.click();
    };

    this.waitEventTypeCreatedSuccessfully = function (eventTypeName) {
        var e = element(by.xpath("//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]".replace('%s', eventTypeName)));
        browser.wait(EC.presenceOf(e), 100000);
        expect(e.isPresent()).toBeTruthy();
    };

    this.verifyEventTypeStatus = function (eventTypeName, eventStatus) {
        var statusActual = element(by.xpath(STATUS_CELL.replace('%s', eventTypeName))).getAttribute("tooltip");
        expect(statusActual).toContain(eventStatus);
    };

    this.openEventType = function (eventTypeName) {
        var e = element(by.xpath("//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]".replace('%s', eventTypeName)));
        e.click();
        expect(uploadFileBtn.isPresent()).toBeTruthy();
    };


};

module.exports = EventType;
