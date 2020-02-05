'use strict';

var LoginPage = require("../pages/login_page");
var AppSwitcher = require("../pages/app_switcher");
var Account = require("../pages/account");
var ConfigureMenu = require("../pages/configure_menu");
var Select2Widget = require("../pages/select2");
var CustomerProfile = require("../pages/customer_profile");
var ChannelTypes = require("../pages/channel_types");
var EventType = require("../pages/event_type");
var Schema = require("../pages/schema");
var Channels = require("../pages/channels");
var JourneyType = require("../pages/journey_types");
var MainMenu = require("../pages/main_menu");
var JourneysDetails = require("../pages/journeys_details");

describe("User should be able to sync dynamic events", function() {

  var loginPage = new LoginPage();
  var appCtxt = new AppSwitcher();
  var account = new Account();
  var configureMenu = new ConfigureMenu();
  var select2 = new Select2Widget();
  var customerProfile = new CustomerProfile();
  var channelTypes = new ChannelTypes();
  var schema = new Schema();
  var eventType = new EventType();
  var channels = new Channels();
  var journeyType = new JourneyType();
  var mainMenu = new MainMenu();
  var journeysDetails = new JourneysDetails();

  var channelTypeName = 'ChannelType' + Date.now();
  var accountName = 'Acc' + Date.now();
  var eventTypeName = 'EventType' + Date.now();
  var channelName = 'CustomChannel' + Date.now();
  var journeyTypeName = 'JourneyTypeName' + Date.now();


  beforeAll(function() {
    loginPage.login('/login');
    configureMenu.switchByLink('/configure#/accounts');
    account.create(accountName);
    var accountLink = account.locateAccountLinkByName(accountName);
    accountLink.first().click();
    select2.addTag('s2id_configurable_apps', 'Journey Analytics');
    var tags = select2.getTagsList('s2id_configurable_apps');
    element(by.buttonText('Update')).click();
    account.activateAccount(accountName);
    appCtxt.switch('Journey Analytics', true);
  });


  describe('Customer Profile Schema:', function() {

    it(" verify Customer Profile page opens", function() {
      customerProfile.navigateToCustomerProfile();
      customerProfile.verifyCustomerProfilePageOpen();
    });

    it(" invoke Create Profile Schema dialog", function() {
      schema.clickCreateSchemaBtn();
      schema.verifyCreateSchemaModalOpen('Create Profile Schema');
    });

    it(" derive schema - success", function() {
      schema.setSeparator("TAB");
      schema.selectSourceFile("customers_simple.csv");
      schema.clickCreateBtnModal();
      schema.verifySchemaDerivedSuccessfully("NAME");
      schema.verifySchemaStatus('Schema out of synchronization', true);
    });

    it(" create Customer Profile schema", function() {
      schema.switchToSchemaSubtab();
      schema.addNewField('NAME');
      schema.addNewField('SEGMENT');
      schema.addNewField('LOCATION');
      schema.addNewField('CUSTOMER_ID');
      schema.setIdFeild('CUSTOMER_ID');
      schema.clickSaveSchemaBtn();
      schema.syncSchema('Schema synchronized', true);
      schema.acceptSchema('Schema applied', true);
    });
  });

  describe('Channel Type:', function() {

    it(" verify Channel Types page opens", function() {
      channelTypes.navigateToChannelTypes();
      channelTypes.verifyChannelTypesPageOpen();
    });

    it(" invoke New Channel Type form", function() {
      channelTypes.clickAddChannelTypeBtn();
    });

    it("should redirect to the list page after creation", function() {
      channelTypes.addChannelTypeName(channelTypeName);
      channelTypes.clickCreateBtn();
      channelTypes.waitChannelTypeCreatedSuccessfully(channelTypeName);
    });
  });

  describe('Event Type:', function() {

    it(" verify Event Type page opens", function() {
      eventType.navigateToEventTypesPage();
      eventType.verifyEventTypesPageOpen();
    });

    it(" invoke New Event Type form", function() {
      eventType.clickAddEventTypeBtn();
      eventType.verifyNewEventTypePageOpen();
    });

    it("should redirect to the list page after creation", function() {
      eventType.addEventTypeName(eventTypeName);
      eventType.addChannelType(channelTypeName);
      eventType.clickCreateEventTypeBtn();
      eventType.waitEventTypeCreatedSuccessfully(eventTypeName);
      eventType.verifyEventTypeStatus(eventTypeName, 'Schema out of synchronization');
    });

    it("clicking on event type name should open Update form", function() {
      eventType.openEventType(eventTypeName);
    });

    it("derive event type schema - success", function() {
      schema.clickUploadFileBtn();
      schema.verifyCreateSchemaModalOpen('Discover Schema');
      schema.setSeparator('TAB');
      schema.selectSourceFile("events_simple.csv");
      schema.clickUploadBtnModal();
      schema.verifySchemaDerivedSuccessfully("CONTENT");
      schema.verifySchemaStatus('Schema out of synchronization', true);
    });

    it(" create event type schema - no sync", function() {
      schema.switchToSchemaSubtab();
      schema.addNewField('CONTENT');
      schema.addNewField('NPS');
      schema.addNewField('actor_id');
      schema.addNewExpression('intention', 'Dict', 'extract_intentions("CONTENT")');
      schema.clickSaveSchemaBtn();
    });
  });

  describe('Channel:', function() {

    it(" verify Channels page opens", function() {
      channels.navigateToChannelsPage();
      channels.verifyNewChannelFormOpen();
    });

    it(" create channel with custom channel type", function() {
      channels.addChannelType(channelTypeName);
      channels.addChannelName(channelName);
      channels.clickCreateBtn();
      channels.invokeImportEventDataModal();
      channels.selectSourceFile("events_simple.csv");
      channels.setSeparator('TAB');
      channels.selectEventType();
      channels.clickUploadButtonModal();
      channels.clickUpdateChannelButton();
      channels.clickAllChannelsButton();
      channels.waitChannelCreatedSuccessfully(channelName);
    });
  });

  describe('Sync Events:', function() {

    it(" open Event Type", function() {
      eventType.navigateToEventTypesPage();
      eventType.verifyEventTypesPageOpen();
      eventType.openEventType(eventTypeName);
    });

    it(" sync Event Type schema", function() {
      schema.switchToSchemaSubtabToSync();
      schema.syncSchema();
      schema.acceptSchema();
    });
  });

  describe('Journey Type:', function() {

    it(" verify Journey Types page opens", function() {
      journeyType.navigateToJourneyTypesPage();
      journeyType.verifyJourneyTypesPageOpen();
    });

    it(" invoke New Journey Type form", function() {
      journeyType.clickAddJourneyTypeBtn();
      journeyType.verifyNewJourneyTypePageOpen();
    });

    it(" create journey type", function() {
      journeyType.addJourneyTypeName(journeyTypeName);
      journeyType.clickCreateJourneyTypeBtn();
    });

    it(" add attributes", function() {
      journeyType.clickAddAttributeBtn();
      journeyType.addAttribute(0, "nps", "String", "max([nps or 1, current_event.NPS])");
      journeyType.clickAddAttributeBtn();
      journeyType.addAttribute(1, "segment", "String", "customer_profile.SEGMENT");
      journeyType.clickAddAttributeBtn();
      journeyType.addAttribute(2, "customer_name", "String", "customer_profile.NAME");
    });

    it(" add stages", function() {
      journeyType.clickAddStageBtn();
      journeyType.addStage(0, "inquiry", "ongoing", "current_event.intention[0]['intention_type'] in ('Asks for Something', 'States a Need / Want')", eventTypeName);
      journeyType.clickAddStageBtn();
      journeyType.addStage(1, "issues", "ongoing", "current_event.intention[0]['intention_type'] in ('States a Problem / Dislikes', 'Recommendation') and (current_event.NPS is None or current_event.NPS < 5)", eventTypeName);
      journeyType.clickAddStageBtn();
      journeyType.addStage(2, "recovered", "ongoing", "current_event.NPS > 8", eventTypeName);
      journeyType.clickAddStageBtn();
      journeyType.addStage(3, "abandoned", "abandoned", "current_event.NPS != None and current_event.NPS < 5", eventTypeName);
    });

    it(" update journey type", function() {
      journeyType.saveJourneyType();
    });
  });

  describe('User should see synced journeys displayed', function() {

    it(" verify number of journeys on All Journeys Page", function() {
      journeyType.navigateToAllJourneyTypes();
      journeyType.verifyJourneyTypesPageOpen();
      journeyType.waitJourneyTypeCreatedSuccessfully(journeyTypeName);
      journeyType.verifyJourneysNumber(journeyTypeName, "4");
    });

    it(" verify journeys are shown on Journeys Details page", function() {
      mainMenu.switch("Journeys");
      journeysDetails.verifySubTabTitle("Journeys Details");
      journeysDetails.verifyNumberOfItemsList(4);
    });
  });
});
