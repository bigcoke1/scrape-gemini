"use strict";

(function () {
  window.addEventListener("load", init);

  const URL = "https://www.scrape-insight.com";
  const MONTH = 2592000000;

  google.charts.load("current", {
    packages: ["corechart", "geochart", "table", "gauge"],
  });

  async function init() {
    qs("#register form").addEventListener("submit", makeRegisterRequest);
    qs("#login form").addEventListener("submit", makeLoginRequest);
    qs("#login > button").addEventListener("click", displayRegister);
    qs("#register > button").addEventListener("click", displayLogin);
    qs("#textbox input").addEventListener("change", toggleSubmit);
    id("textbox").addEventListener("submit", makeRequest);
    id("signout-btn").addEventListener("click", signOut);
    id("clear-btn").addEventListener("click", () => {
      let result = confirm("Are you sure you want to clear all history?");
      if (result) {
        clearHistory();
      }
    });
    id("account-btn").addEventListener("click", displayAccount);
    id("home-btn").addEventListener("click", displayHome);
    id("home-btn2").addEventListener("click", displayHome);
    id("pfp-input").addEventListener("change", savePfp);

    id("db-input").addEventListener("change", uploadDatabase);
    id("db-btn").addEventListener("click", displayDatabasePage);
    let exampleQuestions = qsa("#example-questions button");

    exampleQuestions.forEach(button => {
      button.addEventListener("click", async (e) => {
        qs("#textbox input").value = e.target.textContent;
        await makeRequest(e);
      });
    });
    await checkCookie();
  }

  async function displayDatabasePage() {
    id("home").classList.add("hidden");
    id("login").classList.add("hidden");
    id("register").classList.add("hidden");
    id("account").classList.add("hidden");
    qs("body > section:nth-child(1)").style.display = "flex";
    id("database-page").classList.remove("hidden");

    await makeDatabaseRequest();
  }

  async function makeDatabaseRequest() {
    try {
      let username = getCookie("username");
      console.log(username)
      let res = await fetch(URL + "/get-databases/" + username);
      await statusCheck(res);
      res = await res.json();
      populateDatabases(res);
    } catch (err) {
      handleError(err);
      console.log(err);
    }
  }

  function populateDatabases(res) {
    id("database-list").innerHTML = "";
    for (let i = 0; i < res.length; i++) {
      let file = res[i];
      let section = document.createElement("section");
      let paragraph = document.createElement("p");
      paragraph.textContent = file;
      section.appendChild(paragraph);
      let deleteButton = document.createElement("button");
      deleteButton.addEventListener("click", async () => {
        await makeDeleteDbRequest(file);
      });
      section.appendChild(deleteButton);
      id("database-list").prepend(section);
    }
  }

  async function makeDeleteDbRequest(file) {
    try {
      let params = new FormData();
      let username = getCookie("username");
      params.append("username", username);
      params.append("filename", file);
      let res = await fetch(URL + "/delete-database", {
        method: "POST",
        body: params
      });
      await statusCheck(res);
      res = await res.json();
      populateDatabases(res);
    } catch (err) {
      handleError();
      console.log(err);
    }
  }

  async function uploadDatabase() {
    try {
      let params = new FormData();
      let files = id("db-input").files;
      for (let i = 0; i < files.length; i++) {
        params.append("files[]", files[i]);
        params.append("filenames[]", files[i].name);
      }
      params.append("username", getCookie("username"));
      let res = await fetch(URL + "/upload-db", {
        method: "POST",
        body: params
      });
      await statusCheck(res);
      alert("Database updated!")
    } catch (err) {
      handleError(err);
      console.log(err);
    }
  }

  async function makeAccountRequest(username) {
    let res = await fetch(URL + "/account/" + username);
    await statusCheck(res);
    res = await res.text();
    return res;
  }

  function setCookie(name, value, options = {}) {
    let cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;

    if (options.expires) {
      cookie += `; expires=${options.expires}`;
    }
    if (options.path) {
      cookie += `; path=${options.path}`;
    }
    if (options.domain) {
      cookie += `; domain=${options.domain}`;
    }
    if (options.secure) {
      cookie += `; secure`;
    }
    if (options.sameSite) {
      cookie += `; SameSite=${options.sameSite}`;
    }

    document.cookie = cookie;
  }

  function getCookie(name) {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      let [cookieName, cookieValue] = cookie.split("=").map((c) => c.trim());
      if (cookieName === encodeURIComponent(name)) {
        return decodeURIComponent(cookieValue);
      }
    }
    return null;
  }

  function deleteCookie(name) {
    document.cookie = `${encodeURIComponent(
      name
    )}=; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }

  async function clearHistory() {
    try {
      let params = new FormData();
      params.append("username", getCookie("username"));
      let res = await fetch(URL + "/clear", {
        method: "POST",
        body: params,
      });
      await statusCheck(res);
      await makeChatRequest();
      id("chat").innerHTML = "";
    } catch (err) {
      console.log(err);
      handleError();
    }
  }

  async function checkCookie() {
    if (getCookie("username")) {
      await displayHome();
      if (getCookie("username") === "test") {
        let fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.id = "file-input";
        id("textbox").appendChild(fileInput);
        fileInput.addEventListener("change", feedQuestions);
      }
    } else {
      displayLogin();
    }
  }

  async function displayAccount() {
    id("home").classList.add("hidden");
    id("login").classList.add("hidden");
    id("register").classList.add("hidden");
    id("account").classList.remove("hidden");
    qs("body > section:nth-child(1)").style.display = "flex";
    id("database-page").classList.add("hidden");

    let accountInfo = qsa("#account p");
    accountInfo[0].textContent = "Username: " + getCookie("username");
    let email = await makeAccountRequest(getCookie("username"));
    accountInfo[1].textContent = "Email: " + email;

    let img = qs("#pfp-section img");
    img.onerror = function () {
      img.src = "static/images/account.png";
    };
    img.src = "static/images/pfps/" + getCookie("username") + ".png";
  }

  async function savePfp() {
    try {
      let params = new FormData();
      let image = id("pfp-input").files[0];
      let username = getCookie("username");
      params.append("username", username);
      params.append("image", image);

      let res = await fetch(URL + "/save-image", {
        method: "POST",
        body: params,
      });
      await statusCheck(res);
      id("pfp-input").value = "";
      location.reload();
    } catch (err) {
      handleAccountError();
    }
  }

  function displayLogin() {
    id("home").classList.add("hidden");
    id("login").classList.remove("hidden");
    id("register").classList.add("hidden");
    id("account").classList.add("hidden");
    id("database-page").classList.add("hidden");
    qs("body > section:nth-child(1)").style.display = "flex";
  }

  async function signOut() {
    deleteCookie("username");
    await checkCookie();
  }

  function displayRegister() {
    id("home").classList.add("hidden");
    id("login").classList.add("hidden");
    id("register").classList.remove("hidden");
    id("account").classList.add("hidden");
    id("database-page").classList.add("hidden");
    qs("body > section:nth-child(1)").style.display = "flex";
  }

  async function displayHome() {
    id("home").classList.remove("hidden");
    id("login").classList.add("hidden");
    id("register").classList.add("hidden");
    id("chat").innerHTML = "";
    id("account").classList.add("hidden");
    qs("body > section:nth-child(1)").style.display = "none";
    id("database-page").classList.add("hidden");

    let img = qs("#account-btn img");
    img.onerror = function () {
      img.src = "static/images/account.png";
    };
    img.src = "static/images/pfps/" + getCookie("username") + ".png";

    await makeChatRequest();
  }

  async function makeChatRequest() {
    try {
      let username = getCookie("username");
      let res = await fetch(URL + "/get-all-chat/" + username);
      await statusCheck(res);
      res = await res.json();
      populateSidebar(res);
    } catch (err) {
      console.log(err);
      handleError();
    }
  }

  function populateSidebar(res) {
    id("sidebar").innerHTML = "";

    let data = {};

    for (let i = 0; i < res.length; i++) {
      let date = res[i][4];
      if (!data[date]) {
        data[date] = [];
      }
      data[date].push(res[i]);
    }

    for (let date in data) {
      let dateTitle = document.createElement("h2");
      dateTitle.textContent = date;
      dateTitle.addEventListener("click", () => {
        populateChat(data[date]);
      });
      for (let i = 0; i < data[date].length; i++) {
        let queryTitle = document.createElement("h3");
        queryTitle.textContent = data[date][i][2];
        queryTitle.addEventListener("click", () => {
          populateChat([data[date][i]]);
        });
        queryTitle.addEventListener("dblclick", async () => {
          await deleteChat(data[date][i][0]);
        });
        id("sidebar").prepend(queryTitle);
      }
      id("sidebar").prepend(dateTitle);
    }
  }

  async function deleteChat(id) {
    try {
      let params = new FormData();
      params.append("id", id);
      let res = await fetch(URL + "/delete", {
        method: "POST",
        body: params,
      });
      await statusCheck(res);
      await makeChatRequest();
    } catch (err) {
      handleError();
    }
  }

  function populateChat(res) {
    id("chat").innerHTML = "";
    for (let i = 0; i < res.length; i++) {
      try {
        let entry = res[i];
        let chatId = entry[0];
        let question = entry[2];
        let response = entry[3];
        let data = entry[6];
        let format = entry[7];
        displayEntry(question, false);
        let chartBox = displayEntry(
          response,
          true,
          JSON.parse(entry[5]),
          question,
          chatId
        );
        if (data) {
          generateChart(question, data, format, chartBox, chatId);
        } else {
          chartBox.remove();
        }
      } catch (err) {
        console.log(err);
        continue;
      }
    }
  }

  function setExpirationDate() {
    let expirationDate = new Date();
    expirationDate.setTime(expirationDate.getTime() + MONTH);

    let expires = expirationDate.toUTCString();

    return expires;
  }

  async function makeRegisterRequest(e) {
    try {
      e.preventDefault();
      let params = new FormData(qs("#register form"));
      let res = await fetch(URL + "/register", {
        method: "POST",
        body: params,
      });
      await statusCheck(res);
      let username = qs("#register form input").value;
      let inputs = qsa("#register form input");
      inputs.forEach((input) => {
        input.value = "";
      });
      setCookie("username", username, { expires: setExpirationDate() });
      await displayHome();
    } catch (err) {
      console.log(err);
      displayLoginError();
    }
  }

  async function makeLoginRequest(e) {
    try {
      e.preventDefault();
      let params = new FormData(qs("#login form"));
      let res = await fetch(URL + "/login", {
        method: "POST",
        body: params,
      });
      qsa("#login-form input")[1].value = "";
      await statusCheck(res);
      let username = qs("#login form input").value;
      setCookie("username", username, { expires: setExpirationDate() });
      await displayHome();
    } catch (err) {
      console.log(err);
      displayLoginError();
    }
  }

  function toggleSubmit() {
    let button = qs("#textbox button");
    if (this.value.replaceAll(" ", "")) {
      button.disabled = false;
    } else {
      button.disabled = true;
    }
  }

  async function makeRequest(e) {
    try {
      e.preventDefault();
      let query = qs("#textbox input").value;
      qs("#textbox input").value = "";
      displayEntry(query, false);
      await generateResponse(query);
    } catch (err) {
      console.log(err);
      handleError();
    } finally {
      qs("#textbox button").disabled = false;
      qs("#textbox input").disabled = false;
    }
  }

  async function generateResponse(query) {
    let loading = displayLoading();
    qs("#textbox button").disabled = true;
    qs("#textbox input").disabled = true;
    let username = getCookie("username");
    let params = new FormData();
    params.append("query", query);
    params.append("username", username);
    let res = await fetch(URL + "/getresponse", {
      method: "POST",
      body: params,
    });
    await statusCheck(res);
    res = await res.json();
    let textResponse = res[0];
    let dataResponse = res[1];
    let format = res[2];
    let links = res[3];
    let chatId = res[4];
    loading.remove();
    let chartBox = displayEntry(textResponse, true, links, query);
    if (dataResponse) {
      try {
        generateChart(query, dataResponse, format, chartBox, chatId);
      } catch (err) {
        console.log(err);
      }
    } else {
      chartBox.remove();
    }
    await makeChatRequest();
  }

  function displayLoading() {
    let resTextbox = document.createElement("article");
    let aiImage = document.createElement("img");
    aiImage.src = "static/images/AI.png";
    resTextbox.prepend(aiImage);

    let loadingImage = document.createElement("img");
    loadingImage.src = "static/images/loading.gif";
    resTextbox.appendChild(loadingImage);
    resTextbox.classList.add("chat-entry");
    resTextbox.classList.add("response");
    resTextbox.classList.add("shadow");

    id("chat").appendChild(resTextbox);
    id("chat").scrollTop = id("chat").scrollHeight;

    return resTextbox;
  }

  function displayEntry(
    res,
    response,
    links = null,
    query = null,
    chatId = null
  ) {
    let resTextbox = document.createElement("article");
    let text = document.createElement("p");
    text.innerHTML = res;

    let linkBox = document.createElement("p");
    if (links) {
      populateLinks(linkBox, links);
    }
    linkBox.classList.add("links");

    let subTextbox = document.createElement("section");
    let chartBox = document.createElement("section");

    subTextbox.appendChild(text);
    subTextbox.classList.add("sub-textbox");
    subTextbox.appendChild(chartBox);
    subTextbox.appendChild(linkBox);

    resTextbox.appendChild(subTextbox);
    resTextbox.classList.add("chat-entry");
    if (response) {
      populateResponse(resTextbox, subTextbox, chartBox, query, chatId);
    } else {
      resTextbox.classList.add("question");
      let img = document.createElement("img");
      img.onerror = function () {
        img.src = "static/images/account.png";
      };
      img.src = "static/images/pfps/" + getCookie("username") + ".png";
      resTextbox.appendChild(img);
    }
    resTextbox.classList.add("shadow");
    id("chat").appendChild(resTextbox);

    qsa('.response li > p').forEach(p => {
      let parent = p.parentElement;
      parent.innerHTML = p.innerHTML;
    });

    return chartBox;
  }

  function generateChart(query, dataResponse, format, chartBox, chatId) {
    try {
      function removeSpecialCharacters(str) {
        return str.replace(/[^a-zA-Z0-9\s]|[\r\n]/g, '');
      }
      format = removeSpecialCharacters(format)
      let [modifiedData, modifiedFormat] = processDataResponse(dataResponse, format);
      const numRows = modifiedData.length;
      let data = google.visualization.arrayToDataTable(modifiedData);
      let chartHeight = 600;
      let options = {
        title: modifiedData[0][0] + " vs " + modifiedData[0][1],
        titleTextStyle: {
          fontSize: 20,
        },
        fontSize: 15,
        height: 600,
        chartArea: {
          width: "60%", // Adjust the width of the chart area
          height: "90%", // Adjust the height of the chart area
        },
        legend: {
          position: "top", // Position the legend at the top for more space
        },
        colors: ["#3366CC", "#DC3912", "#FF9900", "#109618", "#990099"], // Customize bar colors
        animation: {
          startup: true,
          duration: 1000,
          easing: "out",
        },
      };
  
      let chart;
      if (modifiedFormat === "bar graph") {
        chartHeight = flexHeight(numRows, options);
        chart = new google.visualization.BarChart(chartBox);
        options["bars"] = "horizontal";
        options["bar"] = {
          groupWidth: "80%",
        };
      } else if (modifiedFormat === "line graph") {
        chart = new google.visualization.LineChart(chartBox);
        options["curveType"] = "function"; // Set curve type for line chart
        options["lineWidth"] = 2; // Set line width
      }  else if (modifiedFormat === "table") {
        chart = new google.visualization.Table(chartBox);
        chartHeight = flexHeight(numRows, options);
        options["allowHtml"] = true; // Allows HTML in table cells
        options["showRowNumber"] = true; // Show row numbers
        options["cssClassNames"] = {
          headerRow: "header-row",
          tableRow: "table-row",
          oddTableRow: "odd-table-row",
          selectedTableRow: "selected-table-row",
          hoverTableRow: "hover-table-row",
        };
        options["width"] = chartBox.offsetWidth;
      } else if (modifiedFormat === "geo chart") {
        chart = new google.visualization.GeoChart(chartBox);
        options["colorAxis"] = { colors: ["#e5f5f9", "#2ca25f"] }; // Set color axis range
      } else {
        let error = document.createElement("p");
        error.textContent = "Graphic Type Not Supported Yet";
        error.classList.add("error");
        chartBox.appendChild(error);
      }
      chart.draw(data, options);
  
      chartBox.style.height = chartHeight + 50 + "px";
  
      populateChartButtons(chart, chartBox, chatId, modifiedData);
    } catch (err) {
      console.log(err)
      chartBox.remove()
    }
  }

  function populateChartButtons(chart, chartBox, chatId, dataResponse) {
    let buttonBox = document.createElement("section");
    let saveButton = document.createElement("button");
    saveButton.addEventListener("click", () => {
      console.log(chart.constructor.name);
      if (chart.constructor.name === "gvjs_hM") {
        saveTableAsCSV(dataResponse);
      } else {
        saveChartAsImage(chart);
      }
    });
    saveButton.textContent = "Download Chart";
    buttonBox.appendChild(saveButton);

    let driveImg = document.createElement("img");
    driveImg.src = "static/images/drive.png";
    driveImg.alt = "google drive logo";

    let uploadButton = document.createElement("button");
    uploadButton.addEventListener("click", async () => {
      let data;
      if (chart.constructor.name !== "gvjs_hM") {
        data = chart.getImageURI();
      } else {
        data = dataResponse
          .map((row) => row.map((cell) => `"${cell}"`).join(","))
          .join("\n");
      }
      await makeUploadRequest(data, chatId);
    });
    uploadButton.textContent = "Upload Chart to Google Drive";
    uploadButton.appendChild(driveImg);
    buttonBox.appendChild(uploadButton);

    chartBox.appendChild(buttonBox);
  }

  async function makeUploadRequest(data, chatId) {
    try {
      let params = new FormData();
      params.append("id", chatId);
      params.append("data", data);
      let res = await fetch(URL + "/upload", {
        method: "POST",
        body: params,
      });
      await statusCheck(res);
      alert("Successfully Uploaded!")
    } catch (err) {
      window.location.href = URL + "/google";
    }
  }

  function populateLinks(linkBox, links) {
    // Create a text node for the initial text and the "References:" label
    linkBox.appendChild(document.createTextNode("\n For More Information: "));
    let list = document.createElement("ol");
    for (let i = 0; i < links.length; i++) {
      // Create a text node for the link index and description
      let item = document.createElement("li");

      let urlElement = document.createElement("a");
      urlElement.href = links[i];
      urlElement.textContent = links[i];

      item.appendChild(urlElement);
      // Append the anchor element
      list.appendChild(item);
    }
    linkBox.appendChild(list);
  }

  function populateResponse(resTextbox, subTextbox, chartBox, query, chatId) {
    resTextbox.classList.add("response");
    let img = document.createElement("img");
    img.src = "static/images/AI.png";
    resTextbox.prepend(img);
    let buttonBox = document.createElement("section");
    let newAnswerButton = document.createElement("button");
    newAnswerButton.textContent = "Regenerate Response";
    newAnswerButton.addEventListener("click", () => {
      id("chat").appendChild(resTextbox.previousElementSibling);
      resTextbox.remove();
      generateResponse(query);
    });
    let deleteButton = document.createElement("button");
    deleteButton.textContent = "Delete Response";
    deleteButton.addEventListener("click", async () => {
      resTextbox.previousElementSibling.remove();
      resTextbox.remove();
      await deleteChat(chatId);
    });
    chartBox.classList.add("chart");
    buttonBox.appendChild(newAnswerButton);
    buttonBox.appendChild(deleteButton);

    buttonBox.classList.add("button-box");
    subTextbox.appendChild(buttonBox);
  }

  function processDataResponse(rawDataResponse, format) {
    // Clean and parse the data response
    let dataResponse = JSON.parse(rawDataResponse.replace(/\\/g, ""));
    dataResponse = checkLength(dataResponse);
    const pairedData = pairData(dataResponse);
  
    // Convert format to lowercase for consistent comparison
    format = format.toLowerCase();
  
    // Determine the data format and prepare the data for visualization
    let data;
    if (format === "table") {
      data = convertToStringArray(dataResponse);
    } else {
      if (!isSecondColumnNumeric(pairedData)) {
        format = "table";
        data = convertToStringArray(dataResponse);
      } else {
        data = pairedData
      }
    }
    return [data, format];
  }
  
  function checkLength(dataResponse) {
    const numColumns = dataResponse[0].length;
  
    // Normalize the length of each row
    dataResponse = dataResponse.map(row => {
      if (row.length > numColumns) {
        return row.slice(0, numColumns);
      } else {
        while (row.length < numColumns) {
          row.push(null);
        }
        return row;
      }
    });
  
    // Limit the number of rows to 50
    return dataResponse.length > 50 ? dataResponse.slice(0, 50) : dataResponse;
  }
  
  function pairData(data) {
    // Convert strings to floats where possible
    data = data.map(innerArray => innerArray.map(item => tryParseFloat(item)));
  
    if (data[0].length <= 2) return data;
  
    // Identify the column to keep (first numeric column)
    const colToKeep = findFirstNumericColumn(data);
  
    // Pair data to keep only the first column and the numeric column
    return data.map(row => [row[0], row[colToKeep]]);
  }
  
  function tryParseFloat(item) {
    const floatValue = parseFloat(item);
    return isNaN(floatValue) ? item : floatValue;
  }
  
  function findFirstNumericColumn(data) {
    for (let i = 1; i < data[1].length; i++) {
      if (typeof data[1][i] === "number") {
        return i;
      }
    }
    return 1; // Fallback if no numeric column found
  }
  
  function isSecondColumnNumeric(data) {
    return data.slice(1).every(row => isNumeric(row[1]));
  }
  
  function isNumeric(value) {
    return !isNaN(parseFloat(value)) && isFinite(value);
  }
  
  function convertToStringArray(dataResponse) {
    return dataResponse.map(innerArray => innerArray.map(item => item.toString()))
  }

  function flexHeight(numRows, options) {
    let minHeight = 400;
    let additionalHeight = 30 * numRows;
    let chartHeight = Math.max(minHeight, minHeight + additionalHeight);
    options["height"] = chartHeight;
    return chartHeight;
  }

  function saveChartAsImage(chart) {
    let imgUrl = chart.getImageURI();
    let link = document.createElement("a");
    link.href = imgUrl;
    link.download = "chart.png";
    link.click();
  }

  function saveTableAsCSV(dataResponse) {
    let csv = dataResponse
      .map((row) => row.map((cell) => `"${cell}"`).join(","))
      .join("\n");
    let csvFile = new Blob([csv], { type: "text/csv" });
    let downloadLink = document.createElement("a");

    downloadLink.download = "table.csv";
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = "none";

    document.body.appendChild(downloadLink);
    downloadLink.click();
  }

  async function feedQuestions(e) {
    try {
      e.preventDefault();
      let username = getCookie("username");
      let file = id("file-input").files[0];
      if (file) {
        let reader = new FileReader();
        reader.readAsText(file);
        reader.onload = function (e) {
          let fileContent = e.target.result;
          let lines = fileContent.split("\n");

          lines.forEach(async (line, index) => {
            let params = new FormData();
            params.append("query", line);
            params.append("username", username);
            console.log(line);
            let res = await fetch(URL + "/getresponse", {
              method: "POST",
              body: params,
            });
            await statusCheck(res);
          });
        };
      }
    } catch (err) {
      console.log(err);
      handleError();
    }
  }

  function handleError() {
    let error = document.createElement("p");
    error.textContent = "An Error Occured. Try Again Later!";
    error.classList.add("error");
    id("chat").appendChild(error);
  }

  function displayLoginError() {
    qs("#login p").classList.remove("hidden");
    qs("#register p").classList.remove("hidden");
    setTimeout(() => {
      qs("#login p").classList.add("hidden");
      qs("#register p").classList.add("hidden");
    }, 3000);
  }

  function handleAccountError() {
    let error = document.createElement("p");
    error.textContent = "An error occured. Try again Later.";
    id("pfp-section").appendChild(error);
  }

  /**
   * Returns the element that has the ID attribute with the specified value.
   * @param {string} id - element ID.
   * @returns {object} - DOM object associated with id.
   */
  function id(id) {
    return document.getElementById(id);
  }

  /**
   * Returns first element matching selector.
   * @param {string} selector - CSS query selector.
   * @returns {object} - DOM object associated selector.
   */
  function qs(selector) {
    return document.querySelector(selector);
  }

  /**
   * Returns the array of elements that match the given CSS selector.
   * @param {string} query - CSS query selector
   * @returns {object[]} array of DOM objects matching the query.
   */
  function qsa(query) {
    return document.querySelectorAll(query);
  }

  /**
   * Helper function to return the response's result text if successful, otherwise
   * returns the rejected Promise result with an error status and corresponding text
   * @param {object} res - response to check for success/error
   * @return {object} - valid response if response was successful, otherwise rejected
   *                    Promise result
   */
  async function statusCheck(res) {
    if (!res.ok) {
      throw new Error(await res.text());
    }
    return res;
  }
})();
