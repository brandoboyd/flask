'use strict';

var Datasets = function () {

    var createBtn = element(by.xpath("//*[@ng-click='openDatasetModal()']"));
    var datasetField = element(by.model('datasetName'));
    var datasetSeparator = element(by.id('separator'));
    var sourceFile = element(by.xpath("//input[@tooltip='Import']"))
    var acceptSchema = element(by.xpath("//*[@ng-click='acceptSchema()']"));
    var cancelSchema = element(by.xpath("//*[@ng-click='cancelSchema()']"));
    var DATASET_ROW = "//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]//ancestor::tr[1]";
    var STATUS_CELL = DATASET_ROW + "//td[2]/span";
    var FIELD_ELEMENT = "//a[contains(@ng-click,'field.name') and (normalize-space(text())='%s')]";
    var SELECT_FIELD = FIELD_ELEMENT + "//ancestor::tr[1]//select";
    var CHECKBOX_FIELD = FIELD_ELEMENT + "//ancestor::tr[1]//label[@class='checkbox']";
    var FIELD_TYPE = FIELD_ELEMENT + "//ancestor::tr[1]//td[3]//span";

    this.navigateToDatasetsList = function () {
        element(by.css('.nav-side-tabs')).element(by.linkText('Datasets')).click();
    };

    this.verifyDatasetPageOpen = function () {
        expect(element(by.tagName('h1')).getText()).toEqual('Datasets');
    };

    this.clickAddNewDatasetBtn = function () {
        createBtn.click();
    };

    this.setDataset = function () {
        var simpleDatasetName = 'AutoDataset' + Math.floor(Math.random() * 99999);
        datasetField.sendKeys(simpleDatasetName);
        return simpleDatasetName;
    };

    this.setSeparator = function (separatorType) {
        datasetSeparator.element(by.cssContainingText('option', separatorType)).click();
    };

    this.openDataset = function (datasetName) {
        element(by.partialLinkText(datasetName)).click();
    };

    this.applySchema = function () {
        var checkbox = element(by.xpath(CHECKBOX_FIELD.replace('%s', 'INTERACTION_DATE')));
        browser.wait(EC.elementToBeClickable(checkbox), 3000);
        checkbox.click();
        element(by.partialButtonText("Set As Created Time")).click();
        element(by.partialButtonText("Save Changes")).click();
        element(by.partialButtonText("Sync Schema")).click();
        browser.wait(EC.presenceOf(acceptSchema), 60000);
        expect(acceptSchema.isPresent()).toBeTruthy();
        acceptSchema.click();
        expect(element(by.xpath("//div[contains(@class,'topright-status') and contains(.,'Schema synchronized')]"))
            .isPresent).toBeTruthy();
    };

    this.navigateBack = function () {
        element(by.xpath("//button[@tooltip='All Datasets']")).click()
        return new Datasets()
    };


    this.setSourceFile = function (filename) {
        var path = require('path');
        var fileToUpload = '../recources/' + filename,
            absolutePath = path.resolve(__dirname, fileToUpload);
        sourceFile.sendKeys(absolutePath);
    };

    this.clickCreateBtn = function () {
        element(by.buttonText('Create')).click();
    };

    this.waitDatasetCreatedSuccessfully = function (name) {
        var e = element(by.xpath("//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]".replace('%s', name)));
        browser.wait(EC.presenceOf(e), 100000);
        expect(e.isPresent()).toBeTruthy();
    };

    this.verifyDatasetStatus = function (datasetName, datasetStatus) {
        var statusActual = element(by.xpath(STATUS_CELL.replace('%s', datasetName))).getAttribute("tooltip");
        expect(statusActual).toContain(datasetStatus);
    };

};

module.exports = Datasets;
