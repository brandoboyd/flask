'use strict';

/* https://github.com/angular/protractor/blob/master/docs/toc.md */

describe('The Application Login', function() {

  it('should automatically redirect back to /login if user wasn\'t authenticated', function() {
    browser.get('/login');
    expect(browser.getLocationAbsUrl()).toMatch("/login");
  });

});

describe('The login page', function() {

  beforeEach(function() {
    browser.get('/login');
  });


  /*
  it('should have proper h2 title', function() {
    pending('Force skip');
    expect(element(by.css('.form-group')).element(by.tagName('h2')).getText()).
    toMatch(/(Journey|Social) Analytics/);
  });
  */

  it('\'Privacy Policy\' link should have proper href parameter', function() {
    var el = element(by.linkText('Privacy Policy'));
    expect(el.getAttribute('href')).toMatch("http://www.genesys.com/about-genesys/legal");
  });

  it('\'Forgot your password?\' link should navigate to /passrestore page', function() {
    var el = element(by.linkText('Forgot your password?'));
    el.click();
    expect(browser.getLocationAbsUrl()).toMatch("/passrestore");
  });

});
