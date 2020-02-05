'use strict';

var LoginPage = require("../pages/login_page");
var AppSwitcher = require("../pages/app_switcher");
var Datasets = require("../pages/datasets");
var using = require('jasmine-data-provider');
var csvType = require('./dataprovider/csvData.js');
var datasetName = null;


describe("PRR App - ", function () {

    var loginPage = new LoginPage();
    var appCtxt = new AppSwitcher();
    var dataset = new Datasets();


    beforeAll(function () {
        loginPage.login('/login');
        appCtxt.switch('Predictive Matching', true);
    });


    describe('Create dataset', function () {
        using(csvType.types, function (value, key) {
            dataset = new Datasets();
            it(" should have correct title", function () {
                dataset.navigateToDatasetsList();
                dataset.verifyDatasetPageOpen();

            });

            it(" should display new form after clicking the button ", function () {
                dataset.clickAddNewDatasetBtn();
                var title = element(by.tagName('h3'));
                expect(title.getText()).toEqual('Create Dataset');
            });

            it("should redirect to the list page after creation", function () {
                datasetName = dataset.setDataset();
                if (key === 'HUGE') {
                    key = 'TAB'
                }
                dataset.setSeparator(key);
                dataset.setSourceFile(value.handle);
                dataset.clickCreateBtn();
                dataset.waitDatasetCreatedSuccessfully(datasetName);
                dataset.verifyDatasetStatus(datasetName, 'Schema out of synchronization');
            }, 120000);
        });
    });

    describe('Remove existing dataset', function () {
        it(" should correctly remove dataset", function () {
            dataset.navigateToDatasetsList();
            dataset.openDataset(datasetName);
            dataset.applySchema();
            dataset = dataset.navigateBack();
            dataset.verifyDatasetPageOpen();
            dataset.verifyDatasetStatus(datasetName, 'Schema synchronized');
        });
    });


});
