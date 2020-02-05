'use strict';

var Schema = function () {

    var uploadFileBtn = element(by.partialButtonText('Upload File'));
    var createSchemaBtn = element(by.partialButtonText('Create Schema'));
    var createButtonModal =  element(by.xpath("//div[@class='modal-dialog']//button[contains(.,'Create')]"));
    var uploadButtonModal =  element(by.xpath("//div[@class='modal-dialog']//button[contains(.,'Upload')]"));
    var syncSchemaBtn = element(by.buttonText('Sync Schema'));
    var saveSchemaBtn = element(by.buttonText('Save Schema'));
    var separator = element(by.id('separator'));
    var sourceFile = element(by.xpath("//input[@tooltip='Import']"));
    var schemaStatus = element(by.css(".topright-status"));
    var acceptSchemaBtn = element(by.buttonText('Accept Schema'));
    var addnewFieldBtn = element(by.partialButtonText('Add New Field'));

    //Customer Profile and Agent Profile
    this.clickCreateSchemaBtn = function () {
         createSchemaBtn.click();
    };

    this.verifyCreateSchemaModalOpen = function (modalName) {
         var e = element(by.xpath("//h3[text()='%s']".replace('%s', modalName)));
         expect(e.isPresent()).toBeTruthy();
    };

    this.setSeparator = function (separatorType) {
        separator.click();
        element(by.cssContainingText('option', separatorType)).click();
    };

    this.selectSourceFile = function (filename) {
        var path = require('path');
        var fileToUpload = '../recources/' + filename,
            absolutePath = path.resolve(__dirname, fileToUpload);
        sourceFile.sendKeys(absolutePath);
    };

    this.clickUploadFileBtn = function () {
        uploadFileBtn.click();
    };

    this.clickCreateBtnModal = function () {
      createButtonModal.click();
    };

    this.clickUploadBtnModal = function () {
      uploadButtonModal.click();
    };

    this.verifySchemaDerivedSuccessfully = function (name) {
        var e = element(by.xpath("//*[contains(@class,'table')]//tbody//span[text()='%s']".replace('%s', name)));
        browser.wait(EC.presenceOf(e), 100000);
        expect(e.isPresent()).toBeTruthy();
    };

    this.verifySchemaStatus = function (status) {
        expect(schemaStatus.getText()).toContain(status);
    };

    this.switchToSchemaSubtab = function () {
        browser.sleep(3000);
        element(by.xpath("//ul[@id='tabs']/li[2]")).click();
        // browser.executeScript("arguments[0].click();", link);
        expect(addnewFieldBtn.isDisplayed()).toBeTruthy();
    };

    this.switchToSchemaSubtabToSync = function () {
        browser.sleep(3000);
        element(by.xpath("//ul[@id='tabs']/li[2]")).click();
        // browser.executeScript("arguments[0].click();", link);
        expect(syncSchemaBtn.isDisplayed()).toBeTruthy();
    };


    this.addNewField = function (labelName) {
        addnewFieldBtn.click();
        var e = element(by.xpath("//div[@class='select2-result-label ui-select-choices-row-inner']//span[text()='%s']".replace('%s', labelName)));
        expect(e.isPresent()).toBeTruthy();
        e.click();
    };

    this.addNewExpression = function(label, type, expression) {
        addnewFieldBtn.click();
        element(by.css(".ui-select-search.select2-input.ng-pristine.ng-valid")).sendKeys(label, protractor.Key.ENTER);
        var e = element(by.xpath("(//select[@ng-model='field.type'])[last()]"));
        e.element(by.cssContainingText('option', type)).click();
        element(by.xpath("//textarea")).sendKeys(expression)
    };

    this.setIdFeild = function (labelName) {
        var e = element(by.xpath("//input[@value='%s']/../span[2]".replace('%s', labelName)));
        e.click();
    };

    this.clickSaveSchemaBtn = function () {
        saveSchemaBtn.click();
        expect(syncSchemaBtn.isPresent()).toBeTruthy();
    };

    this.syncSchema = function () {
        syncSchemaBtn.click();
        expect(element(by.xpath("//div[contains(@class,'topright-status') and contains(.,'Schema applied')]"))
            .isPresent).toBeTruthy();
    };

    this.acceptSchema = function () {
        acceptSchemaBtn.click();
        expect(element(by.xpath("//div[contains(@class,'topright-status') and contains(.,'Schema synchronized')]"))
            .isPresent).toBeTruthy();
    };


};

module.exports = Schema;
