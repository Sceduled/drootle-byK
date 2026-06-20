// Google Apps Script for Agentic Lead AI
// Polling trigger that checks the sheet every minute for new leads.
// Run setupTimeDrivenTrigger() once manually to install.

function checkForNewLeads() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var lastRow = sheet.getLastRow();
  
  var properties = PropertiesService.getScriptProperties();
  var lastProcessedRow = parseInt(properties.getProperty('lastProcessedRow') || '1');
  
  if (lastRow <= lastProcessedRow) {
    return; // no new rows
  }
  
  for (var row = lastProcessedRow + 1; row <= lastRow; row++) {
    var rowData = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
    
    // Assuming columns: A=Name, B=Phone, C=Email, D=Company, E=Source Ad
    var name = rowData[0];
    var phone = rowData[1];
    var email = rowData[2];
    var company = rowData[3];
    var source_ad = rowData[4];
    
    if (!phone) continue;
    
    var payload = {
      name: name,
      phone: String(phone),
      email: email,
      company: company,
      source_ad: source_ad,
      sheet_row: row
    };
    
    var options = {
      method: 'POST',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      headers: { 'X-Webhook-Secret': 'YOUR-WEBHOOK-SECRET' },
      muteHttpExceptions: true
    };
    
    UrlFetchApp.fetch('https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/webhooks/new-lead', options);
  }
  
  properties.setProperty('lastProcessedRow', lastRow.toString());
}

function setupTimeDrivenTrigger() {
  // Delete old triggers first
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  
  // Create new time-driven trigger, runs every minute
  ScriptApp.newTrigger('checkForNewLeads')
    .timeBased()
    .everyMinutes(1)
    .create();
}
