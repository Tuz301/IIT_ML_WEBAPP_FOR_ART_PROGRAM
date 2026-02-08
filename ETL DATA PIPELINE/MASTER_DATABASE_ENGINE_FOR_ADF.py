MASTER PDX BIODATA DATABASE ENGINE 

function onFormSubmit(e) { 

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet(); 

  var lastRowValues; 

 

  // 1️⃣ Get row data from event if available, else use last row from sheet 

  if (e && e.values) { 

    lastRowValues = e.values; 

  } else { 

    var lastRowNum = sheet.getLastRow(); 

    lastRowValues = sheet.getRange(lastRowNum, 1, 1, sheet.getLastColumn()).getValues()[0]; 

    Logger.log("Fallback mode: using last row from sheet."); 

  } 

 

  // 2️⃣ Get headers and locate "IP" column 

  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0]; 

  var ipColIndex = headers.indexOf("IP"); 

  if (ipColIndex === -1) { 

    Logger.log("No 'IP' column found in the sheet."); 

    return; 

  } 

 

  // 3️⃣ Normalize IP value for matching 

  var ipValue = String(lastRowValues[ipColIndex]).trim().toUpperCase(); 

 

  // 4️⃣ Destination mapping 

  var destinations = { 

    "IHVN": { 

      name: "IHVN PDX BIO DATA BASE", 

      url: "https://docs.google.com/spreadsheets/d/11Kg76BydJIYBXdk39TaZFzZEvPmDSwpdhIl3GK_iDK4/edit" 

    }, 

    "APIN": { 

      name: "APIN PDX BIODATA BASE", 

      url: "https://docs.google.com/spreadsheets/d/1lQRloBXRxSYD8ijPdP4Kyot-OHBgTfRk1KhhXJ3PldQ/edit" 

    }, 

    "ECEWS": { 

      name: "ECEWS PDX BIODATA DATABASE", 

      url: "https://docs.google.com/spreadsheets/d/1pLGQO4AJJRqbiOvKJaTg0UNQOR0x42Iedto6Ch-oRhU/edit" 

    }, 

    "CIHP": { 

      name: "CIHP PDX BIODATA BASE", 

      url: "https://docs.google.com/spreadsheets/d/1cIVg65rPABcLiwdMf3szr1ip9yTx0pHFrvmSdC6mkyg/edit" 

    }, 

    "CCFN": { 

      name: "CCFN PDX BIODATA BASE", 

      url: "https://docs.google.com/spreadsheets/d/168M1T74bYvH6ZmxOfDdoIexjuLa8jngmFUaiL7LfNuA/edit" 

    } 

  }; 

 

  // 5️⃣ Find destination 

  var destination = null; 

  for (var key in destinations) { 

    if (ipValue.includes(key)) { 

      destination = destinations[key]; 

      break; 

    } 

  } 

 

  if (!destination) { 

    Logger.log("Unrecognized IP value: " + ipValue); 

    logRouting(ipValue, "N/A", "N/A", "Failed - Unknown IP"); 

    return; 

  } 

 

  // 6️⃣ Append row to destination sheet with tab fallback 

  try { 

    var destSpreadsheet = SpreadsheetApp.openByUrl(destination.url); 

    var destSheet = destSpreadsheet.getSheetByName(destination.name); 

 

    if (!destSheet) { 

      Logger.log("Sheet tab '" + destination.name + "' not found. Using first sheet instead."); 

      destSheet = destSpreadsheet.getSheets()[0]; 

    } 

 

    destSheet.appendRow(lastRowValues); 

    Logger.log("Row sent to: " + destSheet.getName()); 

 

    // Log success 

    logRouting(ipValue, destination.name, destination.url, "Success"); 

  } catch (err) { 

    Logger.log("Error sending row: " + err); 

    logRouting(ipValue, destination.name, destination.url, "Failed - " + err); 

  } 

} 

 

// 📜 Log routing results in 'Routing Log' tab 

function logRouting(ipValue, destName, destUrl, status) { 

  var ss = SpreadsheetApp.getActiveSpreadsheet(); 

  var logSheet = ss.getSheetByName("Routing Log"); 

 

  // Create log sheet with headers if not found 

  if (!logSheet) { 

    logSheet = ss.insertSheet("Routing Log"); 

    logSheet.appendRow(["Timestamp", "IP", "Destination Sheet", "Destination URL", "Status"]); 

  } 

 

  logSheet.appendRow([ 

    new Date(), 

    ipValue, 

    destName, 

    destUrl, 

    status 

  ]); 

} 

 

 