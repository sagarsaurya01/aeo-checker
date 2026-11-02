# Make leads land in a Google Sheet (5 minutes, one time)

Every audit will add a row to a Google Sheet you own. You just do 4 clicks and
send me the link.

## Steps

1. **Make the sheet** — go to https://sheets.new and name it "AEO Leads".

2. **Open Apps Script** — in the sheet: menu **Extensions → Apps Script**.

3. **Paste this code** (delete anything already there), then click the 💾 Save icon:

```javascript
function doPost(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheets()[0];
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['timestamp', 'name', 'phone', 'email', 'url', 'score']);
  }
  var d = JSON.parse(e.postData.contents);
  sheet.appendRow([d.timestamp, d.name, d.phone, d.email, d.url, d.score]);
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

4. **Deploy it** — click **Deploy → New deployment**.
   - Click the gear ⚙ and choose **Web app**.
   - **Execute as:** Me
   - **Who has access:** **Anyone**
   - Click **Deploy**, allow/authorise when asked, then **copy the Web app URL**
     (it looks like `https://script.google.com/macros/s/AKfy.../exec`).

5. **Send me that URL.** I'll plug it into the live app and your leads start flowing
   into the sheet.

That's it — after this, every person who checks their site shows up as a new row,
with their name, WhatsApp, email, website and score.
