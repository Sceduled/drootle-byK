// Google Apps Script for Agentic Lead AI
// Triggers on new rows in the leads sheet and sends a webhook to the backend.

const WEBHOOK_URL = "https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/webhooks/new-lead";
const WEBHOOK_SECRET = "YOUR-WEBHOOK-SECRET";

function createTrigger() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet();
  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(sheet)
    .onFormSubmit()
    .create();
}

function onFormSubmit(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const range = e.range;
  const row = range.getRow();
  
  // Assuming columns: A=Name, B=Phone, C=Email, D=Company, E=Source Ad
  const name = sheet.getRange(row, 1).getValue();
  const phone = sheet.getRange(row, 2).getValue();
  const email = sheet.getRange(row, 3).getValue();
  const company = sheet.getRange(row, 4).getValue();
  const source_ad = sheet.getRange(row, 5).getValue();

  const payload = {
    name: name,
    phone: phone,
    email: email,
    company_name: company,
    source_ad: source_ad,
    sheet_row_index: row
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'X-Webhook-Secret': WEBHOOK_SECRET
    },
    payload: JSON.stringify(payload)
  };

  try {
    UrlFetchApp.fetch(WEBHOOK_URL, options);
  } catch (err) {
    console.error("Webhook failed:", err);
  }
}
